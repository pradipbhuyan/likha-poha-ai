#!/usr/bin/env python3
"""
prewarm_lkb_grades_5_to_8_ollama.py
═════════════════════════════════════════════════════════════════════════════
Background LKB (Lesson Knowledge Base) prewarm for Grades 5–8 using
Ollama Cloud as the AI provider (free tier — gemma3:4b / gemma3:12b).

What it does
────────────
• Uses caffeinate -i to prevent Mac from sleeping during the run.
• Prewarms LKB chips for all CBSE chapters in Grade 5, 6, 7, and 8.
• Overrides the AI provider to ollama_cloud so no OpenAI tokens are spent.
• Logs progress to prewarm_lkb_5_to_8.log AND to stdout.
• Shows a periodic live heartbeat every 60s so you can confirm it's running.
• Skips chapters already fully pre-warmed (idempotent).

Usage (from backend/ directory)
────────────
    # Run in background — keep terminal open OR use screen/tmux
    python3 scripts/prewarm_lkb_grades_5_to_8_ollama.py &

    # OR foreground (blocks terminal, Ctrl+C to stop)
    python3 scripts/prewarm_lkb_grades_5_to_8_ollama.py

    # Check progress any time
    tail -f prewarm_lkb_5_to_8.log

Ollama Cloud model
────────────
Set OLLAMA_CLOUD_API_KEY in your .env or export it:
    export OLLAMA_CLOUD_API_KEY=your_key_here

Free models: gemma3:4b (fastest), gemma3:12b (better quality), gpt-oss:20b
═════════════════════════════════════════════════════════════════════════════
"""

import atexit
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

# ── Ensure project root is in path ────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

# ── Config ────────────────────────────────────────────────────────────────────
GRADES          = ["Grade 5", "Grade 6", "Grade 7", "Grade 8"]
MODE            = "CBSE"
OLLAMA_MODEL    = os.getenv("OLLAMA_PREWARM_MODEL", "gemma3:4b")
OLLAMA_API_KEY  = os.getenv("OLLAMA_CLOUD_API_KEY", "")
LOG_FILE        = os.path.join(ROOT, "prewarm_lkb_5_to_8.log")
HEARTBEAT_SECS  = 60        # Print a heartbeat line every N seconds
DELAY_BETWEEN_CHAPTERS = 1  # Seconds between chapters (polite pacing)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("lkb_prewarm")

# ── caffeinate (keep Mac awake) ───────────────────────────────────────────────
_caff_proc: subprocess.Popen | None = None


def _start_caffeinate() -> None:
    """Start caffeinate -i to prevent display+disk sleep while script runs."""
    global _caff_proc
    try:
        _caff_proc = subprocess.Popen(
            ["caffeinate", "-i"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("caffeinate started (pid=%d) — Mac will not sleep.", _caff_proc.pid)
    except FileNotFoundError:
        log.warning("caffeinate not found — Mac may sleep during prewarm. "
                    "Run this on macOS for sleep prevention.")


def _stop_caffeinate() -> None:
    if _caff_proc and _caff_proc.poll() is None:
        _caff_proc.terminate()
        log.info("caffeinate stopped.")


atexit.register(_stop_caffeinate)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


# ── Patch openai_service to use ollama_cloud ───────────────────────────────────

def _patch_settings_for_ollama() -> None:
    """
    Override the in-memory settings cache to route all LLM calls to
    Ollama Cloud instead of the default provider (OpenAI / gpt-4.1-nano).
    Must be called AFTER importing openai_service.
    """
    from app.services import openai_service as _svc  # noqa: PLC0415

    if not OLLAMA_API_KEY:
        log.error(
            "OLLAMA_CLOUD_API_KEY is not set.\n"
            "  Export it:  export OLLAMA_CLOUD_API_KEY=your_key\n"
            "  Or add to:  backend/.env\n"
            "  Free keys:  https://ollama.com/settings/api-keys"
        )
        sys.exit(1)

    _svc._settings_cache.update({
        "provider":              "ollama_cloud",
        "ollama_cloud_api_key":  OLLAMA_API_KEY,
        "ollama_cloud_model":    OLLAMA_MODEL,
        "api_enabled":           True,
        "loaded_at":             time.time() + 86400,  # TTL far future — don't reload
    })
    log.info("Provider patched → ollama_cloud  model=%s", OLLAMA_MODEL)


# ── Progress counters ─────────────────────────────────────────────────────────
class Progress:
    def __init__(self):
        self.grade_total   = 0
        self.grade_done    = 0
        self.chapter_total = 0
        self.chapter_done  = 0
        self.built         = 0
        self.skipped       = 0
        self.errors        = 0
        self.start_time    = time.time()
        self.last_beat     = time.time()

    def heartbeat_if_due(self) -> None:
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

    def eta(self) -> str:
        if self.chapter_done == 0:
            return "calculating…"
        elapsed   = time.time() - self.start_time
        remaining = self.chapter_total - self.chapter_done
        secs_each = elapsed / self.chapter_done
        eta_secs  = int(remaining * secs_each)
        hrs, rem  = divmod(eta_secs, 3600)
        mins      = rem // 60
        return f"~{hrs}h {mins}m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_existing_chips(grade: str, subject: str, chapter: str) -> int:
    """Count total LKB chips already stored for this chapter (all steps)."""
    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        r = (db.table("lesson_kb")
               .select("id", count="exact")
               .eq("grade",   grade)
               .eq("subject", subject)
               .eq("chapter", chapter)
               .execute())
        return r.count or 0
    except Exception:
        return 0


def _get_syllabus(grade: str) -> dict:
    """Return {subject: [chapter, …]} for the given grade."""
    from app.services.prewarm_service import get_syllabus_for_grade  # noqa: PLC0415
    syllabus = get_syllabus_for_grade(grade)
    return syllabus.get("CBSE", {})


# ── Main prewarm loop ─────────────────────────────────────────────────────────

def prewarm_grade(grade: str, prog: Progress) -> dict:
    """Prewarm all LKB chips for one grade. Returns per-grade summary."""
    from app.services.lesson_kb_service import build_lkb_for_chapter  # noqa: PLC0415

    syllabus = _get_syllabus(grade)
    total_chapters = sum(len(chaps) for chaps in syllabus.values())
    prog.chapter_total += total_chapters

    log.info("━━━ %s  (%d subjects, %d chapters) ━━━",
             grade, len(syllabus), total_chapters)

    grade_built = grade_skipped = grade_errors = 0

    for subject, chapters in syllabus.items():
        log.info("  Subject: %s  (%d chapters)", subject, len(chapters))

        for i, chapter in enumerate(chapters, 1):
            # Quick check: already fully warmed?
            from app.services.lesson_kb_service import _get_lesson_steps, CHIPS_PER_STEP  # noqa: PLC0415
            steps        = _get_lesson_steps(grade)
            expected     = len(steps) * CHIPS_PER_STEP
            already_done = _count_existing_chips(grade, subject, chapter)

            if already_done >= expected:
                log.info("    [SKIP] %d/%d  %s  (already %d chips)", i, len(chapters), chapter, already_done)
                prog.skipped    += already_done
                grade_skipped   += already_done
                prog.chapter_done += 1
                prog.heartbeat_if_due()
                continue

            log.info("    [BUILD] %d/%d  %s  (%d chips existing, need %d)",
                     i, len(chapters), chapter, already_done, expected)

            try:
                result = build_lkb_for_chapter(grade, subject, chapter, MODE)
                b = result.get("built", 0)
                s = result.get("skipped", 0)
                e = result.get("errors", 0)

                prog.built      += b
                prog.skipped    += s
                prog.errors     += e
                grade_built     += b
                grade_skipped   += s
                grade_errors    += e
                prog.chapter_done += 1

                status = "✓" if e == 0 else "⚠"
                log.info("      %s built=%d skipped=%d errors=%d  ETA=%s",
                         status, b, s, e, prog.eta())

            except Exception as exc:
                log.error("    ✗ FAILED: %s — %s", chapter, exc)
                prog.errors     += 1
                grade_errors    += 1
                prog.chapter_done += 1

            prog.heartbeat_if_due()
            if DELAY_BETWEEN_CHAPTERS > 0:
                time.sleep(DELAY_BETWEEN_CHAPTERS)

    prog.grade_done += 1
    return {"grade": grade, "built": grade_built, "skipped": grade_skipped, "errors": grade_errors}


def main() -> None:
    log.info("=" * 70)
    log.info("LKB Prewarm  Grades 5–8  via Ollama Cloud (%s)", OLLAMA_MODEL)
    log.info("Log file: %s", LOG_FILE)
    log.info("Started:  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 70)

    # Start caffeinate first
    _start_caffeinate()

    # Load SSL trust store
    try:
        from app.services.ssl_service import enable_system_truststore  # noqa: PLC0415
        enable_system_truststore()
    except Exception:
        pass

    # Patch provider → ollama_cloud BEFORE any LLM import
    _patch_settings_for_ollama()

    prog = Progress()

    # Count total grades
    prog.grade_total = len(GRADES)

    # Verify Ollama Cloud connectivity with a quick ping
    log.info("Verifying Ollama Cloud connectivity (model=%s)…", OLLAMA_MODEL)
    try:
        import requests  # noqa: PLC0415
        r = requests.post(
            "https://api.ollama.com/api/chat",
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
            json={"model": OLLAMA_MODEL, "stream": False,
                  "messages": [{"role": "user", "content": "ping"}]},
            timeout=30,
        )
        if r.status_code == 200:
            log.info("✓ Ollama Cloud connected  model=%s", OLLAMA_MODEL)
        else:
            log.warning("Ollama Cloud returned HTTP %d — %s", r.status_code, r.text[:200])
    except Exception as exc:
        log.warning("Ollama Cloud ping failed: %s — continuing anyway", exc)

    # Run prewarm for each grade
    results = []
    for grade in GRADES:
        try:
            result = prewarm_grade(grade, prog)
            results.append(result)
            log.info("  Grade %s done: built=%d skipped=%d errors=%d",
                     grade, result["built"], result["skipped"], result["errors"])
        except KeyboardInterrupt:
            log.warning("Interrupted by user during %s.", grade)
            break
        except Exception as exc:
            log.error("Grade %s failed: %s", grade, exc)
            results.append({"grade": grade, "built": 0, "skipped": 0, "errors": -1})

    # Final summary
    elapsed = int(time.time() - prog.start_time)
    hrs, rem = divmod(elapsed, 3600)
    mins = rem // 60

    log.info("")
    log.info("=" * 70)
    log.info("PREWARM COMPLETE  —  %dh %dm elapsed", hrs, mins)
    log.info("")
    log.info("  %-12s  %8s  %8s  %8s", "Grade", "Built", "Skipped", "Errors")
    log.info("  %-12s  %8s  %8s  %8s", "─" * 12, "─" * 8, "─" * 8, "─" * 8)
    for r in results:
        log.info("  %-12s  %8d  %8d  %8d", r["grade"], r["built"], r["skipped"], r["errors"])
    log.info("  %-12s  %8d  %8d  %8d",
             "TOTAL",
             sum(r["built"]   for r in results),
             sum(r["skipped"] for r in results),
             sum(r["errors"]  for r in results))
    log.info("=" * 70)
    log.info("Log saved to: %s", LOG_FILE)
    log.info("")


if __name__ == "__main__":
    main()
