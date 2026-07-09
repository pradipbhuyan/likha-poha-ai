#!/usr/bin/env python3
"""
RAG Upload Script — NCERT Grade 5 to Grade 10 (Maths & Science)
===============================================================
Reads chapter PDFs from the project's 'RAG DB/' folder, extracts text,
chunks it, creates OpenAI embeddings, and stores in the primary Supabase
project (rag_documents + rag_chunks tables).

Covers:
  Grade 5  — Maths (eemh1), EVS (eebu1)
  Grade 6  — Maths (fegp1), Science (fecu1)
  Grade 7  — Maths (gegp1 + gegp2), Science (gecu1)
  Grade 8  — Maths (hegp1 + hegp2), Science (hecu1)   [local files]
  Grade 9  — Maths (iemh1), Science (iesc1)            [local files]
  Grade 10 — Maths (jemh1), Science (jesc1)

All content routes to the PRIMARY Supabase project (Grade 1-10 DB).

Prerequisites:
  1. Run download_ncert_grade5_10.py first for Grades 5, 6, 7, 10.
  2. Grade 8 and 9 files must already be in the RAG DB/ folder.
  3. Backend .env must be configured with SUPABASE_URL and SUPABASE_KEY.

Usage:
    cd backend
    python3 scripts/upload_ncert_grade5_10_rag.py               # all grades
    python3 scripts/upload_ncert_grade5_10_rag.py --grades 5 6  # specific grades
    python3 scripts/upload_ncert_grade5_10_rag.py --subjects Maths
    python3 scripts/upload_ncert_grade5_10_rag.py --dry-run
    python3 scripts/upload_ncert_grade5_10_rag.py --force        # re-upload existing
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

# ── sys.path setup — must run before any app imports ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber
import requests
import urllib3

from app.services.auth_service import admin_client as supabase
from app.services.rag_service import create_embedding

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Configuration ──────────────────────────────────────────────────────────────

RAG_DB_ROOT  = Path(__file__).resolve().parents[2] / "RAG DB"
NCERT_BASE   = "https://ncert.nic.in/textbook/pdf"
BOARD        = "CBSE"
UPLOADED_BY  = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin UUID

CHUNK_SIZE    = 400   # smaller chunks = better Maths retrieval precision
CHUNK_OVERLAP = 50
EMBED_DELAY   = 0.12  # seconds between embedding API calls

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ncert.nic.in/textbook.php",
}

# ── Book catalogue — maps to RAG DB folder structure ──────────────────────────
# Each tuple: (grade_label, subject, book_code, book_title, local_folder_relative_to_RAG_DB)
# local_folder_relative_to_RAG_DB is relative to RAG_DB_ROOT

ALL_BOOKS = [
    # Grade 5
    ("Grade 5",  "Maths",   "eemh1", "Math Magic 5",            "Grade_5/Maths"),
    ("Grade 5",  "EVS",     "eebu1", "Buds EVS Grade 5",        "Grade_5/EVS"),
    # Santoor — new Grade 5 English textbook (NEP 2020 / NCF-SE 2023, first edition June 2025)
    # Chapters: Papa's Spectacles, Gone with the Scooter, The Rainbow, The Wise Parrot,
    # The Frog, What a Tank!, Gilli Danda, The Decision of the Panchayat, Vocation, Glass Bangles
    ("Grade 5",  "English", "eesa1", "Santoor English Grade 5", "Grade_5/English"),
    # Grade 6
    ("Grade 6",  "Maths",   "fegp1", "Ganita Prakash Grade 6",  "Grade_6/Maths"),
    ("Grade 6",  "Science", "fecu1", "Curiosity Science Grade 6","Grade_6/Science"),
    # Grade 7
    ("Grade 7",  "Maths",   "gegp1", "Ganita Prakash 7 Part 1", "Grade_7/Maths"),
    ("Grade 7",  "Maths",   "gegp2", "Ganita Prakash 7 Part 2", "Grade_7/Maths"),
    ("Grade 7",  "Science", "gecu1", "Curiosity Science Grade 7","Grade_7/Science"),
    # Grade 8 — files already in RAG DB/Class 8/
    ("Grade 8",  "Maths",   "hegp1", "Ganita Prakash 8 Part 1", "Class 8/Maths-Part1"),
    ("Grade 8",  "Maths",   "hegp2", "Ganita Prakash 8 Part 2", "Class 8/Maths-Part2"),
    ("Grade 8",  "Science", "hecu1", "Curiosity Science Grade 8","Class 8/Science"),
    # Grade 9 — files already in RAG DB/Maths/ and RAG DB/Science/
    ("Grade 9",  "Maths",   "iemh1", "Mathematics Grade 9",     "Maths"),
    ("Grade 9",  "Science", "iesc1", "Science Grade 9",         "Science"),
    # Grade 10
    ("Grade 10", "Maths",   "jemh1", "Mathematics Grade 10",    "Grade_10/Maths"),
    ("Grade 10", "Science", "jesc1", "Science Grade 10",        "Grade_10/Science"),
]


# ── Chapter name extraction ────────────────────────────────────────────────────

def _normalise_title(raw: str) -> str:
    """Apply consistent title-casing to a chapter name string."""
    ch_name = raw.title()
    for word, fixed in [(' And ', ' and '), (' Of ', ' of '), (' The ', ' the '),
                        (' In ', ' in '), (' A ', ' a '), (' An ', ' an '),
                        (' For ', ' for '), (' With ', ' with '), (' To ', ' to '),
                        (' By ', ' by '), (' On ', ' on '), (' At ', ' at '),
                        (' As ', ' as '), (' Or ', ' or ')]:
        ch_name = ch_name.replace(word, fixed)
    ch_name = re.sub(r'\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|Xi|Xii)\b',
                     lambda m: m.group().upper(), ch_name)
    return (ch_name[0].upper() + ch_name[1:]) if ch_name else ch_name


def _parse_toc_format_a(text: str) -> dict[int, str]:
    """
    Parse TOC lines like: '1. Sets 1'  or  '2. Relations and Functions 24'
    Works for Maths and many Science books.
    """
    chapters: dict[int, str] = {}
    skip = {'foreword', 'preface', 'appendix', 'answers', 'contents',
            'index', 'bibliography', 'glossary', 'acknowledgements', 'notes',
            'about', 'introduction to the', 'a note to'}
    line_re = re.compile(
        r'^(\d{1,2})\.\s+([A-Za-z\u0900-\u097F][^.\n]{3,60}?)\s+(\d{1,3})\s*$',
        re.MULTILINE,
    )
    for m in line_re.finditer(text):
        ch_num = int(m.group(1))
        ch_name = re.sub(r'\s+', ' ', m.group(2)).strip()
        if ch_name.lower() in skip or len(ch_name) <= 3:
            continue
        if ch_num not in chapters:
            chapters[ch_num] = ch_name
    return chapters


def _parse_toc_format_b(text: str) -> dict[int, str]:
    """
    Parse CHAPTER/Chapter header followed by title on the next line.
    Handles Ganita Prakash and Curiosity series formats.
    """
    chapters: dict[int, str] = {}
    word_to_num = {
        'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
        'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10,
        'ELEVEN': 11, 'TWELVE': 12, 'THIRTEEN': 13, 'FOURTEEN': 14, 'FIFTEEN': 15,
    }
    header_re = re.compile(
        r'(?:C\s*H\s*A\s*P\s*T\s*E\s*R|CHAPTER|Chapter)[ \t]+'
        r'(\d{1,2}|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|'
        r'ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN)[ \t]*\n'
        r'([A-Za-z][^\n]{3,80})',
        re.MULTILINE,
    )
    for m in header_re.finditer(text):
        num_str = m.group(1).strip()
        raw_name = re.sub(r'\s+\d{1,3}\s*$', '', m.group(2).strip()).strip()
        raw_name = re.sub(r'\s+', ' ', raw_name).rstrip('.').strip()
        ch_num = int(num_str) if num_str.isdigit() else word_to_num.get(num_str.upper(), 0)
        if ch_num == 0 or len(raw_name) < 3:
            continue
        ch_name = _normalise_title(raw_name)
        if ch_num not in chapters:
            chapters[ch_num] = ch_name
    return chapters


def _parse_toc_ganita_prakash(text: str) -> dict[int, str]:
    """
    Parse Ganita Prakash (new NCERT Maths) TOC format.
    These books use numbered bullet list format: '1 Patterns' or '1. Patterns'
    """
    chapters: dict[int, str] = {}
    # Pattern: digit(s) followed by a title word (no page number on same line in some editions)
    line_re = re.compile(
        r'^(\d{1,2})[\.\s]+([A-Z][A-Za-z ,\':&\-/()\d]{3,60}?)\s*$',
        re.MULTILINE,
    )
    skip = {'foreword', 'preface', 'contents', 'index', 'answers', 'appendix'}
    for m in line_re.finditer(text):
        ch_num = int(m.group(1))
        ch_name = re.sub(r'\s+', ' ', m.group(2)).strip()
        if ch_name.lower() in skip or len(ch_name) <= 3:
            continue
        if ch_num not in chapters:
            chapters[ch_num] = ch_name
    return chapters


def extract_toc_from_ps_pdf(ps_pdf_path: Path) -> dict[int, str]:
    """Extract chapter name map from a ps.pdf prefatory file."""
    chapters: dict[int, str] = {}
    if not ps_pdf_path.exists():
        return chapters
    try:
        with pdfplumber.open(str(ps_pdf_path)) as pdf:
            all_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Try all format parsers; merge results (lower chapter number wins)
        for parser in [_parse_toc_format_a, _parse_toc_format_b, _parse_toc_ganita_prakash]:
            result = parser(all_text)
            for ch_num, name in result.items():
                if ch_num not in chapters:
                    chapters[ch_num] = name
    except Exception as e:
        print(f"    [warn] TOC extraction failed for {ps_pdf_path.name}: {e}")
    return chapters


def extract_chapter_name_from_pdf(pdf_path: Path, chapter_num: int) -> str | None:
    """Fallback: extract chapter name from the first 2 pages of the chapter PDF."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = ""
            for page in pdf.pages[:3]:
                text += (page.extract_text() or "") + "\n"
    except Exception:
        return None

    # Pattern: "Chapter N: Title" or "Chapter N Title"
    m = re.search(
        rf'[Cc]hapter\s*{chapter_num}\s*[:\.\-]?\s*([A-Z][A-Za-z\s,\':&\-/()\d]{{3,70}})',
        text,
    )
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if 3 < len(raw) < 80:
            return _normalise_title(raw)

    # ALL CAPS chapter title on its own line
    m = re.search(r'\n([A-Z][A-Z\s,\':&\-/()\d]{5,60})\n', text)
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if 4 < len(raw) < 80:
            return _normalise_title(raw)

    return None


# ── Supabase helpers ───────────────────────────────────────────────────────────

def doc_has_chunks(grade: str, subject: str, chapter: str) -> bool:
    """Return True if rag_chunks already exist for this grade/subject/chapter."""
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


def get_or_create_rag_document(
    grade: str, subject: str, chapter: str, title: str
) -> str:
    """Return existing rag_documents.id or create a new record."""
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
        return existing.data[0]["id"]

    result = (
        supabase.table("rag_documents")
        .insert({
            "grade": grade,
            "board": BOARD,
            "subject": subject,
            "chapter": chapter,
            "title": title,
            "source_type": "pdf",
            "uploaded_by": UPLOADED_BY,
        })
        .execute()
    )
    return result.data[0]["id"]


def upload_chunks_for_doc(doc_id: str, chunks: list[str]) -> int:
    """Embed each chunk and store in rag_chunks. Returns stored count."""
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


# ── Text extraction and chunking ───────────────────────────────────────────────

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


# ── Parse book code + chapter number from filename ────────────────────────────

def parse_book_chapter(pdf_path: Path) -> tuple[str, int] | None:
    """
    Extract book_code and chapter_num from filename.
    e.g. eemh101.pdf → ("eemh1", 1)
         gegp207.pdf → ("gegp2", 7)
         hegp101.pdf → ("hegp1", 1)
    """
    stem = pdf_path.stem
    m = re.match(r'^([a-z]{3,5}\d?)(\d{2})$', stem)
    if not m:
        return None
    return m.group(1), int(m.group(2))


# ── TOC cache (one ps.pdf download per book) ──────────────────────────────────

_toc_cache: dict[str, dict[int, str]] = {}


def get_toc(book_code: str, book_dir: Path) -> dict[int, str]:
    """Return cached TOC for book_code, loading from local ps.pdf if needed."""
    if book_code not in _toc_cache:
        ps_path = book_dir / f"{book_code}ps.pdf"
        print(f"    → Loading TOC from {ps_path.name} ...")
        toc = extract_toc_from_ps_pdf(ps_path)
        if toc:
            print(f"      {len(toc)} chapter names found")
        else:
            print(f"      [warn] No TOC — will use first-page fallback")
        _toc_cache[book_code] = toc
    return _toc_cache[book_code]


def get_chapter_name(
    book_code: str, chapter_num: int, book_dir: Path, pdf_path: Path
) -> str:
    """
    Resolve chapter name using:
    1. TOC from ps.pdf (auto-extracted)
    2. First-page extraction from chapter PDF
    3. Fallback: 'Chapter N'
    """
    toc = get_toc(book_code, book_dir)
    if chapter_num in toc:
        return toc[chapter_num]

    extracted = extract_chapter_name_from_pdf(pdf_path, chapter_num)
    if extracted:
        return extracted

    return f"Chapter {chapter_num}"


# ── Main upload logic ──────────────────────────────────────────────────────────

def process_book(
    grade: str,
    subject: str,
    book_code: str,
    book_title: str,
    book_dir: Path,
    dry_run: bool,
    force: bool,
) -> int:
    """Process all chapter PDFs for one book. Returns number of chapters uploaded."""
    if not book_dir.exists():
        print(f"  [skip] Folder not found: {book_dir}")
        print(f"         Run download_ncert_grade5_10.py first for this grade.")
        return 0

    pdfs = sorted(
        p for p in book_dir.glob(f"{book_code}*.pdf")
        if not p.stem.endswith("ps")  # skip the TOC file
    )

    if not pdfs:
        print(f"  [skip] No chapter PDFs found in {book_dir}")
        return 0

    print(f"\n  📖 {book_title} [{book_code}] — {len(pdfs)} chapters found")

    # Pre-load TOC
    get_toc(book_code, book_dir)

    uploaded = 0
    for pdf_path in pdfs:
        parsed = parse_book_chapter(pdf_path)
        if not parsed:
            print(f"    [skip] Unrecognised filename: {pdf_path.name}")
            continue

        _, chapter_num = parsed
        chapter_name = get_chapter_name(book_code, chapter_num, book_dir, pdf_path)

        print(f"    Ch {chapter_num:02d}: {chapter_name}")

        if dry_run:
            print(f"      [dry-run] would upload {pdf_path.name}")
            continue

        if not force and doc_has_chunks(grade, subject, chapter_name):
            print(f"      [skip] already in RAG")
            continue

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"      [skip] no text extracted")
            continue

        chunks = chunk_text(text)
        print(f"      {len(text):,} chars → {len(chunks)} chunks → embedding...")

        title = f"{book_title} — {chapter_name}"
        doc_id = get_or_create_rag_document(grade, subject, chapter_name, title)
        stored = upload_chunks_for_doc(doc_id, chunks)
        print(f"      ✅ stored {stored}/{len(chunks)} chunks  (doc_id: {str(doc_id)[:8]}...)")
        uploaded += 1

    return uploaded


def run_upload(
    grades_filter: list[int] | None,
    subject_filter: list[str] | None,
    dry_run: bool,
    force: bool,
) -> None:
    total = 0
    summary: dict[str, int] = {}

    for (grade_label, subject, book_code, book_title, folder_rel) in ALL_BOOKS:
        grade_num = int(grade_label.split()[-1])

        if grades_filter and grade_num not in grades_filter:
            continue

        if subject_filter:
            if not any(sf.lower() in subject.lower() for sf in subject_filter):
                continue

        book_dir = RAG_DB_ROOT / folder_rel

        print(f"\n{'='*65}")
        print(f"  {grade_label} — {subject}")
        print(f"  Folder: {book_dir}")
        print(f"{'='*65}")

        n = process_book(
            grade=grade_label,
            subject=subject,
            book_code=book_code,
            book_title=book_title,
            book_dir=book_dir,
            dry_run=dry_run,
            force=force,
        )
        total += n
        key = f"{grade_label} / {subject} / {book_code}"
        summary[key] = n

    print(f"\n\n{'='*65}")
    print(f"  UPLOAD COMPLETE — {total} chapters uploaded to RAG")
    print(f"{'='*65}")
    for key, n in summary.items():
        if n:
            print(f"  {key}: {n} chapters")

    print()
    print("  Chapters are now visible in the admin panel under:")
    print("  Admin → Syllabus / RAG Documents for each grade.")
    print()
    if not dry_run:
        print("  Next step:")
        print("    Admin panel → Cache & Question Bank → Generate Lessons")
        print("    (for each new grade/subject to pre-warm lesson cache)")
    print()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload NCERT Grade 5-10 Maths + Science to RAG (primary Supabase)"
    )
    parser.add_argument("--grades", nargs="+", type=int,
                        choices=[5, 6, 7, 8, 9, 10],
                        help="Upload specific grades only (default: all 5-10)")
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT",
                        help="Filter by subject e.g. Maths Science EVS")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be uploaded without calling the API")
    parser.add_argument("--force", action="store_true",
                        help="Re-upload even if chapter already exists in RAG")
    args = parser.parse_args()

    print()
    print("  NCERT Grade 5-10 Maths + Science RAG Upload")
    print(f"  RAG DB source: {RAG_DB_ROOT}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    if args.force:
        print("  Mode: FORCE (re-uploading existing chapters)")
    if args.grades:
        print(f"  Grades: {args.grades}")
    if args.subjects:
        print(f"  Subjects: {args.subjects}")
    print()

    run_upload(
        grades_filter=args.grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
