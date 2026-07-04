#!/usr/bin/env python3
"""
RAG Upload Script — NTA PYQ Papers (JEE Main / NEET / CUET)
============================================================
Reads downloaded NTA question papers from ~/Desktop/nta_pyq_pdfs/,
extracts text, chunks it, creates OpenAI embeddings (text-embedding-3-small),
and stores in rag_documents + rag_chunks on SUPABASE 2 (grade_1112_client).

All JEE/NEET/CUET RAG content goes to Supabase 2 — same as Grade 11/12
NCERT content. This keeps everything searchable in the same vector query.

Document tagging:
  grade:   "Grade 11" or "Grade 12" (based on exam type)
  subject: "Physics" | "Chemistry" | "Mathematics" | "Biology" | "General"
  chapter: "PYQ: JEE Main 2026 Apr Shift 1" etc.
  board:   "CBSE" (JEE/NEET are CBSE-aligned)

Prerequisites:
  Run download_nta_pyq.py first to get all PDFs.

Usage:
    cd backend
    python3 scripts/upload_nta_pyq_rag.py               # all exams
    python3 scripts/upload_nta_pyq_rag.py --exam jee    # JEE only
    python3 scripts/upload_nta_pyq_rag.py --exam neet   # NEET only
    python3 scripts/upload_nta_pyq_rag.py --exam cuet   # CUET only
    python3 scripts/upload_nta_pyq_rag.py --dry-run     # no uploads
    python3 scripts/upload_nta_pyq_rag.py --force       # re-upload existing
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openai
import pdfplumber

from dotenv import load_dotenv
load_dotenv()

# SSL must be enabled BEFORE importing the Supabase client
from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

from app.services.supabase_grade_1112_client import grade_1112_client as supabase

# ── OpenAI client ─────────────────────────────────────────────────────────────

import os
_OPENAI_CLIENT: openai.OpenAI = None  # initialized in main()


def _init_openai() -> openai.OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")
    return openai.OpenAI(api_key=key)


def create_embedding(text: str) -> list[float]:
    """Create a 1536-dim embedding using text-embedding-3-small."""
    response = _OPENAI_CLIENT.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


# ── Configuration ──────────────────────────────────────────────────────────────

NTA_PDF_ROOT = Path.home() / "Desktop" / "nta_pyq_pdfs"
BOARD        = "CBSE"
UPLOADED_BY  = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin UUID
CHUNK_SIZE   = 400
CHUNK_OVERLAP = 50
EMBED_DELAY  = 0.12

# ── Exam → subject mapping ─────────────────────────────────────────────────────
# JEE Main papers contain Physics + Chemistry + Maths questions
# NEET papers contain Physics + Chemistry + Biology
# CUET varies — tag as "General" since it's multi-subject

EXAM_TO_GRADES = {
    "JEE_Main": ["Grade 11", "Grade 12"],
    "NEET":     ["Grade 11", "Grade 12"],
    "CUET":     ["Grade 12"],
}

EXAM_TO_SUBJECTS = {
    "JEE_Main": ["Physics", "Chemistry", "Mathematics"],
    "NEET":     ["Physics", "Chemistry", "Biology"],
    "CUET":     ["General"],
}

# Keywords to detect subject within a PYQ paper (for labelling)
SUBJECT_KEYWORDS = {
    "Physics":     ["newton", "force", "velocity", "electric field", "magnetic", "wave", "optics", "thermodynamics"],
    "Chemistry":   ["mole", "periodic", "organic", "reaction", "compound", "ionic", "covalent", "acid", "base"],
    "Mathematics": ["integrate", "differentiate", "matrix", "vector", "probability", "sequence", "parabola", "ellipse"],
    "Biology":     ["cell", "dna", "rna", "photosynthesis", "mitosis", "enzyme", "ecosystem", "genetics"],
}


# ── Text extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Clean NCERT/NTA boilerplate headers
                text = re.sub(r'^\s*(question|paper|nta|national testing agency).*\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
                text = re.sub(r'\n{3,}', '\n\n', text)
                pages.append(text.strip())
        return '\n\n'.join(p for p in pages if p)
    except Exception as e:
        print(f"    [error] Could not extract {pdf_path.name}: {e}")
        return ""


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of ~CHUNK_SIZE chars."""
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


def detect_primary_subject(text: str, exam_key: str) -> str:
    """Detect the dominant subject in a PYQ paper by keyword frequency."""
    text_lower = text.lower()
    scores = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        scores[subject] = sum(text_lower.count(kw) for kw in keywords)
    # Filter to only subjects relevant to this exam
    relevant = EXAM_TO_SUBJECTS.get(exam_key, ["General"])
    if relevant == ["General"]:
        return "General"
    relevant_scores = {s: scores.get(s, 0) for s in relevant}
    return max(relevant_scores, key=relevant_scores.get)


def pdf_filename_to_chapter(filename: str) -> str:
    """Convert a PDF filename to a human-readable chapter/PYQ label."""
    name = filename.replace(".pdf", "")
    # Clean up slugified names
    name = re.sub(r'-+', ' ', name).strip()
    return f"PYQ: {name}"


# ── Supabase 2 helpers ─────────────────────────────────────────────────────────

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


# ── Main upload logic ─────────────────────────────────────────────────────────

def upload_exam(exam_key: str, dry_run: bool, force: bool) -> tuple[int, int]:
    """Upload all PDFs for a given exam. Returns (uploaded, skipped)."""
    exam_dir = NTA_PDF_ROOT / exam_key
    if not exam_dir.exists():
        print(f"  ⚠ Directory not found: {exam_dir}")
        print(f"    Run: python3 scripts/download_nta_pyq.py --exam {exam_key.lower()}")
        return 0, 0

    pdfs = sorted(exam_dir.rglob("*.pdf"))
    if not pdfs:
        print(f"  ⚠ No PDFs found in {exam_dir}")
        return 0, 0

    print(f"\n{'='*60}")
    print(f"Uploading {exam_key} ({len(pdfs)} PDFs) → Supabase 2")
    print(f"{'='*60}")

    grades = EXAM_TO_GRADES.get(exam_key, ["Grade 12"])
    uploaded = skipped = 0

    for pdf_path in pdfs:
        chapter = pdf_filename_to_chapter(pdf_path.name)
        print(f"\n  📄 {pdf_path.name}")
        print(f"     → chapter: {chapter}")

        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            print(f"     ⚠ No text extracted (scanned PDF or empty), skipping")
            skipped += 1
            continue

        # Detect subject
        subject = detect_primary_subject(text, exam_key)
        print(f"     → subject: {subject} ({len(text)} chars)")

        # Upload for each relevant grade
        for grade in grades:
            if not force and doc_has_chunks(grade, subject, chapter):
                print(f"     ⏭  SKIP  {grade} {subject} (already in Supabase 2)")
                skipped += 1
                continue

            if dry_run:
                chunks = chunk_text(text)
                print(f"     🔍 DRY  {grade} {subject} — {len(chunks)} chunks would be uploaded")
                continue

            chunks = chunk_text(text)
            print(f"     ⬆  Uploading {grade} {subject} — {len(chunks)} chunks...")
            doc_id = get_or_create_doc(grade, subject, chapter, f"{exam_key} {chapter}")
            n = upload_chunks(doc_id, chunks)
            print(f"     ✅ {n} chunks stored in Supabase 2")
            uploaded += 1

    return uploaded, skipped


def main() -> None:
    global _OPENAI_CLIENT

    parser = argparse.ArgumentParser(
        description="Upload NTA PYQ papers to Supabase 2 RAG"
    )
    parser.add_argument("--exam", choices=["jee", "neet", "cuet", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--force", action="store_true", help="Re-upload even if already exists")
    args = parser.parse_args()

    if supabase is None:
        print("ERROR: grade_1112_client (Supabase 2) is not configured.")
        print("Set SUPABASE_GRADE_1112_URL and SUPABASE_GRADE_1112_SERVICE_KEY in .env")
        sys.exit(1)

    if not args.dry_run:
        _OPENAI_CLIENT = _init_openai()
        print("✅ OpenAI client initialized (text-embedding-3-small)")

    print(f"NTA PYQ RAG Uploader")
    print(f"Target: Supabase 2 (Grade 11/12 project)")
    print(f"Embedding: text-embedding-3-small (1536 dims)")
    print(f"Dry run: {args.dry_run}")

    exam_map = {
        "jee":  "JEE_Main",
        "neet": "NEET",
        "cuet": "CUET",
    }
    exams = list(exam_map.values()) if args.exam == "all" else [exam_map[args.exam]]

    total_up = total_skip = 0
    for exam_key in exams:
        up, skip = upload_exam(exam_key, args.dry_run, args.force)
        total_up += up
        total_skip += skip

    print(f"\n{'='*60}")
    print(f"DONE: {total_up} uploaded, {total_skip} skipped")
    print(f"All content in Supabase 2 rag_documents/rag_chunks")


if __name__ == "__main__":
    main()
