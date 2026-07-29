#!/usr/bin/env python3
"""
Seed rag_documents rows for Grade 9 & 10 English Grammar topics
====================================================================
The chapter dropdown for Grade 1-10 is entirely driven by rag_documents
rows (merge_uploaded_rag_chapters in app/routes/syllabus.py) -- a chapter
name in the static syllabus.py scaffold that has NO matching
rag_documents row is silently dropped and never shown to students, even
if lesson_cache content exists for it.

Since Grammar topics have no source PDF to upload (see
grammar_reference_data.py's docstring), this script inserts a minimal
rag_documents row per topic (source_type="text", no actual RAG chunks
required) so each Grammar topic becomes a genuine "live" chapter and
appears in the dropdown exactly like every other real chapter -- the
same mechanism already used for every literature chapter.

Run this BEFORE ingesting the GPT-5.5 grammar JSON outputs with
ingest_gpt55_chapter_output.py, so the chapter is already visible in
the dropdown once lesson content lands.

Usage:
    cd backend
    python3 scripts/seed_grammar_rag_documents.py --grade "Grade 9" --dry-run
    python3 scripts/seed_grammar_rag_documents.py --grade "Grade 9"
    python3 scripts/seed_grammar_rag_documents.py --grade "Grade 10"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.ssl_service import enable_system_truststore  # noqa: E402
from scripts.grammar_reference_data import GRADE_9_TOPICS, GRADE_10_TOPICS  # noqa: E402

enable_system_truststore()

SUBJECT_NAME = "English"
BOARD = "CBSE"

TOPIC_LISTS = {
    "Grade 9": GRADE_9_TOPICS,
    "Grade 10": GRADE_10_TOPICS,
}


def seed_topic(grade: str, topic: str, dry_run: bool) -> None:
    existing = (
        admin_client
        .table("rag_documents")
        .select("id")
        .eq("grade", grade)
        .eq("subject", SUBJECT_NAME)
        .eq("board", BOARD)
        .eq("chapter", topic)
        .limit(1)
        .execute()
    )
    if existing.data:
        print(f"    [skip] already exists (id={existing.data[0]['id']}): {topic}")
        return

    payload = {
        "uploaded_by": "Grammar Seed Script",
        "grade": grade,
        "subject": SUBJECT_NAME,
        "chapter": topic,
        "title": f"{grade} CBSE {SUBJECT_NAME} - {topic}",
        "source_type": "text",
        "board": BOARD,
    }

    if dry_run:
        print(f"    [dry-run] would insert: {topic}")
        return

    result = admin_client.table("rag_documents").insert(payload).execute()
    if result.data:
        print(f"    [created] id={result.data[0]['id']}: {topic}")
    else:
        print(f"    [warn] insert returned no data for: {topic}")


def run(grade: str, dry_run: bool) -> None:
    if grade not in TOPIC_LISTS:
        print(f"ERROR: unknown grade {grade!r}. Use 'Grade 9' or 'Grade 10'.")
        sys.exit(1)

    topics = TOPIC_LISTS[grade]
    print(f"\n  Seeding rag_documents for {grade} / {SUBJECT_NAME} Grammar topics")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}")
    print(f"  Topics: {len(topics)}\n")

    for topic in topics:
        seed_topic(grade, topic, dry_run)

    print("\nDone.\n")
    if not dry_run:
        print("Invalidate the syllabus RAG cache so the dropdown updates immediately:")
        print("  (the in-process cache also self-expires after 30 minutes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed rag_documents rows for Grade 9/10 English Grammar topics"
    )
    parser.add_argument("--grade", required=True, choices=["Grade 9", "Grade 10"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run(grade=args.grade, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
