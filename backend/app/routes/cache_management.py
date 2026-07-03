"""
Cache Management Routes
=======================
Admin-only endpoints for grade-level lesson pre-warming,
question bank building, status tracking, and cache clearing.
"""

import threading as _threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from app.services.auth_service import require_admin
from app.services.openai_service import get_effective_settings
from app.services.prewarm_service import (
    prewarm_lessons_for_grade,
    prewarm_single_chapter,
    build_question_bank_for_grade,
    build_question_bank_for_chapter,
    get_grade_status_summary,
    get_chapters_for_grade,
    clear_lesson_cache_for_grade,
    clear_question_bank_for_grade,
    is_job_running,
    set_job_status,
)
from app.services.lesson_cache_service import (
    restore_archived_lessons_for_grade,
    get_archived_lesson_count,
)
from app.services.doubt_kb_service import (
    get_doubt_kb_stats,
    get_doubt_kb_grade_stats,
    prewarm_doubt_kb_for_grade,
)


class PrewarmChapterRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str

router = APIRouter()

# Cache & Question Bank management only covers Grades 5–10.
# Grades 1–4 don't have uploaded RAG content yet so showing them
# in the prewarm panel would be misleading.
ALL_GRADES = [f"Grade {n}" for n in range(5, 13)]


@router.get("/status")
def get_cache_status(admin=Depends(require_admin)):
    """
    Return lesson cache and question bank status for all grades.

    Used by the admin cache management panel to show progress,
    disable completed generate buttons, and highlight running jobs.
    """
    return {
        "success": True,
        "grades": get_grade_status_summary(ALL_GRADES),
    }


@router.post("/prewarm/lessons/{grade_slug}")
def start_lesson_prewarm(
    grade_slug: str,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start lesson pre-warming for a grade as a background task.

    The API returns immediately. Generation runs in the background.
    Poll GET /status to see progress. Already-cached steps are skipped.
    Disabled automatically once the grade is complete.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"lessons_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Lesson pre-warming for {grade} is already running.",
        }

    background_tasks.add_task(prewarm_lessons_for_grade, grade)

    return {
        "success": True,
        "message": f"Lesson pre-warming started for {grade}. Poll /status for progress.",
        "grade": grade,
    }


@router.post("/prewarm/questions/{grade_slug}")
def start_question_bank_build(
    grade_slug: str,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start question bank building for a grade as a background task.

    The API returns immediately. Generation runs in the background.
    Poll GET /status to see progress.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    ai_settings = get_effective_settings()
    if not ai_settings.get("api_enabled", True):
        return {
            "success": False,
            "message": "AI API is currently disabled. Enable it in Admin Control → AI API Settings before building the question bank.",
        }

    job_key = f"questions_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Question bank building for {grade} is already running.",
        }

    background_tasks.add_task(build_question_bank_for_grade, grade)

    return {
        "success": True,
        "message": f"Question bank building started for {grade}. Poll /status for progress.",
        "grade": grade,
    }


@router.get("/chapters/{grade_slug}")
def list_grade_chapters(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Return the list of {mode, subject, chapter} options for a grade.

    Used by the chapter-by-chapter prewarm panel to populate the dropdowns.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    chapters = get_chapters_for_grade(grade)
    return {
        "success": True,
        "grade": grade,
        "chapters": chapters,
    }


@router.post("/build-questions/chapter")
def start_chapter_question_bank_build(
    data: PrewarmChapterRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """Start question bank building for exactly one chapter as a background task."""
    if data.grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {data.grade}")

    ai_settings = get_effective_settings()
    if not ai_settings.get("api_enabled", True):
        return {
            "success": False,
            "message": "AI API is currently disabled. Enable it in Admin Control → AI API Settings before building the question bank.",
        }

    safe_subject = data.subject[:12].replace(" ", "_")
    safe_chapter = data.chapter[:12].replace(" ", "_")
    job_key = f"qbank_{data.grade.replace(' ', '')}_{safe_subject}_{safe_chapter}"

    if is_job_running(job_key):
        return {"success": False, "message": "A question bank build is already running for this chapter."}

    background_tasks.add_task(build_question_bank_for_chapter, data.grade, data.mode, data.subject, data.chapter)
    return {
        "success": True,
        "message": f"Question bank build started: {data.subject} — {data.chapter} (60 questions: Easy/Medium/Hard).",
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
    }


@router.post("/prewarm/chapter")
def start_single_chapter_prewarm(
    data: PrewarmChapterRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start lesson pre-warming for exactly one chapter as a background task.

    Allows admins to test one chapter at a time (5 steps × nano model)
    before running the full grade prewarm.
    """
    if data.grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {data.grade}")

    safe_subject = data.subject[:12].replace(" ", "_")
    safe_chapter = data.chapter[:12].replace(" ", "_")
    job_key = f"chapter_{data.grade.replace(' ', '')}_{safe_subject}_{safe_chapter}"

    if is_job_running(job_key):
        return {
            "success": False,
            "message": "A prewarm job is already running for this chapter.",
        }

    background_tasks.add_task(
        prewarm_single_chapter,
        data.grade,
        data.mode,
        data.subject,
        data.chapter,
    )

    return {
        "success": True,
        "message": f"Chapter prewarm started: {data.subject} — {data.chapter}.",
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "job_key": job_key,
    }


# ---------------------------------------------------------------------------
# Doubt Knowledge Base (DKB) endpoints
# ---------------------------------------------------------------------------

@router.get("/doubt-kb/stats")
def get_doubt_kb_overview(admin=Depends(require_admin)):
    """
    Return aggregate Doubt Knowledge Base stats for the admin console.
    Shows total Q&A pairs, DB hit rate, LLM call rate, and estimated savings.
    """
    return {
        "success": True,
        **get_doubt_kb_stats(),
    }


@router.get("/doubt-kb/stats/{grade_slug}")
def get_doubt_kb_grade_overview(grade_slug: str, admin=Depends(require_admin)):
    """Return per-subject DKB entry and hit counts for one grade."""
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")
    return {
        "success": True,
        **get_doubt_kb_grade_stats(grade),
    }


@router.post("/prewarm/doubt-kb/{grade_slug}")
def start_doubt_kb_prewarm(
    grade_slug: str,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
):
    """
    Start Doubt Knowledge Base pre-warming for a grade as a background task.

    Generates 25 common student questions + answers per chapter using
    gpt-4.1-nano + RAG context.  Already-covered chapters are skipped.
    Safe to re-run.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    ai_settings = get_effective_settings()
    if not ai_settings.get("api_enabled", True):
        return {
            "success": False,
            "message": "AI API is currently disabled. Enable it in Admin Control before building the Doubt KB.",
        }

    job_key = f"doubt_kb_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Doubt KB pre-warming for {grade} is already running.",
        }

    def _run_doubt_kb_prewarm(g: str):
        set_job_status(job_key, "running")
        try:
            prewarm_doubt_kb_for_grade(g)
        finally:
            set_job_status(job_key, "idle")

    # Run in a dedicated OS thread so blocking time.sleep() calls inside
    # ask_llm() retry logic do NOT block the FastAPI event loop or uvicorn
    # worker threads, which would freeze the admin panel and all other API calls.
    import threading as _threading  # noqa: PLC0415
    t = _threading.Thread(target=_run_doubt_kb_prewarm, args=(grade,), daemon=True)
    t.start()
    return {"success": True, "message": f"DKB prewarm started for {grade}.", "job_key": job_key}




@router.get("/cache/lessons/audit")
def audit_lesson_cache(
    grade: str | None = None,
    admin=Depends(require_admin),
):
    """
    Return a summary of lesson_cache contents including duplicate rows.

    Shows:
    - Total active rows per grade
    - Rows with 0 ## headings (flat/stale content)
    - Chapters that have duplicate step rows
    Admin-only. Read-only.
    """
    import re as _re  # noqa: PLC0415
    from app.services.grade_db_router import get_content_db  # noqa: PLC0415

    GRADES = ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]

    summary = []
    total_active = 0
    total_flat = 0
    total_duplicate_chapters = 0

    for g in ([grade] if grade else GRADES):
        try:
            db = get_content_db(g)
            resp = (db.table("lesson_cache")
                    .select("id, grade, subject, chapter, step_title, lesson_content, status, access_count")
                    .eq("grade", g)
                    .eq("status", "active")
                    .limit(2000)
                    .execute())
            rows = resp.data or []
        except Exception:
            continue

        flat_rows = []
        step_key_counts: dict[str, int] = {}
        for row in rows:
            content = row.get("lesson_content", "") or ""
            heading_count = len(_re.findall(r"^#{1,3}\s+", content, _re.M))
            step_key = f"{row.get('subject')}|{row.get('chapter')}|{row.get('step_title')}"
            step_key_counts[step_key] = step_key_counts.get(step_key, 0) + 1
            if heading_count == 0:
                flat_rows.append({
                    "id": row.get("id"),
                    "subject": row.get("subject"),
                    "chapter": row.get("chapter"),
                    "step_title": row.get("step_title"),
                    "word_count": len(content.split()),
                    "access_count": row.get("access_count", 0),
                })

        duplicate_steps = {k: v for k, v in step_key_counts.items() if v > 1}
        total_active += len(rows)
        total_flat += len(flat_rows)
        total_duplicate_chapters += len(duplicate_steps)

        summary.append({
            "grade": g,
            "active_rows": len(rows),
            "flat_content_rows": len(flat_rows),
            "duplicate_steps": len(duplicate_steps),
            "flat_rows": flat_rows[:20],  # limit detail output
            "duplicate_step_keys": list(duplicate_steps.keys())[:20],
        })

    return {
        "success": True,
        "total_active_rows": total_active,
        "total_flat_content_rows": total_flat,
        "total_duplicate_step_keys": total_duplicate_chapters,
        "grades": summary,
        "note": "Flat content rows have 0 ## headings and should be marked stale. Use POST /cache/lessons/deduplicate to clean up.",
    }


@router.post("/cache/lessons/deduplicate")
def deduplicate_lesson_cache(
    grade: str | None = None,
    dry_run: bool = True,
    admin=Depends(require_admin),
):
    """
    Mark flat/stale lesson_cache rows as status='stale'.

    A row is considered stale if it has 0 ## section headings in lesson_content
    (old flat-text format generated before the structured lesson format was introduced).

    dry_run=True (default): show what would be marked stale without changing anything.
    dry_run=False: actually mark the rows as stale.

    Admin-only. Safe to run — only marks status, never deletes.
    """
    import re as _re  # noqa: PLC0415
    from app.services.grade_db_router import get_content_db  # noqa: PLC0415

    GRADES = ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]

    to_stale = []
    errors = []

    for g in ([grade] if grade else GRADES):
        try:
            db = get_content_db(g)
            resp = (db.table("lesson_cache")
                    .select("id, grade, subject, chapter, step_title, lesson_content, access_count")
                    .eq("grade", g)
                    .eq("status", "active")
                    .limit(2000)
                    .execute())
            rows = resp.data or []
        except Exception as e:
            errors.append(f"{g}: {e}")
            continue

        for row in rows:
            content = row.get("lesson_content", "") or ""
            heading_count = len(_re.findall(r"^#{1,3}\s+", content, _re.M))
            if heading_count == 0:
                to_stale.append({
                    "id": row["id"],
                    "grade": row.get("grade"),
                    "subject": row.get("subject"),
                    "chapter": row.get("chapter"),
                    "step_title": row.get("step_title"),
                    "word_count": len(content.split()),
                    "access_count": row.get("access_count", 0),
                })

    marked = 0
    if not dry_run and to_stale:
        for g in ([grade] if grade else GRADES):
            try:
                db = get_content_db(g)
                ids_for_grade = [r["id"] for r in to_stale if r["grade"] == g]
                if ids_for_grade:
                    db.table("lesson_cache").update({"status": "stale"}).in_("id", ids_for_grade).execute()
                    marked += len(ids_for_grade)
            except Exception as e:
                errors.append(f"mark stale {g}: {e}")

    return {
        "success": True,
        "dry_run": dry_run,
        "rows_to_mark_stale": len(to_stale),
        "rows_marked_stale": marked if not dry_run else 0,
        "rows": to_stale[:50],  # limit detail output
        "errors": errors,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"{len(to_stale)} flat-content rows {'would be' if dry_run else 'have been'} marked stale. "
            f"{'Run with dry_run=false to apply.' if dry_run else 'Lesson Lab will now show structured content only.'}"
        ),
    }


@router.delete("/cache/lessons/{grade_slug}")
def clear_lessons(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Archive (soft-delete) cached lessons for a grade.

    Lessons are marked 'archived' rather than permanently deleted so that
    token-expensive pre-generated content can be recovered at any time via
    POST /cache/lessons/{grade_slug}/restore.

    Use this before re-running pre-warming after RAG content is updated.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"lessons_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot clear cache while pre-warming is running for {grade}.",
        )

    archived = clear_lesson_cache_for_grade(grade)

    return {
        "success": True,
        "message": (
            f"Archived {archived} lesson(s) for {grade}. "
            f"They can be restored via POST /api/cache/cache/lessons/{grade_slug}/restore."
        ),
        "archived": archived,
        "grade": grade,
    }


@router.post("/cache/lessons/{grade_slug}/restore")
def restore_lessons(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Restore archived lessons for a grade back to active status.

    Allows recovery from an accidental 'Clear Lessons' click without
    spending tokens to regenerate content.  Archived rows have status='archived'
    and are invisible to students but remain in the database.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    archived_count = get_archived_lesson_count(grade)
    if archived_count == 0:
        return {
            "success": True,
            "message": f"No archived lessons found for {grade}.",
            "restored": 0,
            "grade": grade,
        }

    restored = restore_archived_lessons_for_grade(grade)

    return {
        "success": True,
        "message": (
            f"Restored {restored} lesson(s) for {grade}. "
            "They are now active and will be served to students."
        ),
        "restored": restored,
        "grade": grade,
    }


# ── LKB (Lesson Knowledge Base) endpoints ─────────────────────────────────────

@router.get("/lkb/overview/{grade_slug}")
def get_lkb_overview(grade_slug: str, admin=Depends(require_admin)):
    """Return LKB chip counts and chapter completion status for a grade."""
    from app.services.lesson_kb_service import (  # noqa: PLC0415
        count_lkb_chips, count_expected_lkb_chips, get_lkb_chapter_status,
    )
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    return {
        "success": True,
        "grade": grade,
        "chips_built": count_lkb_chips(grade),
        "chips_expected": count_expected_lkb_chips(grade),
        "chapters": get_lkb_chapter_status(grade),
    }


@router.post("/prewarm/lkb/{grade_slug}")
def start_lkb_build(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Trigger LKB pre-warm for an entire grade.
    Runs as a background thread — returns immediately.
    """
    from app.services.lesson_kb_service import build_lkb_for_grade  # noqa: PLC0415

    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"lkb_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"LKB build already running for {grade}.",
            "grade": grade,
        }

    def _run(g: str):
        set_job_status(job_key, "running")
        try:
            build_lkb_for_grade(g)
        finally:
            set_job_status(job_key, "idle")

    t = _threading.Thread(target=_run, args=(grade,), daemon=True)
    t.start()

    return {
        "success": True,
        "message": f"LKB build started for {grade}. Runs in background.",
        "grade": grade,
    }


@router.post("/prewarm/lkb/chapter")
def start_lkb_build_chapter(
    data: dict,
    admin=Depends(require_admin),
):
    """Build LKB chips for a single chapter. Body: {grade, subject, chapter}."""
    from app.services.lesson_kb_service import build_lkb_for_chapter  # noqa: PLC0415

    grade = data.get("grade", "")
    subject = data.get("subject", "")
    chapter = data.get("chapter", "")

    if not grade or not subject or not chapter:
        raise HTTPException(status_code=400, detail="grade, subject, and chapter are required.")

    job_key = f"lkb_{grade}_{subject}_{chapter}".replace(" ", "_")[:80]
    if is_job_running(job_key):
        return {"success": False, "message": "LKB build already running for this chapter."}

    def _run():
        set_job_status(job_key, "running")
        try:
            build_lkb_for_chapter(grade, subject, chapter)
        finally:
            set_job_status(job_key, "idle")

    t = _threading.Thread(target=_run, daemon=True)
    t.start()

    return {
        "success": True,
        "message": f"LKB build started for {chapter}.",
        "grade": grade, "subject": subject, "chapter": chapter,
    }


@router.delete("/cache/questions/{grade_slug}")
def clear_questions(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Clear all question bank entries for a grade.

    Use this to force re-generation after RAG content is updated,
    or to reset before re-running the bank builder.
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"questions_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot clear bank while building is running for {grade}.",
        )

    deleted = clear_question_bank_for_grade(grade)

    return {
        "success": True,
        "message": f"Cleared question bank for {grade}.",
        "deleted": deleted,
        "grade": grade,
    }


# ── Audio Cache endpoints ──────────────────────────────────────────────────────

@router.get("/audio/overview/{grade_slug}")
def get_audio_overview(grade_slug: str, admin=Depends(require_admin)):
    """
    Return pre-warmed audio counts for a grade (used by admin Cache Management page).
    Shows how many lesson steps have cached audio vs. how many are expected.
    """
    from app.services.audio_cache_service import get_audio_cache_overview  # noqa: PLC0415

    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    overview = get_audio_cache_overview(grade)
    by_grade = overview.get("by_grade", {})
    grade_data = by_grade.get(grade, {"files": 0, "bytes": 0})

    # Expected = number of cached lesson steps for this grade (same as cached_lessons)
    from app.services.prewarm_service import count_cached_lessons  # noqa: PLC0415
    expected = count_cached_lessons(grade)

    return {
        "success": True,
        "grade": grade,
        "audio_cached": grade_data["files"],
        "audio_expected": expected,
        "total_mb": round(grade_data["bytes"] / 1024 / 1024, 1),
    }


@router.post("/prewarm/audio/{grade_slug}")
def start_audio_prewarm(
    grade_slug: str,
    admin=Depends(require_admin),
):
    """
    Trigger TTS audio pre-warm for all cached lessons in a grade.
    Runs as a background thread — returns immediately.
    Already-cached steps are skipped (resume behaviour).
    """
    grade = grade_slug.replace("-", " ").title()
    if grade not in ALL_GRADES:
        raise HTTPException(status_code=400, detail=f"Invalid grade: {grade_slug}")

    job_key = f"audio_{grade.replace(' ', '')}"
    if is_job_running(job_key):
        return {
            "success": False,
            "message": f"Audio prewarm already running for {grade}.",
            "grade": grade,
        }

    def _run(g: str):
        import time as _time  # noqa: PLC0415
        from app.services.auth_service import admin_client as _db  # noqa: PLC0415
        from app.services.tts_service import generate_speech_file, clean_text_for_tts  # noqa: PLC0415
        from app.services.audio_cache_service import store_audio, get_cached_audio_url  # noqa: PLC0415
        import os as _os  # noqa: PLC0415
        import logging as _logging  # noqa: PLC0415

        _log = _logging.getLogger("audio_prewarm")
        set_job_status(job_key, "running")
        try:
            r = _db.table("lesson_cache").select(
                "grade,subject,chapter,step_title,lesson_content"
            ).eq("grade", g).eq("status", "active").execute()
            lessons = [
                row for row in (r.data or [])
                if row.get("lesson_content") and len(row["lesson_content"]) > 100
            ]
            _log.info(f"Audio prewarm {g}: {len(lessons)} lessons to process")
            for lesson in lessons:
                ch = lesson["chapter"]
                st = lesson["step_title"]
                subj = lesson["subject"]
                # Skip if already cached
                if get_cached_audio_url(g, subj, ch, st):
                    continue
                try:
                    clean = clean_text_for_tts(lesson["lesson_content"])
                    mp3_path = generate_speech_file(clean)
                    size_b = _os.path.getsize(mp3_path)
                    with open(mp3_path, "rb") as f:
                        mp3_bytes = f.read()
                    _os.remove(mp3_path)
                    store_audio(g, subj, ch, st, mp3_bytes)
                    _log.info(f"Audio cached: {ch}/{st} ({size_b//1024}KB)")
                except Exception as exc:
                    _log.warning(f"Audio prewarm failed {ch}/{st}: {exc}")
                _time.sleep(0.5)
        except Exception as exc:
            _log.error(f"Audio prewarm job failed for {g}: {exc}")
        finally:
            set_job_status(job_key, "idle")

    t = _threading.Thread(target=_run, args=(grade,), daemon=True)
    t.start()

    return {
        "success": True,
        "message": f"Audio prewarm started for {grade}. Runs in background — already-cached steps skipped.",
        "grade": grade,
    }
