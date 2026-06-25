#!/usr/bin/env python3
"""
NCERT vs Platform Audit — Grade 5 to Grade 10 (Maths & Science)
================================================================
Compares what chapters are on NCERT (from local ps.pdf TOC files)
against what is already uploaded in the platform's Supabase RAG DB.

This script is READ-ONLY. It makes NO changes to any data.

Usage:
    cd backend
    python3 scripts/audit_ncert_vs_platform.py
    python3 scripts/audit_ncert_vs_platform.py --grades 9 10
    python3 scripts/audit_ncert_vs_platform.py --subjects Maths
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber

from app.services.auth_service import admin_client as supabase

RAG_DB_ROOT = Path(__file__).resolve().parents[2] / "RAG DB"

# ── Same book catalogue as the upload script ──────────────────────────────────
ALL_BOOKS = [
    ("Grade 5",  "Maths",   "eemh1", "Math Magic 5",             "Grade_5/Maths"),
    ("Grade 5",  "EVS",     "eebu1", "Buds EVS Grade 5",         "Grade_5/EVS"),
    ("Grade 6",  "Maths",   "fegp1", "Ganita Prakash Grade 6",   "Grade_6/Maths"),
    ("Grade 6",  "Science", "fecu1", "Curiosity Science Grade 6", "Grade_6/Science"),
    ("Grade 7",  "Maths",   "gegp1", "Ganita Prakash 7 Part 1",  "Grade_7/Maths"),
    ("Grade 7",  "Maths",   "gegp2", "Ganita Prakash 7 Part 2",  "Grade_7/Maths"),
    ("Grade 7",  "Science", "gecu1", "Curiosity Science Grade 7", "Grade_7/Science"),
    ("Grade 8",  "Maths",   "hegp1", "Ganita Prakash 8 Part 1",  "Class 8/Maths-Part1"),
    ("Grade 8",  "Maths",   "hegp2", "Ganita Prakash 8 Part 2",  "Class 8/Maths-Part2"),
    ("Grade 8",  "Science", "hecu1", "Curiosity Science Grade 8", "Class 8/Science"),
    ("Grade 9",  "Maths",   "iemh1", "Mathematics Grade 9",      "Maths"),
    ("Grade 9",  "Science", "iesc1", "Science Grade 9",          "Science"),
    ("Grade 10", "Maths",   "jemh1", "Mathematics Grade 10",     "Grade_10/Maths"),
    ("Grade 10", "Science", "jesc1", "Science Grade 10",         "Grade_10/Science"),
]


# ── TOC extraction (same parsers as upload script) ────────────────────────────

def _normalise_title(raw: str) -> str:
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


def _parse_toc_a(text: str) -> dict[int, str]:
    chapters: dict[int, str] = {}
    skip = {'foreword','preface','appendix','answers','contents',
            'index','bibliography','glossary','acknowledgements','notes'}
    line_re = re.compile(
        r'^(\d{1,2})\.\s+([A-Za-z\u0900-\u097F][^.\n]{3,60}?)\s+(\d{1,3})\s*$',
        re.MULTILINE)
    for m in line_re.finditer(text):
        ch_num = int(m.group(1))
        ch_name = re.sub(r'\s+', ' ', m.group(2)).strip()
        if ch_name.lower() in skip or len(ch_name) <= 3:
            continue
        if ch_num not in chapters:
            chapters[ch_num] = ch_name
    return chapters


def _parse_toc_b(text: str) -> dict[int, str]:
    chapters: dict[int, str] = {}
    word_to_num = {'ONE':1,'TWO':2,'THREE':3,'FOUR':4,'FIVE':5,'SIX':6,
                   'SEVEN':7,'EIGHT':8,'NINE':9,'TEN':10,'ELEVEN':11,
                   'TWELVE':12,'THIRTEEN':13,'FOURTEEN':14,'FIFTEEN':15}
    header_re = re.compile(
        r'(?:C\s*H\s*A\s*P\s*T\s*E\s*R|CHAPTER|Chapter)[ \t]+'
        r'(\d{1,2}|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|'
        r'ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN)[ \t]*\n'
        r'([A-Za-z][^\n]{3,80})', re.MULTILINE)
    for m in header_re.finditer(text):
        num_str = m.group(1).strip()
        raw_name = re.sub(r'\s+\d{1,3}\s*$', '', m.group(2).strip()).strip()
        raw_name = re.sub(r'\s+', ' ', raw_name).rstrip('.').strip()
        ch_num = int(num_str) if num_str.isdigit() else word_to_num.get(num_str.upper(), 0)
        if ch_num == 0 or len(raw_name) < 3:
            continue
        if ch_num not in chapters:
            chapters[ch_num] = _normalise_title(raw_name)
    return chapters


def _parse_toc_ganita(text: str) -> dict[int, str]:
    chapters: dict[int, str] = {}
    skip = {'foreword','preface','contents','index','answers','appendix'}
    line_re = re.compile(
        r'^(\d{1,2})[\.\s]+([A-Z][A-Za-z ,\':&\-/()\d]{3,60}?)\s*$',
        re.MULTILINE)
    for m in line_re.finditer(text):
        ch_num = int(m.group(1))
        ch_name = re.sub(r'\s+', ' ', m.group(2)).strip()
        if ch_name.lower() in skip or len(ch_name) <= 3:
            continue
        if ch_num not in chapters:
            chapters[ch_num] = ch_name
    return chapters


def get_ncert_chapters_from_toc(book_code: str, book_dir: Path) -> dict[int, str]:
    """Extract chapter names from local ps.pdf. Returns {ch_num: ch_name}."""
    ps_path = book_dir / f"{book_code}ps.pdf"
    if not ps_path.exists():
        return {}
    chapters: dict[int, str] = {}
    try:
        with pdfplumber.open(str(ps_path)) as pdf:
            all_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        for parser in [_parse_toc_a, _parse_toc_b, _parse_toc_ganita]:
            for ch_num, name in parser(all_text).items():
                if ch_num not in chapters:
                    chapters[ch_num] = name
    except Exception as e:
        print(f"  [warn] TOC extraction failed for {ps_path.name}: {e}")
    # Fallback: count chapter PDFs if TOC failed
    if not chapters:
        pdfs = sorted(p for p in book_dir.glob(f"{book_code}*.pdf")
                      if not p.stem.endswith("ps"))
        for pdf_path in pdfs:
            stem = pdf_path.stem
            m = re.match(r'^([a-z]{3,5}\d?)(\d{2})$', stem)
            if m:
                ch_num = int(m.group(2))
                chapters[ch_num] = f"Chapter {ch_num}"
    return chapters


# ── Supabase query ────────────────────────────────────────────────────────────

def get_platform_chapters(grade: str, subject: str) -> list[dict]:
    """Fetch all rag_documents for grade+subject from Supabase."""
    try:
        response = (
            supabase.table("rag_documents")
            .select("id, chapter, title, source_type, created_at")
            .eq("grade", grade)
            .eq("subject", subject)
            .order("chapter")
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"  [error] Could not query Supabase for {grade}/{subject}: {e}")
        return []


def get_chunk_count(doc_id) -> int:
    """Return the number of rag_chunks for a document."""
    try:
        response = (
            supabase.table("rag_chunks")
            .select("id", count="exact")
            .eq("document_id", doc_id)
            .execute()
        )
        return response.count or 0
    except Exception:
        return 0


# ── Audit logic ───────────────────────────────────────────────────────────────

STATUS_IN_PLATFORM = "✅ IN PLATFORM"
STATUS_MISSING     = "❌ MISSING"
STATUS_NO_CHUNKS   = "⚠️  DOC ONLY (no chunks)"


def run_audit(grades_filter: list[int] | None, subject_filter: list[str] | None) -> None:
    grand_total_ncert    = 0
    grand_total_platform = 0
    grand_total_missing  = 0

    # Group books by grade+subject for cleaner output
    processed: set[tuple] = set()

    print()
    print("=" * 75)
    print("  NCERT vs Platform Audit — Grade 5 to Grade 10")
    print("  READ-ONLY: this script makes NO changes")
    print("=" * 75)

    for (grade_label, subject, book_code, book_title, folder_rel) in ALL_BOOKS:
        grade_num = int(grade_label.split()[-1])

        if grades_filter and grade_num not in grades_filter:
            continue
        if subject_filter:
            if not any(sf.lower() in subject.lower() for sf in subject_filter):
                continue

        book_dir = RAG_DB_ROOT / folder_rel
        key = (grade_label, subject)

        # ── NCERT chapters from local ps.pdf TOC ─────────────────────────────
        ncert_chapters = get_ncert_chapters_from_toc(book_code, book_dir)

        # ── Platform chapters from Supabase ───────────────────────────────────
        # Only query Supabase once per grade+subject (multiple books map to same subject)
        if key not in processed:
            platform_docs = get_platform_chapters(grade_label, subject)
            processed.add(key)

            # Normalise platform chapter names to lower for comparison
            platform_chapters_lower = {
                (doc["chapter"] or "").strip().lower(): doc
                for doc in platform_docs
            }

            print(f"\n{'─' * 75}")
            print(f"  📚 {grade_label} — {subject}  ({book_title})")
            print(f"  NCERT Book Code: {book_code}  |  Local folder: {folder_rel}")
            print(f"{'─' * 75}")
            print(f"  {'Ch#':<5} {'NCERT Chapter Name':<42} {'Status':<25} Chunks")
            print(f"  {'─'*5} {'─'*42} {'─'*25} {'─'*6}")

            book_ncert_count = len(ncert_chapters)
            book_platform_count = 0
            book_missing_count = 0

            for ch_num in sorted(ncert_chapters.keys()):
                ncert_name = ncert_chapters[ch_num]
                ncert_lower = ncert_name.strip().lower()

                # Try exact match first, then partial match
                matched_doc = platform_chapters_lower.get(ncert_lower)

                if not matched_doc:
                    # Try partial match (chapter name may differ slightly)
                    for plat_lower, doc in platform_chapters_lower.items():
                        # Match if NCERT name is contained in platform name or vice versa
                        if (ncert_lower in plat_lower or plat_lower in ncert_lower or
                                # Match first 30 chars (handles slight naming differences)
                                ncert_lower[:30] == plat_lower[:30]):
                            matched_doc = doc
                            break

                if matched_doc:
                    chunk_count = get_chunk_count(matched_doc["id"])
                    if chunk_count > 0:
                        status = STATUS_IN_PLATFORM
                        book_platform_count += 1
                    else:
                        status = STATUS_NO_CHUNKS
                        book_missing_count += 1
                    print(f"  {ch_num:<5} {ncert_name:<42} {status:<25} {chunk_count}")
                else:
                    status = STATUS_MISSING
                    book_missing_count += 1
                    print(f"  {ch_num:<5} {ncert_name:<42} {status:<25} —")

            # Also show any platform chapters NOT in NCERT TOC (extra/custom content)
            extra_docs = []
            for plat_lower, doc in platform_chapters_lower.items():
                ch_name = doc["chapter"] or ""
                found = any(
                    ch_name.strip().lower()[:30] == ncert_chapters[n].strip().lower()[:30]
                    or ch_name.strip().lower() == ncert_chapters[n].strip().lower()
                    for n in ncert_chapters
                )
                if not found:
                    extra_docs.append(doc)

            if extra_docs:
                print(f"\n  ── Extra chapters in platform (not in NCERT TOC) ──")
                for doc in extra_docs:
                    chunks = get_chunk_count(doc["id"])
                    print(f"  {'—':<5} {(doc['chapter'] or 'Unknown'):<42} {'📌 EXTRA':<25} {chunks}")

            # Summary for this grade/subject
            print(f"\n  Summary: {book_ncert_count} NCERT chapters | "
                  f"{book_platform_count} in platform | "
                  f"{book_missing_count} missing/no-chunks")

            grand_total_ncert    += book_ncert_count
            grand_total_platform += book_platform_count
            grand_total_missing  += book_missing_count

    # Grand summary
    print(f"\n{'=' * 75}")
    print(f"  GRAND TOTAL — Grade 5 to Grade 10 Maths + Science")
    print(f"{'=' * 75}")
    print(f"  NCERT chapters available : {grand_total_ncert}")
    print(f"  Already in platform      : {grand_total_platform}  ✅")
    print(f"  Missing / needs upload   : {grand_total_missing}   ❌")
    coverage = (grand_total_platform / grand_total_ncert * 100) if grand_total_ncert else 0
    print(f"  Coverage                 : {coverage:.0f}%")
    print(f"{'=' * 75}")
    print()
    if grand_total_missing > 0:
        print("  To upload missing chapters, run:")
        print("    python3 scripts/upload_ncert_grade5_10_rag.py")
        print("  The script skips chapters already in the platform (no duplicates).")
    else:
        print("  🎉 All NCERT chapters are already in the platform!")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit NCERT chapters vs platform RAG DB (read-only)"
    )
    parser.add_argument("--grades", nargs="+", type=int, choices=[5, 6, 7, 8, 9, 10],
                        help="Audit specific grades only (default: 5-10)")
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT",
                        help="Filter by subject, e.g. Maths Science EVS")
    args = parser.parse_args()

    run_audit(
        grades_filter=args.grades,
        subject_filter=args.subjects,
    )


if __name__ == "__main__":
    main()
