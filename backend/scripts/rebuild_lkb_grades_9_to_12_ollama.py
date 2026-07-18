#!/usr/bin/env python3
"""
rebuild_lkb_grades_9_to_12_ollama.py
═════════════════════════════════════════════════════════════════════════════
Overnight LKB rebuild for Grades 9-12, using Ollama Cloud as the AI provider.

Why this exists
────────────
An audit (2026-07-17) found that lesson_kb_service._get_rag_context() imported
a function ('search_rag') that never existed, from the LKB feature's first
commit until it was fixed on 2026-07-10. Every single active chip in the
database — 21,293 rows, every grade, every subject — was generated during
that window with an always-empty RAG context, i.e. pure LLM imagination with
zero textbook grounding. This script re-generates Grades 9-12 (16,523 of
those chips) through the now-fixed pipeline.

Two behavior changes shipped alongside this script (lesson_kb_service.py):
  1. The "generate generic questions anyway" fallback for subjects with no
     RAG match is gone — ALL subjects now skip (return no chips) rather than
     guess, not just STORY_DEPENDENT_SUBJECTS.
  2. Chip count scales with how much RAG content came back (_target_chip_count)
     instead of always demanding 5 — a thin chapter only supports a couple of
     distinct, well-grounded questions.

Old chips were soft-deleted (status='stale', reversible) for Grade 9/10/11/12
BEFORE this script runs, so lesson_kb_service._count_existing (which only
counts status='active') sees 0 existing chips per step and regenerates
everything. That existing per-step skip-check IS this script's resumability
mechanism — if this process crashes and is re-run, already-rebuilt steps
already have active chips and are skipped; nothing is redone or duplicated.

What it does
────────────
• Uses caffeinate -i to prevent Mac from sleeping during the run.
• Rebuilds LKB chips for all CBSE chapters in Grade 9, 10, 11, and 12.
• Overrides the AI provider to ollama_cloud (model configurable below).
• Logs progress to rebuild_lkb_9_to_12.log AND to stdout.
• Heartbeat every 60s with elapsed/built/skipped/errors/ETA.
• Skips chapters/steps that already have active chips (idempotent — see above).

Usage (from backend/ directory)
────────────
    export OLLAMA_CLOUD_API_KEY=your_key_here
    python3 scripts/rebuild_lkb_grades_9_to_12_ollama.py &

    # Check progress any time
    tail -f rebuild_lkb_9_to_12.log
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
_grades_env = os.getenv("LKB_GRADES", "")
GRADES = [g.strip() for g in _grades_env.split(",") if g.strip()] or ["Grade 9", "Grade 10", "Grade 11", "Grade 12"]
MODE            = "CBSE"

# Provider: "ollama_cloud" or "nvidia". Ollama's free tier was exhausted
# mid-run on 2026-07-17 (silent — ask_llm's fallback path swallowed the
# failure with no ERROR/WARNING logged, only zero built chips for the two
# grades that fell in the exhausted window). Switched to NVIDIA NIM, which
# offers deepseek-v4-pro (a frontier-tier model that was subscription-gated
# on Ollama) for free, and is meaningfully faster when it responds
# (0.6-3.4s vs 20-65s for gpt-oss:120b) — though it shows intermittent full
# timeouts under free-tier load, handled by CHAPTER_RETRY below.
PROVIDER        = os.getenv("LKB_PROVIDER", "nvidia")
OLLAMA_MODEL    = os.getenv("OLLAMA_PREWARM_MODEL", "gpt-oss:20b")
OLLAMA_API_KEY  = os.getenv("OLLAMA_CLOUD_API_KEY", "")
NVIDIA_MODEL    = os.getenv("NVIDIA_PREWARM_MODEL", "deepseek-ai/deepseek-v4-pro")
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
PILOT_CHAPTER    = os.getenv("LKB_PILOT_CHAPTER", "")   # if set: (grade|subject|chapter), only run this one
LOG_FILE        = os.path.join(ROOT, os.getenv("LKB_LOG_FILE", "rebuild_lkb_9_to_12.log"))
HEARTBEAT_SECS  = 60
DELAY_BETWEEN_CHAPTERS = 1  # seconds — polite pacing between chapters
CHAPTER_RETRY   = 2         # extra attempts for a chapter if it comes back with errors
                            # (retries only re-process steps that failed — already-
                            # built steps are skipped via the active-chip check)

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
log = logging.getLogger("lkb_rebuild")

# ── caffeinate (keep Mac awake) ───────────────────────────────────────────────
_caff_proc = None


def _start_caffeinate() -> None:
    global _caff_proc
    try:
        _caff_proc = subprocess.Popen(
            ["caffeinate", "-i"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("caffeinate started (pid=%d) — Mac will not sleep.", _caff_proc.pid)
    except FileNotFoundError:
        log.warning("caffeinate not found — Mac may sleep during rebuild.")


def _stop_caffeinate() -> None:
    if _caff_proc and _caff_proc.poll() is None:
        _caff_proc.terminate()
        log.info("caffeinate stopped.")


atexit.register(_stop_caffeinate)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


# ── Patch openai_service provider ──────────────────────────────────────────────

def _patch_settings_for_provider() -> None:
    """
    Override the IN-MEMORY settings cache (this process only) to route LLM
    calls to the configured provider. Does NOT touch the admin_settings DB
    row, so the live app (other users, other features) keeps using whatever
    provider is actually configured there — this only affects this script's
    own process.
    """
    from app.services import openai_service as _svc

    if PROVIDER == "nvidia":
        if not NVIDIA_API_KEY:
            log.error("NVIDIA_API_KEY is not set.\n  export NVIDIA_API_KEY=your_key\n")
            sys.exit(1)
        _svc._settings_cache.update({
            "provider":       "nvidia",
            "nvidia_api_key": NVIDIA_API_KEY,
            "nvidia_model":   NVIDIA_MODEL,
            "api_enabled":    True,
            "loaded_at":      time.time() + 86400,
        })
        log.info("Provider patched (this process only) -> nvidia  model=%s", NVIDIA_MODEL)
    else:
        if not OLLAMA_API_KEY:
            log.error("OLLAMA_CLOUD_API_KEY is not set.\n  export OLLAMA_CLOUD_API_KEY=your_key\n")
            sys.exit(1)
        _svc._settings_cache.update({
            "provider":              "ollama_cloud",
            "ollama_cloud_api_key":  OLLAMA_API_KEY,
            "ollama_cloud_model":    OLLAMA_MODEL,
            "api_enabled":           True,
            "loaded_at":             time.time() + 86400,
        })
        log.info("Provider patched (this process only) -> ollama_cloud  model=%s", OLLAMA_MODEL)


# ── Progress counters ─────────────────────────────────────────────────────────
class Progress:
    def __init__(self):
        self.grade_total   = 0
        self.grade_done    = 0
        self.chapter_total = 0
        self.chapter_done  = 0
        self.built         = 0
        self.skipped       = 0
        self.no_rag        = 0
        self.errors        = 0
        self.start_time    = time.time()
        self.last_beat     = time.time()

    def heartbeat_if_due(self) -> None:
        now = time.time()
        if now - self.last_beat >= HEARTBEAT_SECS:
            elapsed = int(now - self.start_time)
            log.info(
                "♥ heartbeat | elapsed=%ds | grades=%d/%d | chapters=%d/%d | "
                "built=%d skipped=%d no_rag=%d errors=%d | ETA=%s",
                elapsed,
                self.grade_done, self.grade_total,
                self.chapter_done, self.chapter_total,
                self.built, self.skipped, self.no_rag, self.errors,
                self.eta(),
            )
            self.last_beat = now

    def eta(self) -> str:
        if self.chapter_done == 0:
            return "calculating..."
        elapsed   = time.time() - self.start_time
        remaining = self.chapter_total - self.chapter_done
        secs_each = elapsed / self.chapter_done
        eta_secs  = int(remaining * secs_each)
        hrs, rem  = divmod(eta_secs, 3600)
        mins      = rem // 60
        return f"~{hrs}h {mins}m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_syllabus(grade: str) -> dict:
    from app.services.prewarm_service import get_syllabus_for_grade
    syllabus = get_syllabus_for_grade(grade)
    return syllabus.get("CBSE", {})


# ── Main rebuild loop ─────────────────────────────────────────────────────────

def rebuild_grade(grade: str, prog: Progress) -> dict:
    """Rebuild all LKB chips for one grade. Returns per-grade summary."""
    from app.services.lesson_kb_service import build_lkb_for_chapter, _count_existing, _get_lesson_steps

    syllabus = _get_syllabus(grade)
    total_chapters = sum(len(chaps) for chaps in syllabus.values())
    prog.chapter_total += total_chapters

    log.info("━━━ %s  (%d subjects, %d chapters) ━━━", grade, len(syllabus), total_chapters)

    grade_built = grade_skipped = grade_no_rag = grade_errors = 0
    steps = _get_lesson_steps(grade)

    for subject, chapters in syllabus.items():
        log.info("  Subject: %s  (%d chapters)", subject, len(chapters))

        for i, chapter in enumerate(chapters, 1):
            # Already-done check is per-step (existing >= 1, not >= CHIPS_PER_STEP)
            # so thin chapters that legitimately settled on fewer chips are
            # correctly recognised as complete, not retried forever.
            already_done_steps = sum(
                1 for st in steps if _count_existing(grade, subject, chapter, st) >= 1
            )

            if already_done_steps >= len(steps):
                log.info("    [SKIP] %d/%d  %s  (all %d steps already active)", i, len(chapters), chapter, len(steps))
                prog.chapter_done += 1
                prog.heartbeat_if_due()
                continue

            log.info("    [BUILD] %d/%d  %s  (%d/%d steps already done)",
                     i, len(chapters), chapter, already_done_steps, len(steps))

            try:
                # Retry the chapter if it comes back with errors — a retry
                # only re-processes steps that don't yet have an active chip
                # (already-built steps are skipped), so this is a cheap way
                # to ride out transient provider timeouts without risking
                # duplicate generation for steps that already succeeded.
                attempt = 0
                b = s = e = 0
                while True:
                    result = build_lkb_for_chapter(grade, subject, chapter, MODE)
                    b += result.get("built", 0)
                    s += result.get("skipped", 0)
                    e = result.get("errors", 0)  # only the latest attempt's errors matter for the retry decision
                    attempt += 1
                    if e == 0 or attempt > CHAPTER_RETRY:
                        break
                    log.info("      retrying %s (attempt %d/%d, %d errors so far)...",
                             chapter, attempt + 1, CHAPTER_RETRY + 1, e)
                    time.sleep(2)

                prog.built   += b
                prog.skipped += s
                prog.errors  += e
                grade_built   += b
                grade_skipped += s
                grade_errors  += e
                prog.chapter_done += 1

                status = "✓" if e == 0 else "⚠"
                log.info("      %s built=%d skipped=%d errors=%d (errors include steps with no RAG match, not just failures)  ETA=%s",
                         status, b, s, e, prog.eta())

            except Exception as exc:
                log.error("    ✗ FAILED: %s - %s", chapter, exc)
                prog.errors += 1
                grade_errors += 1
                prog.chapter_done += 1

            prog.heartbeat_if_due()
            if DELAY_BETWEEN_CHAPTERS > 0:
                time.sleep(DELAY_BETWEEN_CHAPTERS)

    prog.grade_done += 1
    return {"grade": grade, "built": grade_built, "skipped": grade_skipped, "errors": grade_errors}


def main() -> None:
    model_label = NVIDIA_MODEL if PROVIDER == "nvidia" else OLLAMA_MODEL
    log.info("=" * 70)
    log.info("LKB Rebuild  Grades 9-12  via %s (%s)", PROVIDER, model_label)
    log.info("Log file: %s", LOG_FILE)
    log.info("Started:  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 70)

    _start_caffeinate()

    try:
        from app.services.ssl_service import enable_system_truststore
        enable_system_truststore()
    except Exception:
        pass

    _patch_settings_for_provider()

    prog = Progress()
    grades = GRADES

    if PILOT_CHAPTER:
        # Format: "Grade 9|Science|Some Chapter" — pilot-test a single chapter
        # end-to-end before committing to the full overnight run.
        from app.services.lesson_kb_service import build_lkb_for_chapter
        g, subj, chap = PILOT_CHAPTER.split("|")
        log.info("PILOT MODE: rebuilding only %s / %s / %s", g, subj, chap)
        result = build_lkb_for_chapter(g, subj, chap, MODE)
        log.info("PILOT RESULT: %s", result)
        return

    prog.grade_total = len(grades)

    log.info("Verifying %s connectivity (model=%s)...", PROVIDER, model_label)
    try:
        import requests
        if PROVIDER == "nvidia":
            r = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
                json={"model": NVIDIA_MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 10},
                timeout=30,
            )
        else:
            r = requests.post(
                "https://api.ollama.com/api/chat",
                headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
                json={"model": OLLAMA_MODEL, "stream": False,
                      "messages": [{"role": "user", "content": "ping"}]},
                timeout=30,
            )
        if r.status_code == 200:
            log.info("%s connected  model=%s", PROVIDER, model_label)
        else:
            log.warning("%s returned HTTP %d - %s", PROVIDER, r.status_code, r.text[:200])
    except Exception as exc:
        log.warning("%s ping failed: %s - continuing anyway", PROVIDER, exc)

    results = []
    for grade in grades:
        try:
            result = rebuild_grade(grade, prog)
            results.append(result)
            log.info("  Grade %s done: built=%d skipped=%d errors=%d",
                     grade, result["built"], result["skipped"], result["errors"])
        except KeyboardInterrupt:
            log.warning("Interrupted by user during %s.", grade)
            break
        except Exception as exc:
            log.error("Grade %s failed: %s", grade, exc)
            results.append({"grade": grade, "built": 0, "skipped": 0, "errors": -1})

    elapsed = int(time.time() - prog.start_time)
    hrs, rem = divmod(elapsed, 3600)
    mins = rem // 60

    log.info("")
    log.info("=" * 70)
    log.info("REBUILD COMPLETE  -  %dh %dm elapsed", hrs, mins)
    log.info("")
    log.info("  %-12s  %8s  %8s  %8s", "Grade", "Built", "Skipped", "Errors")
    log.info("  %-12s  %8s  %8s  %8s", "-" * 12, "-" * 8, "-" * 8, "-" * 8)
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
