#!/usr/bin/env python3
"""
RAG Upload Script — Grade 9 Social Science (NCF-SE 2023 textbook)
===================================================================
Reads the 9 chapter PDFs of "Understanding Society: India and Beyond"
(book code "iest1", first edition June 2026) from RAG DB/Social Science/,
extracts text, chunks it, creates OpenAI embeddings via the platform's
configured embedding model, and stores them in rag_documents + rag_chunks
in the primary Supabase project — exactly the same pipeline used for
Grade 9 Science and Maths (see upload_ncert_grade5_10_rag.py).

Chapter names are taken directly from CBSE_9["Social Science"] in
app/data/syllabus.py (already updated to match this textbook's official
table of contents), mapped 1:1 to iest101.pdf .. iest109.pdf by chapter
number — no automatic TOC/OCR guessing needed since both were provided
directly by the user for this chapter.

Usage:
    cd backend
    python3 scripts/upload_g9_social_science_rag.py               # upload all 9 chapters
    python3 scripts/upload_g9_social_science_rag.py --dry-run
    python3 scripts/upload_g9_social_science_rag.py --force        # re-upload existing
    python3 scripts/upload_g9_social_science_rag.py --chapters 1 3 5
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber

from app.data.syllabus import CBSE_9
from app.services.auth_service import admin_client as supabase
from app.services.rag_service import create_embedding

# ── Configuration ──────────────────────────────────────────────────────────────

RAG_DB_ROOT = Path(__file__).resolve().parents[2] / "RAG DB"
BOOK_DIR    = RAG_DB_ROOT / "Social Science"
BOOK_CODE   = "iest1"
BOOK_TITLE  = "Understanding Society: India and Beyond"
GRADE       = "Grade 9"
SUBJECT     = "Social Science"
BOARD       = "CBSE"
UPLOADED_BY = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin UUID

CHUNK_SIZE    = 400   # matches the chunking used for Grade 9 Science/Maths
CHUNK_OVERLAP = 50
EMBED_DELAY   = 0.12  # seconds between embedding API calls

# Chapter numbers 1-9 map 1:1 to CBSE_9["Social Science"] (already updated
# to this textbook's exact table of contents) and to iest101.pdf..iest109.pdf.
CHAPTER_NAMES = {i + 1: name for i, name in enumerate(CBSE_9["Social Science"])}


# ── Text extraction and chunking (same approach as Grade 9 Science/Maths) ────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract and clean all text from a chapter PDF using pdfplumber."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                text = re.sub(r'\bReprint\s+\d{4}-\d{2,4}\b', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\bNCERT\b.*?\n', '', text)
                text = re.sub(r'\bPage\s*\|\s*\d+\b', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\n{3,}', '\n\n', text)
                pages.append(text.strip())
        return '\n\n'.join(p for p in pages if p)
    except Exception as e:
        print(f"    [error] Could not extract {pdf_path.name}: {e}")
        return ""


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping sentence-boundary chunks."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, current_len = [], [], 0

    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > CHUNK_SIZE and current:
            chunks.append(' '.join(current))
            tail = ' '.join(current)
            current = [tail[-CHUNK_OVERLAP:]] if CHUNK_OVERLAP else []
            current_len = len(current[0]) if current else 0
        current.append(sentence)
        current_len += s_len

    if current:
        chunks.append(' '.join(current))

    return [c.strip() for c in chunks if len(c.strip()) > 30]


# ── Supabase helpers (same pattern as upload_ncert_grade5_10_rag.py) ─────────

def doc_has_chunks(chapter: str) -> bool:
    """Return True if rag_chunks already exist for this chapter."""
    existing = (
        supabase.table("rag_documents")
        .select("id")
        .eq("grade", GRADE)
        .eq("subject", SUBJECT)
        .eq("chapter", chapter)
        .execute()
    )
    if not existing.data:
        return False
    doc_id = existing.data[0]["id"]
    chunks = (
        supabase.table("rag_chunks")
        .select("id", count="exact")
        .eq("document_id", doc_id)
        .execute()
    )
    return (chunks.count or 0) > 0


def get_or_create_rag_document(chapter: str, title: str) -> str:
    """Return existing rag_documents.id or create a new record."""
    existing = (
        supabase.table("rag_documents")
        .select("id")
        .eq("grade", GRADE)
        .eq("board", BOARD)
        .eq("subject", SUBJECT)
        .eq("chapter", chapter)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    result = (
        supabase.table("rag_documents")
        .insert({
            "grade": GRADE,
            "board": BOARD,
            "subject": SUBJECT,
            "chapter": chapter,
            "title": title,
            "source_type": "pdf",
            "uploaded_by": UPLOADED_BY,
        })
        .execute()
    )
    return result.data[0]["id"]


def upload_chunks_for_doc(doc_id: str, chunks: list[str]) -> int:
    """Embed each chunk via the platform's configured OpenAI embedding model
    (create_embedding, see app/services/rag_service.py) and store in
    rag_chunks. Returns the number of chunks successfully stored."""
    supabase.table("rag_chunks").delete().eq("document_id", doc_id).execute()
    stored = 0
    for i, chunk in enumerate(chunks):
        try:
            embedding = create_embedding(chunk)
            supabase.table("rag_chunks").insert({
                "document_id": doc_id,
                "chunk_text": chunk,
                "chunk_index": i,
                "embedding": embedding,
            }).execute()
            stored += 1
            time.sleep(EMBED_DELAY)
        except Exception as e:
            print(f"    [embed error] chunk {i}: {e}")
    return stored


# ── Main upload logic ──────────────────────────────────────────────────────────

def run_upload(chapters_filter: list[int] | None, dry_run: bool, force: bool) -> None:
    if not BOOK_DIR.exists():
        print(f"ERROR: source folder not found: {BOOK_DIR}")
        sys.exit(1)

    print()
    print(f"  Grade 9 Social Science RAG Upload — {BOOK_TITLE}")
    print(f"  Source folder: {BOOK_DIR}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}{' + FORCE' if force else ''}")
    print()

    total_uploaded = 0
    for chapter_num in sorted(CHAPTER_NAMES.keys()):
        if chapters_filter and chapter_num not in chapters_filter:
            continue

        chapter_name = CHAPTER_NAMES[chapter_num]
        pdf_path = BOOK_DIR / f"{BOOK_CODE}{chapter_num:02d}.pdf"

        print(f"  Ch {chapter_num}: {chapter_name}")

        if not pdf_path.exists():
            print(f"    [skip] source PDF not found: {pdf_path.name}")
            continue

        if dry_run:
            print(f"    [dry-run] would upload {pdf_path.name}")
            continue

        if not force and doc_has_chunks(chapter_name):
            print(f"    [skip] already in RAG")
            continue

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"    [skip] no text extracted")
            continue

        chunks = chunk_text(text)
        print(f"    {len(text):,} chars -> {len(chunks)} chunks -> embedding...")

        title = f"{BOOK_TITLE} — {chapter_name}"
        doc_id = get_or_create_rag_document(chapter_name, title)
        stored = upload_chunks_for_doc(doc_id, chunks)
        print(f"    -> stored {stored}/{len(chunks)} chunks (doc_id: {str(doc_id)[:8]}...)")
        total_uploaded += 1

    print()
    print(f"  Summary: {total_uploaded} chapter(s) uploaded to RAG")
    print()
    if not dry_run and total_uploaded:
        print("  Chapters are now visible in the admin panel under:")
        print("  Admin -> Syllabus / RAG Documents -> Grade 9 -> Social Science")
        print()
        print("  Next step:")
        print("    Admin panel -> Cache & Question Bank -> Generate Lessons")
        print("    (to pre-warm the lesson cache for Grade 9 Social Science)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload Grade 9 Social Science (NCF-SE 2023 textbook) to RAG"
    )
    parser.add_argument("--chapters", nargs="+", type=int,
                        help="Upload specific chapter numbers only (1-9)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be uploaded without calling the API")
    parser.add_argument("--force", action="store_true",
                        help="Re-upload even if the chapter already exists in RAG")
    args = parser.parse_args()

    run_upload(
        chapters_filter=args.chapters,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
