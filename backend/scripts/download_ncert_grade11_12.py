#!/usr/bin/env python3
"""
NCERT Textbook Downloader — Grade 11 & Grade 12
================================================
Downloads all CBSE NCERT chapter PDFs from https://ncert.nic.in/textbook.php
and saves them structured by Grade / Subject / chapter.

URL pattern: https://ncert.nic.in/textbook/pdf/{book_code}{chapter_num:02d}.pdf
  k = Class XI (Grade 11),  l = Class XII (Grade 12)

Output root: ~/Desktop/cbse_ncert_pdfs/

Usage:
    cd backend
    python3 scripts/download_ncert_grade11_12.py               # all grades
    python3 scripts/download_ncert_grade11_12.py --grade 11    # Grade 11 only
    python3 scripts/download_ncert_grade11_12.py --grade 12    # Grade 12 only
    python3 scripts/download_ncert_grade11_12.py --dry-run     # show URLs only
    python3 scripts/download_ncert_grade11_12.py --subjects Physics Chemistry
"""

from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib3
from pathlib import Path

import requests

# Disable SSL verification for ncert.nic.in (macOS cert store issue)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

# ── Configuration ────────────────────────────────────────────────────────────

OUTPUT_ROOT = Path.home() / "Desktop" / "cbse_ncert_pdfs"
NCERT_BASE = "https://ncert.nic.in/textbook/pdf"
DOWNLOAD_DELAY = 0.6   # seconds between requests — be polite to NCERT

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ncert.nic.in/textbook.php",
}

# ── Book catalogue ────────────────────────────────────────────────────────────
# Each entry: (subject_folder, book_code, book_label, max_chapters_to_probe)
# The downloader auto-stops when it hits the first 404.
# Max-probe values are set generously.

GRADE_11_BOOKS = [
    ("Physics",          "keph1",  "Physics Part 1",                           10),
    ("Physics",          "keph2",  "Physics Part 2",                           10),
    ("Chemistry",        "kech1",  "Chemistry Part 1",                         10),
    ("Chemistry",        "kech2",  "Chemistry Part 2",                         10),
    ("Mathematics",      "kemh1",  "Mathematics Part 1",                       10),
    ("Mathematics",      "kemh2",  "Mathematics Part 2",                       10),
    ("Biology",          "kebo1",  "Biology",                                  22),
    ("English",          "keeh1",  "English Hornbill (Core Reader)",            8),
    ("English",          "kesp1",  "English Snapshots (Supplementary)",         8),
    ("Hindi",            "khah1",  "Hindi Aroh",                               20),
    ("Hindi",            "khvt1",  "Hindi Vitan (Supplementary)",               5),
    ("Economics",        "keec1",  "Indian Economic Development",              10),
    ("Economics",        "kest1",  "Statistics for Economics",                 10),
    ("Business_Studies", "kebs1",  "Business Studies Part 1",                  10),
    ("Business_Studies", "kebs2",  "Business Studies Part 2",                  10),
    ("Accountancy",      "keac1",  "Accountancy Part 1",                       10),
    ("Accountancy",      "keac2",  "Accountancy Part 2",                       10),
    ("History",          "keh01",  "Themes in World History Part 1",           20),
    ("Geography",        "kegy1",  "Fundamentals of Physical Geography",       10),
    ("Geography",        "kegy2",  "India Physical Environment",               10),
    ("Political_Science","kepp1",  "Political Theory",                         10),
    ("Political_Science","kepp2",  "Indian Constitution at Work",              10),
    ("Sociology",        "kes01",  "Introducing Sociology",                    10),
    ("Sociology",        "kes02",  "Understanding Society",                    10),
]

GRADE_12_BOOKS = [
    ("Physics",          "leph1",  "Physics Part 1",                           10),
    ("Physics",          "leph2",  "Physics Part 2",                           10),
    ("Chemistry",        "lech1",  "Chemistry Part 1",                         10),
    ("Chemistry",        "lech2",  "Chemistry Part 2",                         10),
    ("Mathematics",      "lemh1",  "Mathematics Part 1",                       10),
    ("Mathematics",      "lemh2",  "Mathematics Part 2",                       10),
    ("Biology",          "lebo1",  "Biology",                                  16),
    ("English",          "lefl1",  "English Flamingo (Core Reader)",            8),
    ("English",          "levs1",  "English Vistas (Supplementary)",            8),
    ("Hindi",            "lhah1",  "Hindi Aroh",                               20),
    ("Hindi",            "lhvt1",  "Hindi Vitan (Supplementary)",               5),
    ("Economics",        "leec1",  "Indian Economy (Development Exp.)",        10),
    ("Economics",        "lema1",  "Introductory Macroeconomics",              10),
    ("Business_Studies", "lebs1",  "Business Studies Part 1",                  10),
    ("Business_Studies", "lebs2",  "Business Studies Part 2",                  10),
    ("Accountancy",      "leac1",  "Accountancy Part 1",                       10),
    ("Accountancy",      "leac2",  "Accountancy Part 2",                       10),
    ("History",          "leh01",  "Themes in Indian History Part 1",          10),
    ("History",          "leh02",  "Themes in Indian History Part 2",          10),
    ("History",          "leh03",  "Themes in Indian History Part 3",          10),
    ("Geography",        "legy1",  "Fundamentals of Human Geography",          10),
    ("Geography",        "legz1",  "India People and Economy",                 10),
    ("Political_Science","lepp1",  "Contemporary World Politics",              10),
    ("Political_Science","lepp2",  "Politics in India since Independence",     10),
    ("Sociology",        "les01",  "Indian Society",                           10),
    ("Sociology",        "les02",  "Social Change and Development in India",   10),
]

GRADE_BOOKS: dict[int, tuple[str, list]] = {
    11: ("Grade_11", GRADE_11_BOOKS),
    12: ("Grade_12", GRADE_12_BOOKS),
}


# ── Download logic ────────────────────────────────────────────────────────────

def build_url(book_code: str, chapter: int) -> str:
    return f"{NCERT_BASE}/{book_code}{chapter:02d}.pdf"


def probe_and_download(
    grade_dir: Path,
    subject_folder: str,
    book_code: str,
    book_label: str,
    max_chapters: int,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> list[Path]:
    """
    Probe chapter URLs 01 → max_chapters for one book.
    Download each chapter that returns HTTP 200.
    Stop at the first 404 (end of chapters for this book).
    Returns list of downloaded file paths.
    """
    subject_dir = grade_dir / subject_folder
    subject_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    consecutive_404 = 0

    for ch in range(1, max_chapters + 1):
        url = build_url(book_code, ch)
        filename = f"{book_code}{ch:02d}.pdf"
        out_path = subject_dir / filename

        # Skip if already downloaded
        if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
            print(f"    [skip] {filename} already exists ({out_path.stat().st_size // 1024} KB)")
            downloaded.append(out_path)
            consecutive_404 = 0
            continue

        if dry_run:
            # Just check the URL without downloading
            try:
                r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True, verify=SSL_VERIFY)
                status = r.status_code
            except Exception as e:
                print(f"    [error] {url}: {e}")
                consecutive_404 += 1
                if consecutive_404 >= 2:
                    break
                continue

            if status == 200:
                print(f"    [would download] {url}")
                consecutive_404 = 0
            else:
                print(f"    [404 - stop] {url}")
                break
            time.sleep(0.1)
            continue

        # Actual download
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, stream=True, verify=SSL_VERIFY)
        except Exception as e:
            print(f"    [ERROR] {url}: {e}")
            consecutive_404 += 1
            if consecutive_404 >= 2:
                print("    Two consecutive errors — stopping this book.")
                break
            time.sleep(1)
            continue

        if r.status_code == 200:
            content = b"".join(r.iter_content(chunk_size=8192))
            if len(content) < 500:
                # Likely a redirect/error page, not a real PDF
                print(f"    [too small, skip] {filename} ({len(content)} bytes)")
                consecutive_404 += 1
                if consecutive_404 >= 2:
                    break
                time.sleep(DOWNLOAD_DELAY)
                continue

            out_path.write_bytes(content)
            size_kb = len(content) // 1024
            print(f"    ✅ {filename}  ({size_kb} KB)")
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


def run_downloader(
    grades: list[int],
    subject_filter: list[str] | None,
    dry_run: bool,
    skip_existing: bool,
) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    summary: dict[str, list[str]] = {}

    for grade in grades:
        grade_folder_name, books = GRADE_BOOKS[grade]
        grade_dir = OUTPUT_ROOT / grade_folder_name
        print(f"\n{'='*70}")
        print(f"  Grade {grade} → {grade_dir}")
        print(f"{'='*70}")

        for (subject_folder, book_code, book_label, max_probe) in books:
            # Apply subject filter if provided
            if subject_filter:
                if not any(
                    sf.lower() in subject_folder.lower() or
                    sf.lower() in book_label.lower()
                    for sf in subject_filter
                ):
                    continue

            print(f"\n  📚 {book_label} [{book_code}] → {subject_folder}/")
            paths = probe_and_download(
                grade_dir=grade_dir,
                subject_folder=subject_folder,
                book_code=book_code,
                book_label=book_label,
                max_chapters=max_probe,
                dry_run=dry_run,
                skip_existing=skip_existing,
            )
            total_downloaded += len(paths)

            key = f"Grade {grade} / {subject_folder} / {book_label}"
            summary[key] = [p.name for p in paths]

    # ── Final summary ──
    print(f"\n\n{'='*70}")
    print(f"  DOWNLOAD COMPLETE — {total_downloaded} files")
    print(f"{'='*70}")

    for book, files in summary.items():
        if files:
            print(f"\n  {book} ({len(files)} chapters):")
            for f in files:
                print(f"    {f}")

    print(f"\n  Output folder: {OUTPUT_ROOT}")
    print()

    # ── Write manifest ──
    if not dry_run and total_downloaded > 0:
        manifest_path = OUTPUT_ROOT / "manifest.txt"
        lines = [
            "NCERT Grade 11 & 12 Download Manifest",
            f"Downloaded: {total_downloaded} chapter PDFs",
            "",
        ]
        for book, files in summary.items():
            if files:
                lines.append(f"\n{book}:")
                for f in files:
                    lines.append(f"  {f}")
        manifest_path.write_text("\n".join(lines))
        print(f"  Manifest written: {manifest_path}")

    print()
    print("  Next step:")
    print("    cd backend")
    print("    python3 scripts/upload_ncert_grade11_12_rag.py")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download NCERT Grade 11 & 12 chapter PDFs from ncert.nic.in"
    )
    parser.add_argument(
        "--grade", type=int, choices=[11, 12],
        help="Download only Grade 11 or Grade 12 (default: both)"
    )
    parser.add_argument(
        "--subjects", nargs="+", metavar="SUBJECT",
        help="Download only specific subjects, e.g. Physics Chemistry Mathematics"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be downloaded without saving files"
    )
    parser.add_argument(
        "--no-skip", action="store_true",
        help="Re-download even if file already exists"
    )
    args = parser.parse_args()

    grades = [args.grade] if args.grade else [11, 12]

    print()
    print("  NCERT Grade 11 & 12 Textbook Downloader")
    print(f"  Output: {OUTPUT_ROOT}")
    if args.dry_run:
        print("  Mode: DRY RUN (no files saved)")
    if args.subjects:
        print(f"  Subjects filter: {args.subjects}")
    print()

    # Verify requests is available
    try:
        import requests  # noqa: F401
    except ImportError:
        print("ERROR: 'requests' library not found.")
        print("Install: pip install requests")
        sys.exit(1)

    run_downloader(
        grades=grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
    )


if __name__ == "__main__":
    main()
