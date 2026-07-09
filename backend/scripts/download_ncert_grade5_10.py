#!/usr/bin/env python3
"""
NCERT Textbook Downloader — Grade 5 to Grade 10 (Maths & Science)
=================================================================
Downloads CBSE NCERT chapter PDFs from https://ncert.nic.in/textbook/pdf
and saves them into the project's 'RAG DB/' folder, mirroring the
structure already used for Grade 8 and Grade 9 content.

Book codes verified against NCERT server (June 2026):
  Grade 5  Maths:   eemh1   (Math Magic 5)
  Grade 5  EVS:     eebu1   (Buds - new EVS/Science)
  Grade 6  Maths:   fegp1   (Ganita Prakash 6)
  Grade 6  Science: fecu1   (Curiosity 6)
  Grade 7  Maths:   gegp1   (Ganita Prakash 7 Part 1)
           Maths:   gegp2   (Ganita Prakash 7 Part 2)
  Grade 7  Science: gecu1   (Curiosity 7)
  Grade 10 Maths:   jemh1   (Mathematics 10)
  Grade 10 Science: jesc1   (Science 10)

Grade 8  (hegp1/hegp2/hecu1) — already in RAG DB/Class 8/
Grade 9  (iemh1/iesc1)       — already in RAG DB/Maths/ and RAG DB/Science/

Usage:
    cd backend
    python3 scripts/download_ncert_grade5_10.py              # all missing grades
    python3 scripts/download_ncert_grade5_10.py --grades 5 6 # specific grades
    python3 scripts/download_ncert_grade5_10.py --dry-run    # show URLs only
    python3 scripts/download_ncert_grade5_10.py --no-skip    # re-download existing
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

# ── Paths ─────────────────────────────────────────────────────────────────────

# RAG DB/ lives two levels above backend/scripts/
RAG_DB_ROOT = Path(__file__).resolve().parents[2] / "RAG DB"
NCERT_BASE  = "https://ncert.nic.in/textbook/pdf"
DOWNLOAD_DELAY = 0.8   # polite delay between NCERT requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ncert.nic.in/textbook.php",
}

# ── Book Catalogue ─────────────────────────────────────────────────────────────
# Each tuple: (folder_name, book_code, book_label, platform_subject, max_chapters_to_probe)
# folder_name  = subfolder inside RAG DB/Grade_N/
# platform_subject = subject name used in rag_documents (must match syllabus.py)

GRADE_5_BOOKS = [
    ("Maths",   "eemh1", "Math Magic 5",          "Maths",   16),
    ("EVS",     "eebu1", "Buds (EVS/Science) 5",  "EVS",     20),
    # Santoor — new Grade 5 English textbook (NEP 2020 / NCF-SE 2023, first edition June 2025)
    # Book code: eesa1   Contains: Papa's Spectacles, Gone with the Scooter, The Rainbow,
    # The Wise Parrot, The Frog, What a Tank!, Gilli Danda, The Decision of the Panchayat,
    # Vocation, Glass Bangles (10 chapters)
    ("English", "eesa1", "Santoor (English) 5",   "English", 10),
]

GRADE_6_BOOKS = [
    ("Maths",   "fegp1", "Ganita Prakash 6",       "Maths",   15),
    ("Science", "fecu1", "Curiosity Science 6",    "Science", 15),
]

GRADE_7_BOOKS = [
    ("Maths",   "gegp1", "Ganita Prakash 7 Part 1", "Maths",  12),
    ("Maths",   "gegp2", "Ganita Prakash 7 Part 2", "Maths",  10),
    ("Science", "gecu1", "Curiosity Science 7",     "Science", 15),
]

# Grade 8 already present in RAG DB/Class 8/ — handled by upload script
# Grade 9 already present in RAG DB/Maths/ and RAG DB/Science/ — handled by upload script

GRADE_10_BOOKS = [
    ("Maths",   "jemh1", "Mathematics 10",   "Maths",   16),
    ("Science", "jesc1", "Science 10",        "Science", 16),
]

# Downloadable grades — Grades 8 and 9 are already local
GRADE_BOOKS: dict[int, tuple[str, list]] = {
    5:  ("Grade_5",  GRADE_5_BOOKS),
    6:  ("Grade_6",  GRADE_6_BOOKS),
    7:  ("Grade_7",  GRADE_7_BOOKS),
    10: ("Grade_10", GRADE_10_BOOKS),
}


# ── Download helpers ───────────────────────────────────────────────────────────

def build_url(book_code: str, chapter: int) -> str:
    return f"{NCERT_BASE}/{book_code}{chapter:02d}.pdf"


def download_ps_pdf(book_code: str, dest_dir: Path, skip_existing: bool = True) -> Path | None:
    """Download the prefatory/TOC ps.pdf for a book (used for chapter name extraction)."""
    url = f"{NCERT_BASE}/{book_code}ps.pdf"
    out_path = dest_dir / f"{book_code}ps.pdf"

    if skip_existing and out_path.exists() and out_path.stat().st_size > 500:
        print(f"    [skip] {book_code}ps.pdf already exists")
        return out_path

    try:
        r = requests.get(url, headers=HEADERS, timeout=30, verify=SSL_VERIFY)
        if r.status_code == 200 and len(r.content) > 500:
            out_path.write_bytes(r.content)
            print(f"    ✅ {book_code}ps.pdf  ({len(r.content) // 1024} KB)  [TOC]")
            time.sleep(DOWNLOAD_DELAY)
            return out_path
        else:
            print(f"    [no TOC] {book_code}ps.pdf → HTTP {r.status_code}")
    except Exception as e:
        print(f"    [warn] Could not download TOC: {e}")
    return None


def probe_and_download_book(
    dest_dir: Path,
    book_code: str,
    book_label: str,
    max_chapters: int,
    dry_run: bool,
    skip_existing: bool,
) -> list[Path]:
    """Download all chapter PDFs for one book code, stopping at first 404."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    consecutive_404 = 0

    for ch in range(1, max_chapters + 1):
        url = build_url(book_code, ch)
        filename = f"{book_code}{ch:02d}.pdf"
        out_path = dest_dir / filename

        if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
            print(f"    [skip] {filename} already exists ({out_path.stat().st_size // 1024} KB)")
            downloaded.append(out_path)
            consecutive_404 = 0
            continue

        if dry_run:
            try:
                r = requests.head(url, headers=HEADERS, timeout=10,
                                  allow_redirects=True, verify=SSL_VERIFY)
                if r.status_code == 200:
                    print(f"    [would download] {filename}")
                    consecutive_404 = 0
                else:
                    print(f"    [404 — end] chapter {ch:02d}")
                    break
            except Exception as e:
                print(f"    [error] {e}")
                consecutive_404 += 1
                if consecutive_404 >= 2:
                    break
            time.sleep(0.15)
            continue

        try:
            r = requests.get(url, headers=HEADERS, timeout=30,
                             stream=True, verify=SSL_VERIFY)
        except Exception as e:
            print(f"    [ERROR] {url}: {e}")
            consecutive_404 += 1
            if consecutive_404 >= 2:
                break
            time.sleep(1)
            continue

        if r.status_code == 200:
            content = b"".join(r.iter_content(chunk_size=8192))
            if len(content) < 500:
                print(f"    [too small] {filename} — skipping")
                consecutive_404 += 1
                if consecutive_404 >= 2:
                    break
                time.sleep(DOWNLOAD_DELAY)
                continue
            out_path.write_bytes(content)
            print(f"    ✅ {filename}  ({len(content) // 1024} KB)")
            downloaded.append(out_path)
            consecutive_404 = 0
            time.sleep(DOWNLOAD_DELAY)

        elif r.status_code == 404:
            print(f"    [404 — end of {book_code}] chapter {ch:02d}")
            break
        else:
            print(f"    [HTTP {r.status_code}] {url}")
            consecutive_404 += 1
            if consecutive_404 >= 2:
                break
            time.sleep(1)

    return downloaded


# ── Main runner ────────────────────────────────────────────────────────────────

def run_downloader(
    grades: list[int],
    subject_filter: list[str] | None,
    dry_run: bool,
    skip_existing: bool,
) -> None:
    RAG_DB_ROOT.mkdir(parents=True, exist_ok=True)
    total = 0
    summary: dict[str, int] = {}

    for grade in grades:
        folder_name, books = GRADE_BOOKS[grade]
        grade_dir = RAG_DB_ROOT / folder_name

        print(f"\n{'='*65}")
        print(f"  Grade {grade}  →  {grade_dir}")
        print(f"{'='*65}")

        for (subfolder, book_code, book_label, platform_subject, max_probe) in books:
            if subject_filter:
                if not any(sf.lower() in platform_subject.lower() or
                           sf.lower() in book_label.lower()
                           for sf in subject_filter):
                    continue

            dest = grade_dir / subfolder
            print(f"\n  📚 {book_label} [{book_code}] → {folder_name}/{subfolder}/")

            if not dry_run:
                download_ps_pdf(book_code, dest, skip_existing=skip_existing)

            paths = probe_and_download_book(
                dest_dir=dest,
                book_code=book_code,
                book_label=book_label,
                max_chapters=max_probe,
                dry_run=dry_run,
                skip_existing=skip_existing,
            )
            total += len(paths)
            summary[f"Grade {grade} / {book_label}"] = len(paths)

    print(f"\n\n{'='*65}")
    print(f"  DOWNLOAD COMPLETE — {total} chapter PDFs")
    print(f"{'='*65}")
    for key, n in summary.items():
        if n:
            print(f"  {key}: {n} chapters")

    print(f"\n  Output: {RAG_DB_ROOT}")
    print()
    print("  Next step:")
    print("    cd backend")
    print("    python3 scripts/upload_ncert_grade5_10_rag.py")
    print()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download NCERT Grade 5-10 Maths + Science PDFs"
    )
    parser.add_argument("--grades", nargs="+", type=int, choices=[5, 6, 7, 10],
                        help="Download specific grades only (default: 5 6 7 10)")
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT",
                        help="Filter by subject, e.g. Maths Science EVS")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without saving files")
    parser.add_argument("--no-skip", action="store_true",
                        help="Re-download even if file already exists")
    args = parser.parse_args()

    grades = args.grades if args.grades else [5, 6, 7, 10]

    print()
    print("  NCERT Grade 5-10 Maths + Science Downloader")
    print(f"  RAG DB output: {RAG_DB_ROOT}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    if args.subjects:
        print(f"  Subject filter: {args.subjects}")
    print()

    run_downloader(
        grades=grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
    )


if __name__ == "__main__":
    main()
