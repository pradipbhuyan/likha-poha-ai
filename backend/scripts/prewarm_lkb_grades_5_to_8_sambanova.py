#!/usr/bin/env python3
"""
prewarm_lkb_grades_5_to_8_sambanova.py
═══════════════════════════════════════════════════════════════════════════════
LKB prewarm for Grades 5–8 using SambaNova Cloud (Meta-Llama-3.3-70B-Instruct).

SambaNova free tier: ~1M tokens/day.  Get key at cloud.sambanova.ai.
Key is read from Admin Settings DB (AI Studio → SambaNova API Key).

Usage (from backend/ directory):
    python3 scripts/prewarm_lkb_grades_5_to_8_sambanova.py &
    tail -f prewarm_lkb_5_to_8_sambanova.log

Override model:
    export SAMBANOVA_PREWARM_MODEL=Meta-Llama-3.3-70B-Instruct
═══════════════════════════════════════════════════════════════════════════════
"""

import atexit
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

GRADES          = ["Grade 5", "Grade 6", "Grade 7", "Grade 8"]
MODE            = "CBSE"
SAMBANOVA_MODEL = os.getenv("SAMBANOVA_PREWARM_MODEL", "Meta-Llama-3.3-70B-Instruct")
LOG_FILE        = os.path.join(ROOT, "prewarm_lkb_5_to_8_sambanova.log")
HEARTBEAT_SECS  = 60
DELAY_BETWEEN_CHAPTERS = 0.5   # SambaNova is fast — minimal delay needed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("lkb_prewarm_sn")

_caff_proc = None

def _start_caffeinate():
    global _caff_proc
    try:
        _caff_proc = subprocess.Popen(["caffeinate", "-i"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("caffeinate started (pid=%d) — Mac will not sleep.", _caff_proc.pid)
    except FileNotFoundError:
        log.warning("caffeinate not found.")

def _stop_caffeinate():
    if _caff_proc and _caff_proc.poll() is None:
        _caff_proc.terminate()

atexit.register(_stop_caffeinate)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


def _patch_settings_for_sambanova() -> None:
    """Override _settings_cache to use SambaNova as the LLM provider."""
    from app.services import openai_service as _svc  # noqa

    _svc.force_refresh_settings()
    api_key = _svc._settings_cache.get("sambanova_api_key") or ""
    model   = _svc._settings_cache.get("sambanova_model") or SAMBANOVA_MODEL

    if not api_key:
        api_key = os.getenv("SAMBANOVA_API_KEY", "")
    if not api_key:
        log.error(
            "SAMBANOVA_API_KEY not set.\n"
            "  Set it in Admin Console → AI Studio → SambaNova API Key\n"
            "  Or: export SAMBANOVA_API_KEY=sn-..."
        )
        sys.exit(1)

    if model:
        log.info("Using sambanova_model from DB: %s", model)
    else:
        model = SAMBANOVA_MODEL

    _svc._settings_cache.update({
        "provider":         "sambanova",
        "sambanova_api_key": api_key,
        "sambanova_model":   model,
        "api_enabled":       True,
        "loaded_at":         time.time() + 86400,
    })
    log.info("Provider patched → sambanova  model=%s", model)


class Progress:
    def __init__(self):
        self.grade_total = self.grade_done = 0
        self.chapter_total = self.chapter_done = 0
        self.built = self.skipped = self.errors = 0
        self.start_time = self.last_beat = time.time()

    def heartbeat_if_due(self):
        now = time.time()
        if now - self.last_beat >= HEARTBEAT_SECS:
            elapsed = int(now - self.start_time)
            log.info(
                "♥ heartbeat | elapsed=%ds | grades=%d/%d | chapters=%d/%d | "
                "built=%d skipped=%d errors=%d",
                elapsed,
                self.grade_done, self.grade_total,
                self.chapter_done, self.chapter_total,
                self.built, self.skipped, self.errors,
            )
            self.last_beat = now

    def eta(self):
        if self.chapter_done == 0:
            return "calculating…"
        elapsed   = time.time() - self.start_time
        remaining = self.chapter_total - self.chapter_done
        secs_each = elapsed / self.chapter_done
        eta_secs  = int(remaining * secs_each)
        h, r = divmod(eta_secs, 3600)
        return f"~{h}h {r//60}m"


def _count_existing_chips(grade, subject, chapter):
    try:
        from app.services.grade_db_router import get_content_db  # noqa
        db = get_content_db(grade)
        r = (db.table("lesson_kb").select("id", count="exact")
               .eq("grade", grade).eq("subject", subject).eq("chapter", chapter)
               .execute())
        return r.count or 0
    except Exception:
        return 0


def _get_syllabus(grade):
    from app.services.prewarm_service import get_syllabus_for_grade  # noqa
    return get_syllabus_for_grade(grade).get("CBSE", {})


def prewarm_grade(grade, prog):
    from app.services.lesson_kb_service import build_lkb_for_chapter  # noqa
    from app.services.lesson_kb_service import _get_lesson_steps, CHIPS_PER_STEP  # noqa

    syllabus = _get_syllabus(grade)
    total_chapters = sum(len(c) for c in syllabus.values())
    prog.chapter_total += total_chapters
    log.info("━━━ %s  (%d subjects, %d chapters) ━━━", grade, len(syllabus), total_chapters)

    gb = gs = ge = 0
    for subject, chapters in syllabus.items():
        log.info("  Subject: %s  (%d chapters)", subject, len(chapters))
        for i, chapter in enumerate(chapters, 1):
            steps    = _get_lesson_steps(grade)
            expected = len(steps) * CHIPS_PER_STEP
            existing = _count_existing_chips(grade, subject, chapter)
            if existing >= expected:
                log.info("    [SKIP] %d/%d  %s  (already %d chips)", i, len(chapters), chapter, existing)
                prog.skipped  += existing
                gs             += existing
                prog.chapter_done += 1
                prog.heartbeat_if_due()
                continue
            log.info("    [BUILD] %d/%d  %s  (%d chips existing, need %d)",
                     i, len(chapters), chapter, existing, expected)
            try:
                result = build_lkb_for_chapter(grade, subject, chapter, MODE)
                b, s, e = result["built"], result["skipped"], result["errors"]
                prog.built  += b; gb += b
                prog.skipped += s; gs += s
                prog.errors += e; ge += e
                prog.chapter_done += 1
                status = "✓" if e == 0 else "⚠"
                log.info("      %s built=%d skipped=%d errors=%d  ETA=%s", status, b, s, e, prog.eta())
            except Exception as exc:
                log.error("    ✗ FAILED: %s — %s", chapter, exc)
                prog.errors += 1; ge += 1; prog.chapter_done += 1
            prog.heartbeat_if_due()
            if DELAY_BETWEEN_CHAPTERS > 0:
                time.sleep(DELAY_BETWEEN_CHAPTERS)

    prog.grade_done += 1
    return {"grade": grade, "built": gb, "skipped": gs, "errors": ge}


def main():
    log.info("=" * 70)
    log.info("LKB Prewarm  Grades 5–8  via SambaNova Cloud (%s)", SAMBANOVA_MODEL)
    log.info("Log file: %s", LOG_FILE)
    log.info("Started:  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 70)

    _start_caffeinate()
    try:
        from app.services.ssl_service import enable_system_truststore  # noqa
        enable_system_truststore()
    except Exception:
        pass

    _patch_settings_for_sambanova()

    prog = Progress()
    prog.grade_total = len(GRADES)

    results = []
    for grade in GRADES:
        try:
            r = prewarm_grade(grade, prog)
            results.append(r)
            log.info("  Grade %s done: built=%d skipped=%d errors=%d",
                     grade, r["built"], r["skipped"], r["errors"])
        except KeyboardInterrupt:
            log.warning("Interrupted during %s.", grade)
            break
        except Exception as exc:
            log.error("Grade %s failed: %s", grade, exc)
            results.append({"grade": grade, "built": 0, "skipped": 0, "errors": -1})

    elapsed = int(time.time() - prog.start_time)
    h, r = divmod(elapsed, 3600)
    log.info("\n" + "=" * 70)
    log.info("PREWARM COMPLETE  —  %dh %dm elapsed", h, r // 60)
    log.info("  %-12s  %8s  %8s  %8s", "Grade", "Built", "Skipped", "Errors")
    log.info("  %-12s  %8s  %8s  %8s", "─"*12, "─"*8, "─"*8, "─"*8)
    for res in results:
        log.info("  %-12s  %8d  %8d  %8d", res["grade"], res["built"], res["skipped"], res["errors"])
    log.info("  %-12s  %8d  %8d  %8d", "TOTAL",
             sum(r["built"] for r in results),
             sum(r["skipped"] for r in results),
             sum(r["errors"] for r in results))
    log.info("=" * 70)
    log.info("Log saved to: %s", LOG_FILE)


if __name__ == "__main__":
    main()
