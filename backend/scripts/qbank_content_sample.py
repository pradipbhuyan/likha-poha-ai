#!/usr/bin/env python3
"""
Question Bank Content-Quality Sampler (READ-ONLY)
======================================================
Phase 2 of the deep quality check. For a curated list of (grade, subject)
pairs, pulls a sample of question_bank rows per EXACT-MATCHED chapter
(i.e. chapters already confirmed reachable at tier "exact" by
qbank_reachability_audit.py, so any content problem found here is a
genuine staleness/quality question, not a chapter-identity question)
alongside the actual current rag_chunks text for that chapter, and writes
a structured text dump for manual review.

Does NOT write anything to the database.

Usage:
    cd backend
    ./venv/bin/python scripts/qbank_content_sample.py --out /tmp/qbank_sample.txt
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

BOARD = "CBSE"

# Curated spread: the 6 originally-flagged-stale subjects, a sample of the
# newly-found-stale subjects from the comprehensive sweep, and a sample of
# "likely fine" subjects as a control group.
SAMPLE_PLAN = [
    # (grade, subject, questions_per_chapter, max_chapters) -- flagged stale, full rewrite
    ("Grade 11", "Biology", 3, 6),
    ("Grade 12", "Political Science", 3, 6),
    ("Grade 12", "Geography", 3, 6),
    ("Grade 11", "Accountancy", 2, 4),
    ("Grade 12", "Chemistry", 2, 4),
    # newly-found-stale, full rewrite
    ("Grade 11", "Physics", 2, 4),
    ("Grade 12", "History", 2, 4),
    ("Grade 11", "Economics", 2, 4),
    ("Grade 10", "Social Science", 2, 4),
    ("Grade 9", "Science", 2, 4),
    # narrow-fix stale (citation links + exemplar cleanup only, not full rewrite)
    ("Grade 9", "Maths", 2, 3),
    ("Grade 10", "Maths", 2, 3),
    # "likely fine" control group -- never touched by the correction pipeline
    ("Grade 5", "Maths", 2, 3),
    ("Grade 6", "Science", 2, 3),
    ("Grade 12", "Hindi", 2, 3),
]

random.seed(42)


def fetch_all(qb, page: int = 1000) -> list[dict]:
    rows, start = [], 0
    while True:
        r = qb().range(start, start + page - 1).execute()
        d = r.data or []
        rows.extend(d)
        if len(d) < page:
            break
        start += page
    return rows


def get_chunk_text(grade: str, subject: str, chapter: str, max_chars: int = 3000) -> str:
    docs = admin_client.table("rag_documents").select("id").eq("grade", grade).eq(
        "subject", subject).eq("chapter", chapter).eq("board", BOARD).execute()
    doc_ids = [d["id"] for d in (docs.data or [])]
    if not doc_ids:
        return ""
    chunks = fetch_all(lambda: admin_client.table("rag_chunks").select("chunk_text,chunk_index")
                        .in_("document_id", doc_ids))
    chunks.sort(key=lambda c: c.get("chunk_index") or 0)
    text = "\n\n".join(c.get("chunk_text", "") for c in chunks)
    return text[:max_chars]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_lines = []
    total_questions = 0

    for grade, subject, per_chapter, max_chapters in SAMPLE_PLAN:
        out_lines.append(f"\n{'#' * 90}\n# {grade} / {subject}\n{'#' * 90}")

        rag_rows = admin_client.table("rag_documents").select("chapter").eq(
            "grade", grade).eq("subject", subject).eq("board", BOARD).execute()
        canonical_chapters = sorted(set(r["chapter"] for r in (rag_rows.data or [])
                                         if not r["chapter"].lower().startswith("exemplar")))
        if not canonical_chapters:
            out_lines.append("  [no rag_documents chapters found -- skipping]")
            continue

        sample_chapters = canonical_chapters[:max_chapters] if len(canonical_chapters) <= max_chapters \
            else random.sample(canonical_chapters, max_chapters)

        for chapter in sample_chapters:
            qb_rows = fetch_all(lambda ch=chapter: admin_client.table("question_bank").select(
                "id,question,options,answer,explanation,difficulty,status"
            ).eq("grade", grade).eq("subject", subject).eq("chapter", ch).eq("board", BOARD))

            if not qb_rows:
                continue  # this exact-canonical chapter has no bank rows -- coverage gap, not a content issue

            sample = random.sample(qb_rows, min(per_chapter, len(qb_rows)))
            chunk_text = get_chunk_text(grade, subject, chapter)

            out_lines.append(f"\n{'=' * 90}\n## CHAPTER: {chapter}\n{'=' * 90}")
            out_lines.append(f"--- CURRENT TEXTBOOK CONTENT (first 3000 chars of rag_chunks) ---")
            out_lines.append(chunk_text if chunk_text else "[NO RAG CHUNK TEXT FOUND]")
            out_lines.append(f"\n--- SAMPLED BANK QUESTIONS ({len(sample)} of {len(qb_rows)} total for this chapter) ---")
            for q in sample:
                total_questions += 1
                out_lines.append(f"\n[Q{q['id']}] ({q.get('difficulty')}, status={q.get('status')})")
                out_lines.append(f"  Question: {q.get('question')}")
                opts = q.get("options") or {}
                for k in ["A", "B", "C", "D"]:
                    if k in opts:
                        out_lines.append(f"    {k}. {opts[k]}")
                out_lines.append(f"  Answer: {q.get('answer')}")
                out_lines.append(f"  Explanation: {q.get('explanation')}")

    Path(args.out).write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {total_questions} sampled questions across the sample plan to {args.out}")


if __name__ == "__main__":
    main()
