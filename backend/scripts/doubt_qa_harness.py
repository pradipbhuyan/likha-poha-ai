"""
Doubt-answering quality QA harness (retrieval-only pipeline audit).

Enumerates every real (grade, subject, chapter) with an authored lesson in
lesson_cache for Grade 5-12 (excluding Grade 12 Hindi, which has only 3/18
chapters authored, and "Exemplar:" rows), asks 5 template questions per
chapter through the Ask Doubt page pipeline (answer_doubt) and 1 parity
question through the in-lesson widget pipeline (answer_lesson_follow_up),
and writes one JSON line per call to results.jsonl for later analysis.

Run from backend/: ../venv/bin/python scripts/doubt_qa_harness.py
"""
import sys
import re
import json
import time
import traceback

sys.path.insert(0, '.')
import truststore
truststore.inject_into_ssl()
from dotenv import load_dotenv
load_dotenv('.env')

from app.services.auth_service import admin_client
from app.services.tutor_service import answer_doubt, answer_lesson_follow_up

OUT_PATH = "/private/tmp/claude-501/-Users-a0247716/0ff84df7-214d-4ae0-a83b-8c9062438dbc/scratchpad/doubt_qa_harness/results.jsonl"
PROGRESS_PATH = "/private/tmp/claude-501/-Users-a0247716/0ff84df7-214d-4ae0-a83b-8c9062438dbc/scratchpad/doubt_qa_harness/progress.txt"

EXCLUDE = {("Grade 12", "Hindi")}

PREFIX_RE = re.compile(r'^\s*Chapter\s*\d+\s*[:\-]\s*', re.IGNORECASE)


def fetch_all(table, select, filters):
    q = admin_client.table(table).select(select, count='exact')
    for k, v in filters.items():
        q = q.eq(k, v)
    all_rows = []
    page = 1000
    start = 0
    while True:
        r = q.range(start, start + page - 1).execute()
        rows = r.data or []
        all_rows.extend(rows)
        if len(rows) < page:
            break
        start += page
    return all_rows


def normalize(ch):
    return PREFIX_RE.sub('', ch or '').strip().lower()


def display_chapter_name(ch):
    """Strip the 'Chapter N:' prefix for natural-sounding question text."""
    return PREFIX_RE.sub('', ch or '').strip()


def build_chapter_universe():
    grades = [f"Grade {i}" for i in range(5, 13)]
    universe = []
    for grade in grades:
        rows = fetch_all('lesson_cache', 'subject,chapter', {'grade': grade, 'mode': 'CBSE'})
        by_subject = {}
        for row in rows:
            ch = (row.get('chapter') or '').strip()
            if not ch or ch.lower().startswith('exemplar'):
                continue
            subj = row.get('subject') or 'Unknown'
            if (grade, subj) in EXCLUDE:
                continue
            key = normalize(ch)
            by_subject.setdefault(subj, {})
            # Keep the first-seen raw chapter string per normalized chapter
            by_subject[subj].setdefault(key, ch)
        for subj, chapters in by_subject.items():
            for raw_chapter in chapters.values():
                universe.append((grade, subj, raw_chapter))
    return universe


def build_questions(chapter_display):
    return [
        f"What is {chapter_display}?",
        f"Explain {chapter_display} in simple words.",
        f"Why is {chapter_display} important?",
        f"Give an example related to {chapter_display}.",
        f"What are the key points I should remember about {chapter_display}?",
    ]


def summarize_result(result):
    sources = result.get("sources") or []
    top_similarity = None
    if sources:
        sims = [s.get("similarity") for s in sources if isinstance(s.get("similarity"), (int, float))]
        if sims:
            top_similarity = max(sims)
    answer = result.get("answer") or ""
    return {
        "source_type": result.get("source_type"),
        "answer_len": len(answer),
        "answer_preview": answer[:220],
        "top_similarity": top_similarity,
        "num_sources": len(sources),
    }


def main():
    universe = build_chapter_universe()
    total_chapters = len(universe)
    print(f"Chapter universe: {total_chapters} (grade,subject,chapter) combos", flush=True)

    out_f = open(OUT_PATH, "a")
    done = 0
    t0 = time.time()

    for grade, subject, chapter in universe:
        chapter_display = display_chapter_name(chapter)
        questions = build_questions(chapter_display)

        # --- Ask Doubt page pipeline: 5 questions ---
        for q in questions:
            record = {
                "surface": "ask_doubt_page",
                "grade": grade, "subject": subject, "chapter": chapter,
                "question": q,
            }
            try:
                t1 = time.time()
                result = answer_doubt(
                    grade=grade, mode="CBSE", subject=subject, chapter=chapter,
                    question=q, username="qa_harness", board="CBSE",
                )
                record["elapsed_s"] = round(time.time() - t1, 2)
                record.update(summarize_result(result))
            except Exception as e:
                record["error"] = f"{type(e).__name__}: {e}"
                record["source_type"] = "ERROR"
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()

        # --- Lesson follow-up widget pipeline: 1 parity question ---
        parity_q = questions[0]
        record = {
            "surface": "lesson_follow_up",
            "grade": grade, "subject": subject, "chapter": chapter,
            "question": parity_q,
        }
        try:
            t1 = time.time()
            result = answer_lesson_follow_up(
                grade=grade, mode="CBSE", subject=subject, chapter=chapter,
                step_title="Introduction", lesson=f"This chapter covers {chapter_display}.",
                question=parity_q, username="qa_harness", board="CBSE",
            )
            record["elapsed_s"] = round(time.time() - t1, 2)
            record.update(summarize_result(result))
        except Exception as e:
            record["error"] = f"{type(e).__name__}: {e}"
            record["source_type"] = "ERROR"
        out_f.write(json.dumps(record) + "\n")
        out_f.flush()

        done += 1
        if done % 5 == 0 or done == total_chapters:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta_min = (total_chapters - done) / rate / 60 if rate > 0 else -1
            with open(PROGRESS_PATH, "w") as pf:
                pf.write(
                    f"{done}/{total_chapters} chapters done "
                    f"({grade} {subject}) | elapsed {elapsed/60:.1f}min | "
                    f"ETA {eta_min:.1f}min\n"
                )

    out_f.close()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
