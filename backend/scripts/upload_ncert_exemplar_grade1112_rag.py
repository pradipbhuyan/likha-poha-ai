#!/usr/bin/env python3
"""
RAG Upload Script — NCERT Exemplar Problems Grade 11 & Grade 12
================================================================
Reads exemplar PDFs from ~/Desktop/cbse_ncert_pdfs/Exemplar/Grade_11/
and ~/Desktop/cbse_ncert_pdfs/Exemplar/Grade_12/, extracts text,
chunks it, creates OpenAI embeddings, and stores in the GRADE 11/12
Supabase project (grade_1112_client — second Supabase instance).

Exemplar content is tagged:
  chapter = "Exemplar: {chapter_name}"
  grade   = "Grade 11" or "Grade 12"

Prerequisites:
  1. Run download_ncert_exemplar_grade1112.py first.
  2. SUPABASE_GRADE_1112_URL and SUPABASE_GRADE_1112_SERVICE_KEY must be
     set in .env or environment.

Usage:
    cd backend
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py           # all
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py --grade 11
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py --grade 12
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py --subjects Maths Physics
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py --dry-run
    python3 scripts/upload_ncert_exemplar_grade1112_rag.py --force   # re-upload
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Inject system trust store so macOS corporate/system certificates are accepted
# by httpx (used by the Supabase client). Must happen before any HTTPS import.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import openai
import pdfplumber
import urllib3

from app.services.supabase_grade_1112_client import grade_1112_client as supabase
from app.services.auth_service import admin_client as primary_supabase

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_openai_key() -> str:
    """
    Return the real OpenAI API key.
    Priority:
      1. DB admin_settings.ai_settings.openai_api_key (if not placeholder)
      2. app.config.settings.OPENAI_API_KEY (from .env)
      3. OPENAI_API_KEY environment variable
    """
    # Try DB first (skip placeholder values)
    try:
        resp = (
            primary_supabase.table("admin_settings")
            .select("value")
            .eq("key", "ai_settings")
            .limit(1)
            .execute()
        )
        if resp.data:
            key = (resp.data[0].get("value") or {}).get("openai_api_key", "")
            if key and not key.startswith("sk-newse") and not key.startswith("sk-proj-lmQ_r4"):
                # Real DB key (not the .env key accidentally stored there)
                print(f"  [key] Using OpenAI key from Supabase admin_settings")
                return key
    except Exception as e:
        print(f"  [warn] Could not load key from DB: {e}")

    # Fall back to app config / .env
    try:
        from app.config import settings as _settings  # noqa: PLC0415
        key = _settings.OPENAI_API_KEY or ""
        if key and not key.startswith("sk-newse"):
            print(f"  [key] Using OpenAI key from .env / app config")
            return key
    except Exception:
        pass

    import os
    return os.getenv("OPENAI_API_KEY", "")


def create_embedding(text: str, _openai_client=None) -> list[float]:
    """Create a 1536-dim embedding using text-embedding-3-small."""
    client = _openai_client or _OPENAI_CLIENT
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


_OPENAI_CLIENT: openai.OpenAI = None  # initialised in main()

# ── Config ─────────────────────────────────────────────────────────────────────

EXEMPLAR_ROOT = Path.home() / "Desktop" / "cbse_ncert_pdfs" / "Exemplar"
BOARD         = "CBSE"
UPLOADED_BY   = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin UUID
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50
EMBED_DELAY   = 0.12

# Import catalogue and chapter names from the download script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_ncert_exemplar_grade1112 import (  # noqa: E402
    EXEMPLAR_BOOKS_1112,
    CHAPTER_NAMES,
    get_chapter_name,
)

# ── Text extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
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


# ── Supabase helpers (Grade 11/12 DB) ─────────────────────────────────────────

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
        .eq("subject", subject)
        .eq("chapter", chapter)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    resp = (
        supabase.table("rag_documents")
        .insert({
            "grade": grade,
            "board": BOARD,
            "subject": subject,
            "chapter": chapter,
            "title": title,
            "uploaded_by": UPLOADED_BY,
        })
        .execute()
    )
    return resp.data[0]["id"]


def delete_existing_chunks(doc_id: str) -> None:
    supabase.table("rag_chunks").delete().eq("document_id", doc_id).execute()


def upload_chunks(doc_id: str, chunks: list[str]) -> int:
    uploaded = 0
    for i, chunk in enumerate(chunks):
        try:
            embedding = create_embedding(chunk)
            supabase.table("rag_chunks").insert({
                "document_id": doc_id,
                "chunk_index": i,
                "chunk_text": chunk,
                "embedding": embedding,
            }).execute()
            uploaded += 1
            time.sleep(EMBED_DELAY)
        except Exception as e:
            print(f"      [embed error] chunk {i}: {e}")
    return uploaded


# ── Subject folder → canonical subject name ────────────────────────────────────

FOLDER_TO_SUBJECT = {
    "Maths":     "Mathematics",
    "Physics":   "Physics",
    "Chemistry": "Chemistry",
    "Biology":   "Biology",
}


# ── Main processing ────────────────────────────────────────────────────────────

def process_book(
    grade_label: str,
    folder_name: str,
    subject_folder: str,
    code_prefix: str,
    max_chapters: int,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Process all PDFs for one book. Returns (uploaded_docs, skipped_docs, total_chunks)."""
    subject = FOLDER_TO_SUBJECT.get(subject_folder, subject_folder)
    book_dir = EXEMPLAR_ROOT / folder_name / subject_folder

    if not book_dir.exists():
        print(f"    [skip] folder not found: {book_dir}")
        print(f"           Run download_ncert_exemplar_grade1112.py first.")
        return 0, 0, 0

    # Find all chapter PDFs (excludes *an.pdf answer files — ingest separately)
    pdf_files = sorted(book_dir.glob(f"{code_prefix}[0-9][0-9].pdf"))
    ans_files = sorted(book_dir.glob(f"{code_prefix}an.pdf"))
    all_pdfs = pdf_files + ans_files

    if not all_pdfs:
        print(f"    [skip] no PDFs found in {book_dir}")
        return 0, 0, 0

    uploaded_docs = skipped_docs = total_chunks = 0

    for pdf_path in all_pdfs:
        code = pdf_path.stem  # e.g. "keep201" or "keep2an"

        # Determine chapter name and number
        if code.endswith("an"):
            chapter_name = "Answers and Solutions"
            chapter_num = 0
        else:
            # Extract chapter number from code (last 2 digits)
            try:
                chapter_num = int(code[-2:])
            except ValueError:
                chapter_num = 0
            chapter_name = get_chapter_name(code_prefix, chapter_num)

        chapter_tag = f"Exemplar: {chapter_name}"
        title = f"NCERT Exemplar — {grade_label} {subject} — {chapter_name}"

        if dry_run:
            print(f"    [dry-run] {pdf_path.name} → {grade_label} | {subject} | {chapter_tag}")
            continue

        # Skip if already uploaded (unless --force)
        if not force and doc_has_chunks(grade_label, subject, chapter_tag):
            print(f"    skip (exists) {pdf_path.name} — {chapter_tag}")
            skipped_docs += 1
            continue

        print(f"    ⚙  {pdf_path.name} — {chapter_tag}")

        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"      [warn] no text extracted from {pdf_path.name}")
            continue

        # Chunk
        chunks = chunk_text(text)
        if not chunks:
            print(f"      [warn] no chunks from {pdf_path.name}")
            continue

        print(f"      {len(chunks)} chunks")

        # Upsert document row
        doc_id = get_or_create_doc(grade_label, subject, chapter_tag, title)

        # Delete old chunks if forcing
        if force:
            delete_existing_chunks(doc_id)

        # Upload chunks with embeddings
        n = upload_chunks(doc_id, chunks)
        total_chunks += n
        uploaded_docs += 1
        print(f"      ✅ {n} chunks uploaded")

    return uploaded_docs, skipped_docs, total_chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload NCERT Exemplar PDFs (Grade 11 & 12) to Grade 11/12 Supabase RAG DB."
    )
    parser.add_argument("--grade", choices=["11", "12"], help="Only one grade")
    parser.add_argument(
        "--subjects", nargs="+",
        choices=["Maths", "Physics", "Chemistry", "Biology"],
        help="Filter subjects",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded")
    parser.add_argument("--force", action="store_true", help="Re-upload even if already uploaded")
    args = parser.parse_args()

    global _OPENAI_CLIENT
    if supabase is None:
        print("ERROR: grade_1112_client is None.")
        print("Set SUPABASE_GRADE_1112_URL and SUPABASE_GRADE_1112_SERVICE_KEY in .env")
        sys.exit(1)

    openai_key = _get_openai_key()
    if not openai_key or openai_key.startswith("sk-newse"):
        print("ERROR: Valid OpenAI API key not found.")
        print("The key must be stored in admin_settings.ai_settings.openai_api_key in Supabase.")
        sys.exit(1)
    _OPENAI_CLIENT = openai.OpenAI(api_key=openai_key)
    print(f"OpenAI client initialised with key: {openai_key[:8]}••••{openai_key[-4:]}")

    print("=" * 65)
    print("NCERT Exemplar RAG Upload — Grade 11 & 12 → Grade 11/12 Supabase")
    print(f"Source: {EXEMPLAR_ROOT}")
    print("=" * 65)

    total_docs = total_skip = total_chunks = 0

    for grade_label, folder_name, _class_roman, _subject_url, subject_folder, code_prefix, max_ch in EXEMPLAR_BOOKS_1112:
        grade_num = grade_label.split()[-1]
        if args.grade and grade_num != args.grade:
            continue
        if args.subjects and subject_folder not in args.subjects:
            continue

        subject = FOLDER_TO_SUBJECT.get(subject_folder, subject_folder)
        print(f"\n📚 {grade_label} — {subject}")

        docs, skip, chunks = process_book(
            grade_label, folder_name, subject_folder, code_prefix, max_ch,
            force=args.force, dry_run=args.dry_run,
        )
        total_docs  += docs
        total_skip  += skip
        total_chunks += chunks

    print("\n" + "=" * 65)
    print(f"Done.")
    print(f"  Documents uploaded : {total_docs}")
    print(f"  Documents skipped  : {total_skip} (already in DB)")
    print(f"  Total chunks       : {total_chunks}")
    print("=" * 65)


if __name__ == "__main__":
    main()
