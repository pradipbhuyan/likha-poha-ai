#!/usr/bin/env python3
"""
Prewarm the 17 newly-uploaded Grade 11/12 English chapters
============================================================
Covers all 5 content types for each chapter, via whichever provider is
currently configured in Admin > AI & Settings (ollama_cloud by default —
verified at startup, aborts if it resolves to openai instead):
  1. lesson_cache   — 5 lesson steps (Concept intro, Core explanation, ...)
  2. lesson_chapter_doc — converted from the lesson_cache steps above
  3. lesson_kb      — LKB chips (all 5 steps)
  4. question_bank  — MCQ/exam questions across Easy/Medium/Hard
  5. doubt_kb       — pre-answered anticipated student doubts

Usage:
    cd backend
    nohup .venv/bin/python3 scripts/prewarm_grade1112_english_new_chapters.py \
        >> /tmp/prewarm_g1112_english.log 2>&1 &
    tail -f /tmp/prewarm_g1112_english.log
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

LOG_FILE = "/tmp/prewarm_g1112_english.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("prewarm_g1112_english")

BOARD = "CBSE"
MODE = "CBSE"
SUBJECT = "English"

CHAPTERS = [
    ("Grade 11", "The Portrait of a Lady"),
    ("Grade 11", "We're Not Afraid to Die"),
    ("Grade 11", "Discovering Tut: the Saga Continues"),
    ("Grade 11", "The Ailing Planet: the Green Movement's Role"),
    ("Grade 11", "The Adventure"),
    ("Grade 11", "Silk Road"),
    ("Grade 12", "My Mother at Sixty-six"),
    ("Grade 12", "Keeping Quiet"),
    ("Grade 12", "A Thing of Beauty"),
    ("Grade 12", "A Roadside Stand"),
    ("Grade 12", "Aunt Jennifer's Tigers"),
    ("Grade 12", "The Third Level"),
    ("Grade 12", "The Tiger King"),
    ("Grade 12", "Journey to the End of the Earth"),
    ("Grade 12", "The Enemy"),
    ("Grade 12", "On the Face of It"),
    ("Grade 12", "Memories of Childhood"),
]

LESSON_STEPS = [
    "Concept introduction",
    "Core explanation",
    "Worked examples",
    "Exam-style problems",
    "Revision and recap",
]

QBANK_DIFFICULTIES = ["Easy", "Medium", "Hard"]
QBANK_TARGET_PER_DIFFICULTY = 30
QBANK_BATCH_SIZE = 10
DOUBT_KB_TARGET = 25

REQUEST_DELAY = 2.0


def verify_provider():
    from app.services.openai_service import force_refresh_settings, get_effective_settings
    force_refresh_settings()
    settings = get_effective_settings()
    provider = settings.get("provider", "openai")
    log.info("Configured provider: %s", provider)
    if provider == "openai":
        log.error(
            "Provider resolved to 'openai' — refusing to run (this script must "
            "use ollama_cloud or nvidia). Check Admin > AI & Settings."
        )
        sys.exit(1)
    model_key = f"{provider}_model"
    log.info("Model: %s", settings.get(model_key, "(default)"))
    return provider


def prewarm_lesson_steps(grade, chapter):
    from app.services.tutor_service import generate_step_lesson
    from app.services.lesson_cache_service import make_lesson_cache_key, get_cached_lesson

    done = 0
    for step in LESSON_STEPS:
        cache_key = make_lesson_cache_key(BOARD, grade, SUBJECT, chapter, MODE, step, "")
        if get_cached_lesson(cache_key):
            done += 1
            continue
        try:
            generate_step_lesson(
                grade=grade, subject=SUBJECT, chapter=chapter, mode=MODE,
                step_title=step, teacher_persona="", username="prewarm_g1112_english",
                board=BOARD,
            )
            done += 1
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            log.warning("    lesson step %r failed: %s", step, exc)
    return done


def prewarm_chapter_doc(grade, chapter):
    from app.services.chapter_doc_service import get_or_convert_chapter_doc
    try:
        doc = get_or_convert_chapter_doc(BOARD, grade, SUBJECT, chapter, MODE)
        return bool(doc)
    except Exception as exc:
        log.warning("    chapter doc failed: %s", exc)
        return False


def prewarm_lkb(grade, chapter):
    from app.services.lesson_kb_service import build_lkb_for_chapter
    try:
        result = build_lkb_for_chapter(grade, SUBJECT, chapter, MODE)
        return result
    except Exception as exc:
        log.warning("    LKB chips failed: %s", exc)
        return {"built": 0, "skipped": 0, "errors": 1}


def prewarm_question_bank(grade, chapter):
    from app.services.openai_service import ask_llm
    from app.services.question_bank_service import add_questions_to_bank
    from app.services.grade_db_router import get_content_db
    import json, re

    db = get_content_db(grade)
    total_added = 0

    for difficulty in QBANK_DIFFICULTIES:
        existing = (
            db.table("question_bank").select("id", count="exact")
            .eq("grade", grade).eq("board", BOARD).eq("subject", SUBJECT)
            .eq("chapter", chapter).eq("difficulty", difficulty).eq("status", "active")
            .execute()
        )
        have = existing.count or 0
        need = QBANK_TARGET_PER_DIFFICULTY - have
        if need <= 0:
            continue

        batches = (need + QBANK_BATCH_SIZE - 1) // QBANK_BATCH_SIZE
        for b in range(batches):
            batch_size = min(QBANK_BATCH_SIZE, need - b * QBANK_BATCH_SIZE)
            system_prompt = (
                "You create original CBSE exam questions for exam preparation on a "
                "literature chapter. Return ONLY a valid JSON array. No markdown.\n"
                'JSON schema: [{"id":1,"section":"MCQ","question":"...",'
                '"options":{"A":"...","B":"...","C":"...","D":"..."},'
                '"answer":"A","explanation":"...","marks":1}]'
            )
            user_prompt = (
                f"Create {batch_size} unique {difficulty} exam questions for CBSE "
                f"{grade} {SUBJECT}, chapter {chapter!r} (variant batch {b+1}).\n"
                f"Base questions on the actual chapter content (comprehension, theme, "
                f"literary device, author's craft). Return ONLY a JSON array of "
                f"{batch_size} items."
            )
            try:
                raw = ask_llm(system_prompt, user_prompt, username="prewarm_g1112_english", feature="question_bank_prewarm")
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                s, e = raw.find("["), raw.rfind("]")
                questions = json.loads(raw[s:e + 1]) if s != -1 and e != -1 else []
            except Exception as exc:
                log.warning("    qbank batch failed (%s, %s): %s", difficulty, b, exc)
                questions = []

            if questions:
                add_questions_to_bank(
                    questions=questions, board=BOARD, grade=grade,
                    subject=SUBJECT, chapter=chapter,
                    difficulty=difficulty, exam_type="General",
                )
                total_added += len(questions)
            time.sleep(REQUEST_DELAY)

    return total_added


def prewarm_doubt_kb(grade, chapter):
    from app.services.doubt_kb_service import prewarm_doubt_kb_for_chapter
    try:
        return prewarm_doubt_kb_for_chapter(
            grade=grade, subject=SUBJECT, chapter=chapter, mode=MODE, board=BOARD,
            num_questions=DOUBT_KB_TARGET, username="prewarm_g1112_english",
        )
    except Exception as exc:
        log.warning("    doubt_kb failed: %s", exc)
        return {"generated": 0, "skipped_existing": 0, "errors": 1}


def main():
    log.info("=" * 70)
    log.info("Prewarm — 17 new Grade 11/12 English chapters")
    log.info("Log file: %s", LOG_FILE)
    log.info("=" * 70)

    provider = verify_provider()

    for i, (grade, chapter) in enumerate(CHAPTERS, 1):
        log.info("\n[%d/%d] %s — %r", i, len(CHAPTERS), grade, chapter)

        steps_done = prewarm_lesson_steps(grade, chapter)
        log.info("  lesson steps: %d/%d cached", steps_done, len(LESSON_STEPS))

        doc_ok = prewarm_chapter_doc(grade, chapter)
        log.info("  chapter doc: %s", "ok" if doc_ok else "FAILED")

        lkb = prewarm_lkb(grade, chapter)
        log.info("  LKB chips: built=%d skipped=%d errors=%d",
                 lkb.get("built", 0), lkb.get("skipped", 0), lkb.get("errors", 0))

        qbank_added = prewarm_question_bank(grade, chapter)
        log.info("  question bank: +%d questions", qbank_added)

        doubt = prewarm_doubt_kb(grade, chapter)
        log.info("  doubt_kb: generated=%d skipped=%d errors=%d",
                 doubt.get("generated", 0), doubt.get("skipped_existing", 0), doubt.get("errors", 0))

    log.info("\n" + "=" * 70)
    log.info("PREWARM COMPLETE — provider=%s", provider)
    log.info("=" * 70)


if __name__ == "__main__":
    main()
