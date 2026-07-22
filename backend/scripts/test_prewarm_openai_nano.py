#!/usr/bin/env python3
"""
One-off test: generate a single chapter doc using OpenAI gpt-4.1-nano
directly, bypassing the admin-configured provider (currently ollama_cloud).

This monkeypatches get_effective_settings() *within this process only* —
it does not touch the platform_settings DB row, so the live server and
all other traffic are unaffected.

Usage:
    cd backend
    .venv/bin/python3 scripts/test_prewarm_openai_nano.py "Grade 11" "Hindi" "Alo-Aandhari"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.openai_service as openai_service
from app.config import settings

_FORCED_SETTINGS = {
    "api_enabled": True,
    "provider": "openai",
    "api_key": settings.OPENAI_API_KEY,
    "fallback_provider": "",
}
openai_service.get_effective_settings = lambda: dict(_FORCED_SETTINGS)
# get_openai_client() caches a client keyed by the resolved key — reset so
# it rebuilds using the forced settings instead of whatever was cached
# before this monkeypatch (e.g. an empty/None key from a prior no-op call).
openai_service._active_client = None
openai_service._active_key = None

from app.services.chapter_doc_prewarm_service import generate_chapter_doc_v2  # noqa: E402
from app.services.chapter_doc_service import store_chapter_doc  # noqa: E402

BOARD = "CBSE"
MODE = "CBSE"


def main():
    grade, subject, chapter = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f"Generating {grade} / {subject} / {chapter!r} via OpenAI gpt-4.1-nano ...")
    doc = generate_chapter_doc_v2(
        board=BOARD, grade=grade, subject=subject, chapter=chapter, mode=MODE,
        model="gpt-4.1-nano",
    )
    if doc is None:
        print("FAILED — refused or invalid, see logs above")
        sys.exit(1)
    exam_note = f", {len(doc.exam)} board Qs" if doc.exam else ""
    print(f"SUCCESS — {len(doc.milestones)} milestones{exam_note}")
    if store_chapter_doc(doc):
        print("Stored to lesson_chapter_doc.")
    else:
        print("Generated OK but DB write failed.")


if __name__ == "__main__":
    main()
