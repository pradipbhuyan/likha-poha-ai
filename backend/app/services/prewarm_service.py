"""
Pre-warm Service
================
Grade-level lesson and question bank pre-generation.
Runs as background tasks triggered from the admin cache management panel.

Tracks in-progress jobs in memory (works for single-instance deployments).
Status is persisted in the lesson_cache / question_bank Supabase tables.
"""

import logging
import re
import threading
import time

logger = logging.getLogger(__name__)

from app.data.syllabus import CBSE_9, SOF_9
from app.services.tutor_service import generate_step_lesson
from app.services.lesson_cache_service import get_cached_lesson, make_lesson_cache_key
from app.services.question_bank_service import add_questions_to_bank
from app.services.openai_service import ask_llm, PREWARM_TEXT_MODEL
from app.services.supabase_client import supabase

# ------------------------------------------------------------------ constants

LESSON_STEPS = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Practice questions",
    "Revision and recap",
]

DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTIONS_PER_BATCH = 20
BATCHES_PER_CHAPTER = 3
REQUEST_DELAY_SECONDS = 1.5

MOCK_TEST_SYSTEM = (
    "You create original CBSE mock test questions for exam preparation. "
    "Return ONLY valid JSON array. No markdown. "
    'Schema: [{"id":1,"section":"MCQ","question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"answer":"A","explanation":"...","marks":1}]'
)

# ---------------------------------------------------------- in-memory job state

_running_jobs: dict[str, str] = {}
_job_lock = threading.Lock()


def is_job_running(job_key: str) -> bool:
    """Return True if a background job is currently running."""
    with _job_lock:
        return _running_jobs.get(job_key) == "running"


def set_job_status(job_key: str, status: str) -> None:
    """Set job status: 'running' or 'idle'."""
    with _job_lock:
        _running_jobs[job_key] = status


def get_all_job_statuses() -> dict[str, str]:
    """Return a snapshot of all job statuses."""
    with _job_lock:
        return dict(_running_jobs)


# ------------------------------------------------------- syllabus helpers

def get_syllabus_for_grade(grade: str) -> dict:
    """
    Return {mode: {subject: [chapter, ...]}} using the same reviewed syllabus
    data the student-facing UI uses (merge_uploaded_rag_chapters).

    This ensures the full-grade prewarm generates lessons for exactly the
    chapters students can access — matching the student lesson dropdown.
    """
    reviewed = _get_reviewed_syllabus_for_grade(grade)
    if reviewed:
        return reviewed
    # Fallback: read raw rag_documents if syllabus merge fails
    try:
        response = (
            supabase
            .table("rag_documents")
            .select("subject, chapter, board")
            .eq("grade", grade)
            .execute()
        )
        syllabus: dict = {"CBSE": {}, "SOF": {}}
        for doc in response.data or []:
            subject = doc.get("subject") or ""
            chapter = doc.get("chapter") or ""
            mode = "SOF" if "Olympiad" in subject else "CBSE"
            if subject and chapter:
                syllabus[mode].setdefault(subject, [])
                if chapter not in syllabus[mode][subject]:
                    syllabus[mode][subject].append(chapter)
        return syllabus
    except Exception:
        return {"CBSE": {}, "SOF": {}}


def has_rag_content_for_chapter(board: str, grade: str, subject: str, chapter: str) -> bool:
    """
    Return True if at least one RAG document exists for this chapter.

    Pre-generation skips chapters without RAG so lessons are always
    grounded in uploaded textbook content rather than LLM general knowledge.
    """
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
        result = (
            supabase
            .table("rag_documents")
            .select("id")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", clean_chapter)
            .limit(1)
            .execute()
        )
        return len(result.data or []) > 0
    except Exception:
        return False  # If DB check fails, skip to be safe


def count_expected_lessons(grade: str) -> int:
    """
    Total lesson steps to generate for a grade (RAG-backed chapters only).

    Only chapters that have at least one RAG document are counted so the
    progress bar reflects what will actually be generated.
    """
    syllabus = get_syllabus_for_grade(grade)
    total = 0
    for mode, mode_data in syllabus.items():
        board = "CBSE"
        for subject, chapters in mode_data.items():
            for chapter in chapters:
                if has_rag_content_for_chapter(board, grade, subject, chapter):
                    total += len(LESSON_STEPS)
    return total


def count_expected_questions(grade: str) -> int:
    """Total bank questions expected for a grade (CBSE only)."""
    syllabus = get_syllabus_for_grade(grade)
    cbse_data = syllabus.get("CBSE", {})
    total = 0
    for chapters in cbse_data.values():
        total += len(chapters) * len(DIFFICULTIES) * QUESTIONS_PER_BATCH * BATCHES_PER_CHAPTER
    return total


def count_cached_lessons(grade: str) -> int:
    """Count active cached lessons for a grade."""
    try:
        result = (
            supabase
            .table("lesson_cache")
            .select("id", count="exact")
            .eq("grade", grade)
            .eq("status", "active")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def count_banked_questions(grade: str) -> int:
    """Count active question bank entries for a grade."""
    try:
        result = (
            supabase
            .table("question_bank")
            .select("id", count="exact")
            .eq("grade", grade)
            .eq("status", "active")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def clear_lesson_cache_for_grade(grade: str) -> int:
    """Delete all lesson cache rows for a grade. Returns count deleted."""
    try:
        result = (
            supabase
            .table("lesson_cache")
            .delete()
            .eq("grade", grade)
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0


def clear_question_bank_for_grade(grade: str) -> int:
    """Delete all question bank rows for a grade. Returns count deleted."""
    try:
        result = (
            supabase
            .table("question_bank")
            .delete()
            .eq("grade", grade)
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0


# ------------------------------------------------------- background jobs

def prewarm_lessons_for_grade(grade: str) -> None:
    """
    Background task: generate and cache RAG-backed lesson steps for a grade.

    Only chapters that have RAG documents uploaded are processed.
    Chapters without RAG content are skipped — this ensures all cached
    lessons are grounded in uploaded textbook material.
    Already-cached steps are also skipped (safe to re-run).
    """
    job_key = f"lessons_{grade.replace(' ', '')}"
    set_job_status(job_key, "running")

    try:
        syllabus = get_syllabus_for_grade(grade)

        for mode, mode_data in syllabus.items():
            board = "CBSE" if mode != "SOF" else "CBSE"
            for subject, chapters in mode_data.items():
                for chapter in chapters:
                    # Skip chapters with no uploaded RAG content
                    if not has_rag_content_for_chapter(board, grade, subject, chapter):
                        continue

                    for step_title in LESSON_STEPS:
                        cache_key = make_lesson_cache_key(
                            board=board,
                            grade=grade,
                            subject=subject,
                            chapter=chapter,
                            mode=mode,
                            step_title=step_title,
                            teacher_persona="",
                        )
                        if get_cached_lesson(cache_key):
                            continue

                        try:
                            generate_step_lesson(
                                grade=grade,
                                subject=subject,
                                chapter=chapter,
                                mode=mode,
                                step_title=step_title,
                                teacher_persona="",
                                username="prewarm_admin",
                                board=board,
                                model=PREWARM_TEXT_MODEL,
                            )
                            time.sleep(REQUEST_DELAY_SECONDS)
                        except Exception as exc:
                            logger.warning(
                                "Prewarm step failed [%s | %s | %s | %s]: %s",
                                grade, subject, chapter, step_title, exc,
                            )
                            time.sleep(REQUEST_DELAY_SECONDS * 2)

    except Exception as exc:
        logger.error("Prewarm lessons job failed for %s: %s", grade, exc)
    finally:
        set_job_status(job_key, "idle")


def build_question_bank_for_grade(grade: str) -> None:
    """
    Background task: generate question bank for all CBSE chapters of a grade.
    Already-populated chapter/difficulty combinations are skipped.
    """
    job_key = f"questions_{grade.replace(' ', '')}"
    set_job_status(job_key, "running")

    try:
        syllabus = get_syllabus_for_grade(grade)
        cbse_data = syllabus.get("CBSE", {})
        board = "CBSE"

        for subject, chapters in cbse_data.items():
            for chapter in chapters:
                for difficulty in DIFFICULTIES:
                    for batch in range(1, BATCHES_PER_CHAPTER + 1):
                        prompt = (
                            f"Create {QUESTIONS_PER_BATCH} original {difficulty} MCQ questions "
                            f"for {grade} {board} {subject}. Chapter: {chapter}. Batch: {batch}. "
                            "Return ONLY valid JSON array."
                        )

                        try:
                            raw = ask_llm(
                                MOCK_TEST_SYSTEM,
                                prompt,
                                username="bank_builder",
                                feature="question_bank_build",
                            )
                            raw = raw.strip()
                            if raw.startswith("```"):
                                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                                raw = re.sub(r"\s*```$", "", raw)
                            start = raw.find("[")
                            end = raw.rfind("]")
                            if start != -1 and end > start:
                                import json
                                questions = json.loads(raw[start:end + 1])
                                if isinstance(questions, list) and questions:
                                    add_questions_to_bank(
                                        questions=questions,
                                        board=board,
                                        grade=grade,
                                        subject=subject,
                                        chapter=chapter,
                                        difficulty=difficulty,
                                        exam_type="General",
                                    )
                        except Exception as exc:
                            logger.warning(
                                "Question bank batch failed [%s | %s | %s | difficulty=%s | batch=%d]: %s",
                                grade, subject, chapter, difficulty, batch, exc,
                            )

                        time.sleep(REQUEST_DELAY_SECONDS)

    except Exception as exc:
        logger.error("Build question bank job failed for %s: %s", grade, exc)
    finally:
        set_job_status(job_key, "idle")


def _get_reviewed_syllabus_for_grade(grade: str) -> dict:
    """
    Return the reviewed {mode: {subject: [chapters]}} for a grade using the
    same merge_uploaded_rag_chapters logic the student-facing syllabus uses.

    This ensures prewarm chapter names exactly match what students see.
    """
    try:
        from app.routes.syllabus import merge_uploaded_rag_chapters  # noqa: PLC0415
        from app.data.syllabus import SYLLABUS  # noqa: PLC0415
        full_syllabus = merge_uploaded_rag_chapters(SYLLABUS)
        return full_syllabus.get(grade, {})
    except Exception:
        return {}


def get_chapters_for_grade(grade: str) -> list[dict]:
    """
    Return deduplicated {mode, subject, chapter} dicts using the same
    reviewed syllabus data students see in their lesson dropdown.

    Uses merge_uploaded_rag_chapters so the chapter panel always matches
    the student UI — no duplicates, no unreviewed placeholder chapters.
    """
    try:
        grade_data = _get_reviewed_syllabus_for_grade(grade)
        seen: set = set()
        chapters: list[dict] = []
        for mode, mode_subjects in grade_data.items():
            for subject, chapter_list in (mode_subjects or {}).items():
                for chapter in (chapter_list or []):
                    if not chapter:
                        continue
                    key = (mode, subject, chapter)
                    if key not in seen:
                        seen.add(key)
                        chapters.append({"mode": mode, "subject": subject, "chapter": chapter})
        return sorted(chapters, key=lambda x: (x["mode"], x["subject"], x["chapter"]))
    except Exception:
        return []


def prewarm_single_chapter(grade: str, mode: str, subject: str, chapter: str) -> None:
    """
    Background task: generate and cache all 5 lesson steps for one specific chapter.

    Useful for testing a newly uploaded chapter without running the full grade prewarm.
    Already-cached steps are skipped so this is safe to re-run.
    """
    board = "CBSE"
    safe_subject = subject[:12].replace(" ", "_")
    safe_chapter = chapter[:12].replace(" ", "_")
    job_key = f"chapter_{grade.replace(' ', '')}_{safe_subject}_{safe_chapter}"
    set_job_status(job_key, "running")

    try:
        for step_title in LESSON_STEPS:
            cache_key = make_lesson_cache_key(
                board=board,
                grade=grade,
                subject=subject,
                chapter=chapter,
                mode=mode,
                step_title=step_title,
                teacher_persona="",
            )
            if get_cached_lesson(cache_key):
                continue

            try:
                generate_step_lesson(
                    grade=grade,
                    subject=subject,
                    chapter=chapter,
                    mode=mode,
                    step_title=step_title,
                    teacher_persona="",
                    username="prewarm_admin",
                    board=board,
                    model=PREWARM_TEXT_MODEL,
                )
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as exc:
                logger.warning(
                    "Chapter prewarm step failed [%s | %s | %s | %s]: %s",
                    grade, subject, chapter, step_title, exc,
                )
                time.sleep(REQUEST_DELAY_SECONDS * 2)

    except Exception as exc:
        logger.error("Chapter prewarm failed [%s | %s | %s]: %s", grade, subject, chapter, exc)
    finally:
        set_job_status(job_key, "idle")


def get_grade_status_summary(grades: list[str]) -> list[dict]:
    """
    Return cache/bank status for a list of grades for the admin dashboard.
    """
    statuses = get_all_job_statuses()
    result = []

    for grade in grades:
        grade_key = grade.replace(" ", "")
        lesson_job_key = f"lessons_{grade_key}"
        question_job_key = f"questions_{grade_key}"

        expected_lessons = count_expected_lessons(grade)
        cached_lessons = count_cached_lessons(grade)
        expected_questions = count_expected_questions(grade)
        banked_questions = count_banked_questions(grade)

        lessons_complete = expected_lessons > 0 and cached_lessons >= expected_lessons
        questions_complete = expected_questions > 0 and banked_questions >= expected_questions

        result.append({
            "grade": grade,
            "expected_lessons": expected_lessons,
            "cached_lessons": cached_lessons,
            "lessons_complete": lessons_complete,
            "lessons_running": statuses.get(lesson_job_key) == "running",
            "expected_questions": expected_questions,
            "banked_questions": banked_questions,
            "questions_complete": questions_complete,
            "questions_running": statuses.get(question_job_key) == "running",
        })

    return result
