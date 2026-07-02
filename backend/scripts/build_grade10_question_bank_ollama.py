"""
Grade 10 Question Bank Builder — Ollama Cloud (DB-Aware)
=========================================================
Scans the question_bank table for Grade 10 to find:
  1. Chapters with < TARGET questions per difficulty (incomplete)
  2. Subjects/chapters from lesson_cache not yet in question_bank (missing)
Then generates questions using Ollama Cloud free models with automatic
model cycling when consecutive failures are detected.

Free models cycled: gemma3:4b -> gemma3:12b -> gpt-oss:20b

Usage:
    caffeinate -i python3 scripts/build_grade10_question_bank_ollama.py

Background:
    nohup caffeinate -i python3 scripts/build_grade10_question_bank_ollama.py \
        >> /tmp/grade10_qbank.log 2>&1 &

Monitor:
    tail -f /tmp/grade10_qbank.log
"""

import sys, os, time, json, re, threading, logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.openai_service import _call_ollama_cloud, get_effective_settings
from app.services.question_bank_service import add_questions_to_bank
from app.services.grade_db_router import get_content_db

# ── Config ────────────────────────────────────────────────────────────────────
GRADE        = "Grade 10"
BOARD        = "CBSE"
DIFFICULTIES = ["Easy", "Medium", "Hard"]
TARGET_PER_COMBO      = 30    # target questions per chapter/difficulty
QUESTIONS_PER_BATCH   = 10
MAX_FAILS_BEFORE_SWAP = 2
REQUEST_DELAY         = 4.0

FREE_MODELS = ["gemma3:4b", "gemma3:12b", "gpt-oss:20b"]
LOG_FILE    = "/tmp/grade10_qbank.log"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("qbank_g10")

SYSTEM_PROMPT = """You create original CBSE Grade 10 mock test questions for exam preparation.
Return ONLY a valid JSON array. No markdown. No explanations outside JSON.
JSON schema: [{"id":1,"section":"MCQ","question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"answer":"A","explanation":"...","marks":1}]
"""


def get_config():
    c = get_effective_settings()
    key = c.get("ollama_cloud_api_key", "")
    if not key:
        raise RuntimeError("No Ollama Cloud API key. Set it in Admin > AI & Settings.")
    return key, c.get("ollama_cloud_base_url", "https://api.ollama.com")


def discover_work_items():
    """
    Scan question_bank + lesson_cache to find all chapter/difficulty combos
    that need more questions. Returns list of (subject, chapter, difficulty, needed).
    """
    sb = get_content_db(GRADE)

    # 1. Count existing questions per (subject, chapter, difficulty)
    all_rows = []
    offset = 0
    log.info("Scanning existing question_bank...")
    while True:
        r = sb.table("question_bank") \
              .select("subject,chapter,difficulty") \
              .eq("grade", GRADE).eq("board", BOARD).eq("status", "active") \
              .range(offset, offset + 999).execute()
        all_rows.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000

    existing = defaultdict(int)
    for row in all_rows:
        existing[(row["subject"], row["chapter"], row["difficulty"])] += 1

    log.info(f"Found {len(all_rows)} existing questions across "
             f"{len({(s,c) for s,c,d in existing})} chapters")

    # 2. Discover chapters from lesson_cache (RAG content = real chapter names)
    lesson_chapters = defaultdict(set)
    try:
        lc = sb.table("lesson_cache") \
               .select("subject,chapter") \
               .eq("grade", GRADE).eq("board", BOARD) \
               .limit(2000).execute()
        for row in lc.data:
            if row.get("subject") and row.get("chapter"):
                lesson_chapters[row["subject"]].add(row["chapter"])
        log.info(f"Found {sum(len(v) for v in lesson_chapters.values())} "
                 f"chapters in lesson_cache")
    except Exception as e:
        log.warning(f"Could not scan lesson_cache: {e}")

    # 3. Build work list: incomplete existing + missing from lesson_cache
    work = []
    all_chapters = defaultdict(set)

    # From existing question_bank
    for (subj, ch, diff) in existing:
        all_chapters[subj].add(ch)

    # From lesson_cache (may have chapters with 0 questions)
    for subj, chs in lesson_chapters.items():
        for ch in chs:
            all_chapters[subj].add(ch)

    for subj, chapters in sorted(all_chapters.items()):
        for ch in sorted(chapters):
            for diff in DIFFICULTIES:
                have = existing.get((subj, ch, diff), 0)
                need = TARGET_PER_COMBO - have
                if need > 0:
                    work.append((subj, ch, diff, have, need))

    log.info(f"Work items: {len(work)} combos need more questions")
    return work


def generate_questions(subject, chapter, difficulty, count, batch_num,
                       api_key, model, base_url):
    prompt = (
        f"Create {count} unique {difficulty} MCQ questions for CBSE {GRADE} {subject}.\n"
        f"Chapter: {chapter}\nDifficulty: {difficulty}\nVariant: {batch_num}\n\n"
        f"Use real NCERT Grade 10 content. Return ONLY a JSON array of {count} items."
    )
    try:
        raw = _call_ollama_cloud(
            system_prompt=SYSTEM_PROMPT, user_prompt=prompt,
            model=model, api_key=api_key, base_url=base_url, timeout=120.0,
        )
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        s, e = raw.find("["), raw.rfind("]")
        if s == -1 or e == -1:
            return []
        return json.loads(raw[s:e + 1])
    except Exception as ex:
        log.warning(f"      ⚠  {type(ex).__name__}: {str(ex)[:80]}")
        return []


def build_bank(stop_event):
    try:
        api_key, base_url = get_config()
    except RuntimeError as e:
        log.error(str(e)); return

    work = discover_work_items()
    if not work:
        log.info("All chapters already at target. Nothing to do.")
        return

    model_idx = 0
    consecutive_fail = 0

    def mdl():
        return FREE_MODELS[model_idx % len(FREE_MODELS)]

    log.info("=" * 64)
    log.info("LikhaPoha AI — Grade 10 Question Bank Builder (DB-Aware)")
    log.info(f"Free models    : {' -> '.join(FREE_MODELS)}")
    log.info(f"Active model   : {mdl()}")
    log.info(f"Fail-swap after: {MAX_FAILS_BEFORE_SWAP} consecutive failures")
    log.info(f"Work items     : {len(work)} combos to fill")
    log.info(f"Est. batches   : {sum((n + QUESTIONS_PER_BATCH - 1) // QUESTIONS_PER_BATCH for *_, n in work)}")
    log.info("=" * 64)

    total_added = 0

    for subj, ch, diff, have, need in work:
        if stop_event.is_set():
            log.info("Stop signal — exiting gracefully."); return

        batches_needed = (need + QUESTIONS_PER_BATCH - 1) // QUESTIONS_PER_BATCH
        log.info(f"\n📚 {subj} | {ch[:45]} | {diff} "
                 f"(have {have}, need {need}, batches {batches_needed})")

        for b in range(1, batches_needed + 1):
            if stop_event.is_set():
                log.info("Stop signal — exiting gracefully."); return

            batch_size = min(QUESTIONS_PER_BATCH, need - (b - 1) * QUESTIONS_PER_BATCH)
            log.info(f"  ⚡ [{mdl()}] batch {b}/{batches_needed} ({batch_size} q)")

            questions = generate_questions(
                subject=subj, chapter=ch, difficulty=diff,
                count=batch_size, batch_num=b,
                api_key=api_key, model=mdl(), base_url=base_url,
            )

            if questions:
                add_questions_to_bank(
                    questions=questions, board=BOARD, grade=GRADE,
                    subject=subj, chapter=ch,
                    difficulty=diff, exam_type="General",
                )
                total_added += len(questions)
                consecutive_fail = 0
                log.info(f"      ✅ +{len(questions)} (running total: {total_added})")
            else:
                consecutive_fail += 1
                log.warning(f"      ❌ Empty response (fail #{consecutive_fail})")
                if consecutive_fail >= MAX_FAILS_BEFORE_SWAP:
                    old = mdl()
                    model_idx += 1
                    consecutive_fail = 0
                    log.warning(f"  🔄 Model switch: {old} -> {mdl()}")

            time.sleep(REQUEST_DELAY)

    log.info("\n" + "=" * 64)
    log.info("✅ Grade 10 question bank fill complete!")
    log.info(f"Questions added : {total_added}")
    log.info(f"Final model     : {mdl()}")
    log.info("=" * 64)


if __name__ == "__main__":
    stop_event = threading.Event()
    worker = threading.Thread(target=build_bank, args=(stop_event,),
                              daemon=True, name="qbank-g10")
    worker.start()
    log.info(f"[main] PID {os.getpid()} | tail -f {LOG_FILE}")
    try:
        while worker.is_alive():
            worker.join(timeout=5.0)
    except KeyboardInterrupt:
        log.info("[main] Stopping...")
        stop_event.set()
        worker.join(timeout=30.0)
    log.info("[main] Done.")
