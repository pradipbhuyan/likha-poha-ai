#!/usr/bin/env python3
"""
Export GPT hand-off packages for flagged lesson_kb rows
=========================================================
Reads reports/lesson_kb_quality/flagged_rows.json (from audit_lesson_kb_quality.py)
and, for each affected chapter, pulls the real ingested textbook text from
rag_chunks (via rag_documents) so a human can hand a clean, grounded prompt
to an external LLM (e.g. GPT-5.5) to regenerate corrected chip answers.

READ-ONLY: makes no changes to any database.

Usage:
    cd backend
    python3 scripts/export_lesson_kb_gpt_handoff.py

Output:
    reports/lesson_kb_quality/gpt_handoff/<NN>_<chapter_slug>.md   (one per chapter)
    reports/lesson_kb_quality/gpt_handoff/README.md                (index + instructions)

Each per-chapter file contains:
  - The defective card(s): id, question, current (corrupted) answer
  - The full textbook context for that chapter, reconstructed from rag_chunks
  - A copy-pasteable instruction block for the LLM, with the exact JSON
    schema expected back (so scripts/apply_lesson_kb_fixes.py can ingest it)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

FLAGGED_PATH = Path("reports/lesson_kb_quality/flagged_rows.json")
OUT_DIR = Path("reports/lesson_kb_quality/gpt_handoff")

# Strips the front-matter grade/subject prefixes and "Text Book - " labels
# that lesson_kb.chapter carries but rag_documents.chapter does not.
CHAPTER_PREFIX_RE = re.compile(
    r"^(Text Book - |Exemplar: |Part \d+ - )+", re.IGNORECASE
)

# The source NCERT PDFs render bold text (headings, repeated table rows) as
# multiple stacked/offset copies of the same glyphs in the PDF's text layer —
# confirmed by extracting the raw PDF directly with pypdf, which reproduces
# the exact same duplication independent of this app's ingestion pipeline
# (e.g. "CONSUMER RIGHTS" x5, "More than 28.1" repeated line after line).
# This is NOT an ingestion bug; it's noise baked into the source file that
# any naive extractor reproduces. Collapse it generically: a word or short
# phrase (1-4 words) repeated immediately 2+ times in a row -> keep one copy.
WORD_DEDUP_RE = re.compile(
    r"\b(\w+(?:[ \t]+\w+){0,3})\b(?:[ \t]*\n?[ \t]*\1\b)+", re.IGNORECASE
)
# Character-level version for the letter-by-letter case ("NDERSTNDERST",
# "OPMENTOPMENT") where there's no word boundary between repeats at all.
CHAR_DEDUP_RE = re.compile(r"([A-Za-z]{3,})\1+")


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:60]


def find_document(grade: str, subject: str, chapter: str) -> dict | None:
    clean_chapter = CHAPTER_PREFIX_RE.sub("", chapter).strip()
    res = (
        admin_client.table("rag_documents")
        .select("id, grade, subject, chapter, title")
        .eq("grade", grade)
        .eq("subject", subject)
        .execute()
    )
    docs = res.data or []
    # exact match first, then substring match either direction
    for d in docs:
        if d["chapter"].strip().lower() == clean_chapter.lower():
            return d
    for d in docs:
        dc = d["chapter"].strip().lower()
        if dc in clean_chapter.lower() or clean_chapter.lower() in dc:
            return d
    return None


def fetch_chapter_text(document_id: int) -> str:
    res = (
        admin_client.table("rag_chunks")
        .select("chunk_index, chunk_text")
        .eq("document_id", document_id)
        .order("chunk_index")
        .execute()
    )
    chunks = res.data or []
    joined = "\n\n".join(c["chunk_text"] for c in chunks)
    # Best-effort dedup of the source PDF's stacked-bold-text artifact so the
    # LLM sees mostly-clean prose. Run word-level dedup a few passes (nested
    # repeats collapse one layer at a time), then character-level for the
    # no-word-boundary case.
    cleaned = joined
    for _ in range(3):
        new = WORD_DEDUP_RE.sub(r"\1", cleaned)
        if new == cleaned:
            break
        cleaned = new
    cleaned = CHAR_DEDUP_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


INSTRUCTIONS_TEMPLATE = """\
You are fixing corrupted "Ask about this chapter" answer cards in a CBSE tutoring app.

Each card below has a QUESTION (keep as-is) and a CURRENT ANSWER that is corrupted —
either from duplicated/garbled characters (e.g. "NDERSTNDERST", "A RefundA RefundA
Refund") or from formulas that got flattened into disjointed symbol soup during
extraction (e.g. "GM R GM R GM R", "ˆ ˆ ˆ" for vectors).

Root cause, for context: the source NCERT PDFs render bold text (headings, some
table rows) as multiple stacked copies of the same glyphs in the PDF's text layer.
Any text extractor reproduces this as literally repeated words/letters. It is a
source-file artifact, not a transcription error — treat any run of an immediately
repeated word, phrase, or letter-cluster as ONE occurrence and ignore the repetition.

TEXTBOOK CONTEXT for this chapter follows the card list — it is the actual text the
app ingested for RAG grounding, with a best-effort automatic dedup pass already
applied. It may still contain minor residual noise (stray page numbers, a leftover
duplicated fragment); use only the substantive content and ignore anything that
looks like extraction noise rather than real chapter text.

For EACH card, write a corrected answer as 3-6 concise bullet points:
- Grounded strictly in the textbook context provided (no outside knowledge).
- Clear, well-formed prose — no leftover extraction artifacts.
- For formula-based cards, write the formula/derivation in plain readable notation
  (e.g. "U = 1/2 CV^2 = Q^2 / 2C" not scattered symbols), preserving the actual
  mathematical content from the context.
- If the context genuinely does not contain enough to answer a card, say so in the
  "note" field instead of guessing.

Return ONLY a JSON array, one object per card, in EXACTLY this schema:

[
  {{
    "id": "<card id, copied exactly>",
    "answer": "- bullet one\\n- bullet two\\n- bullet three",
    "note": ""
  }}
]

No markdown fences, no commentary outside the JSON array.

---

## Cards to fix ({n_cards})

{cards_block}

---

## Textbook context ({grade} / {subject} / {chapter})

{context}
"""


def main():
    if not FLAGGED_PATH.exists():
        print(f"Missing {FLAGGED_PATH} — run scripts/audit_lesson_kb_quality.py first.")
        sys.exit(1)

    flagged = json.loads(FLAGGED_PATH.read_text())
    by_chapter: dict[tuple, list] = {}
    for row in flagged:
        key = (row["grade"], row["subject"], row["chapter"])
        by_chapter.setdefault(key, []).append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# GPT Hand-off Packages — Lesson KB Fixes",
        "",
        f"{len(flagged)} flagged cards across {len(by_chapter)} chapters.",
        "",
        "For each file below: paste the whole file into GPT-5.5 (or your LLM of choice),",
        "save its JSON array response, and combine all responses into one file to feed",
        "to `scripts/apply_lesson_kb_fixes.py` (expects a JSON array of {id, answer, note}",
        "objects — see that script's docstring).",
        "",
    ]

    for i, ((grade, subject, chapter), rows) in enumerate(sorted(by_chapter.items()), 1):
        doc = find_document(grade, subject, chapter)
        if doc:
            context = fetch_chapter_text(doc["id"])
            context_note = f"(rag_documents.id={doc['id']}, {len(context)} chars)"
        else:
            context = "[No matching rag_documents entry found — regenerate from your own copy of the NCERT chapter text.]"
            context_note = "(no document match found)"

        cards_block = "\n\n".join(
            f"### Card {j+1}\n"
            f"id: {r['id']}\n"
            f"question: {r['question']}\n"
            f"current (corrupted) answer:\n{r['answer_preview']}\n"
            f"detected issues: {r['issues']}"
            for j, r in enumerate(rows)
        )

        content = INSTRUCTIONS_TEMPLATE.format(
            n_cards=len(rows),
            cards_block=cards_block,
            grade=grade, subject=subject, chapter=chapter,
            context=context,
        )

        slug = slugify(f"{grade}-{subject}-{chapter}")
        fname = f"{i:02d}_{slug}.md"
        (OUT_DIR / fname).write_text(content)

        index_lines.append(f"- `{fname}` — {grade} / {subject} / {chapter} — {len(rows)} card(s) {context_note}")

    (OUT_DIR / "README.md").write_text("\n".join(index_lines))
    print(f"Wrote {len(by_chapter)} hand-off files to {OUT_DIR}/")
    print(f"Start with {OUT_DIR}/README.md")


if __name__ == "__main__":
    main()
