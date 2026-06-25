#!/usr/bin/env python3
"""
RAG Upload Script — NCERT Exemplar Problems (Grade 8, 9, 10)
============================================================
Reads exemplar PDFs from RAG DB/Exemplar/, extracts text, chunks,
creates OpenAI embeddings, and stores in the primary Supabase project.

Exemplar content is tagged with chapter = "Exemplar: {unit_name}"
so it lives alongside textbook content without naming conflicts.
Broad doubt searches (no chapter filter) will find exemplar content.

Prerequisites:
  Run download_ncert_exemplar.py first.

Usage:
    cd backend
    python3 scripts/upload_ncert_exemplar_rag.py               # all
    python3 scripts/upload_ncert_exemplar_rag.py --grades 9 10
    python3 scripts/upload_ncert_exemplar_rag.py --subjects Maths
    python3 scripts/upload_ncert_exemplar_rag.py --dry-run
    python3 scripts/upload_ncert_exemplar_rag.py --force
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber
import urllib3

from app.services.auth_service import admin_client as supabase
from app.services.rag_service import create_embedding

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Config ─────────────────────────────────────────────────────────────────────

EXEMPLAR_ROOT = Path(__file__).resolve().parents[2] / "RAG DB" / "Exemplar"
BOARD         = "CBSE"
UPLOADED_BY   = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin UUID
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50
EMBED_DELAY   = 0.12

# Import the unit names from the download script
# Add scripts/ dir to sys.path so sibling module loads without __init__.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_ncert_exemplar import (  # noqa: E402
    EXEMPLAR_BOOKS,
    EXEMPLAR_UNIT_NAMES,
)


# ── Text extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract clean text from an exemplar PDF."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                text = re.sub(r'\bNCERT\b.*?\n', '', text)
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


# ── Supabase helpers ───────────────────────────────────────────────────────────

def doc_has_chunks(grade: str, subject: str, chapter: str) -> bool:
    existing = (
        supabase.table("rag_documents")
        .select("id")
        .eq("grade", grade)
        .eq("subject", subject)
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


def get_or_create_doc(grade: str, subject: str, chapter: str, title: str) -> str:
    existing = (
        supabase.table("rag_documents")
        .select("id")
        .eq("grade", grade)
        .eq("board", BOARD)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .execute()
    )
    if existing.data:
        return str(existing.data[0]["id"])

    result = (
        supabase.table("rag_documents")
        .insert({
            "grade": grade,
            "board": BOARD,
            "subject": subject,
            "chapter": chapter,
            "title": title,
            "source_type": "exemplar",
            "uploaded_by": UPLOADED_BY,
        })
        .execute()
    )
    return str(result.data[0]["id"])


def upload_chunks(doc_id: str, chunks: list[str]) -> int:
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

def run_upload(
    grades_filter: list[int] | None,
    subject_filter: list[str] | None,
    dry_run: bool,
    force: bool,
) -> None:
    total = 0
    summary: dict[str, int] = {}

    print()
    print("  NCERT Exemplar RAG Upload — Grade 8, 9, 10")
    print(f"  Source: {EXEMPLAR_ROOT}")
    if dry_run:
        print("  Mode: DRY RUN")
    print()

    for (grade_label, folder_name, subject, _subject_folder, base_code, start, end) in EXEMPLAR_BOOKS:
        grade_num = int(grade_label.split()[-1])

        if grades_filter and grade_num not in grades_filter:
            continue
        if subject_filter and not any(sf.lower() in subject.lower() for sf in subject_filter):
            continue

        book_dir = EXEMPLAR_ROOT / folder_name / subject

        print(f"\n{'='*60}")
        print(f"  {grade_label} — {subject} Exemplar  [{base_code}xx]")
        print(f"{'='*60}")

        if not book_dir.exists():
            print(f"  [skip] Folder not found: {book_dir}")
            print(f"         Run download_ncert_exemplar.py first.")
            continue

        # Process each unit PDF
        book_uploaded = 0
        for unit_num in range(start, end + 1):
            filename = f"{base_code}{unit_num:02d}"
            pdf_path = book_dir / f"{filename}.pdf"
            unit_name = EXEMPLAR_UNIT_NAMES.get(filename, f"Unit {unit_num}")

            # Chapter tagged as "Exemplar: {unit_name}" to distinguish from textbook
            chapter_name = f"Exemplar: {unit_name}"
            title = f"NCERT Exemplar {grade_label} {subject} — {unit_name}"

            print(f"  Unit {unit_num:02d}: {unit_name}")

            if not pdf_path.exists():
                print(f"    [skip] PDF not found: {pdf_path.name}")
                continue

            if dry_run:
                print(f"    [dry-run] would upload as chapter: '{chapter_name}'")
                continue

            if not force and doc_has_chunks(grade_label, subject, chapter_name):
                print(f"    [skip] already in RAG")
                continue

            text = extract_text_from_pdf(pdf_path)
            if not text:
                print(f"    [skip] no text extracted")
                continue

            chunks = chunk_text(text)
            print(f"    {len(text):,} chars → {len(chunks)} chunks → embedding...")

            doc_id = get_or_create_doc(grade_label, subject, chapter_name, title)
            stored = upload_chunks(doc_id, chunks)
            print(f"    ✅ stored {stored}/{len(chunks)} chunks")
            book_uploaded += 1

        total += book_uploaded
        summary[f"{grade_label} / {subject}"] = book_uploaded

    print(f"\n\n{'='*60}")
    print(f"  UPLOAD COMPLETE — {total} exemplar units uploaded to RAG")
    print(f"{'='*60}")
    for key, n in summary.items():
        if n:
            print(f"  {key}: {n} units")
    print()
    if not dry_run:
        print("  Exemplar chapters appear in the RAG Documents list as:")
        print("  subject=Maths/Science, chapter='Exemplar: {unit_name}'")
        print("  source_type=exemplar")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload NCERT Exemplar Grade 8-10 to RAG (primary Supabase)"
    )
    parser.add_argument("--grades", nargs="+", type=int, choices=[8, 9, 10])
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Re-upload even if already in RAG")
    args = parser.parse_args()

    run_upload(
        grades_filter=args.grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
