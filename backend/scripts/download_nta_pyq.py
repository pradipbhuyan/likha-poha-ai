#!/usr/bin/env python3
"""
NTA Question Papers Downloader — JEE Main / NEET / CUET
========================================================
Scrapes the official NTA websites and downloads all publicly available
question papers, answer keys, and information bulletins.

NTA hosts PDFs on: cdnbbsr.s3waas.gov.in/{site_hash}/uploads/{year}/...
URLs are not predictable — this script scrapes the live pages to find them.

Output: ~/Desktop/nta_pyq_pdfs/
  JEE_Main/2026/B-Tech-2nd-Apr-2026-Shift-1.pdf
  NEET/2026/...
  CUET/2026/...

Usage:
    cd backend
    python3 scripts/download_nta_pyq.py              # all exams
    python3 scripts/download_nta_pyq.py --exam jee   # JEE only
    python3 scripts/download_nta_pyq.py --exam neet  # NEET only
    python3 scripts/download_nta_pyq.py --exam cuet  # CUET only
    python3 scripts/download_nta_pyq.py --dry-run    # show URLs only

Note: NTA only keeps the most recent year's papers on their live sites.
      Earlier years are removed when new sessions are published.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_ROOT = Path.home() / "Desktop" / "nta_pyq_pdfs"
DOWNLOAD_DELAY = 0.8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://nta.ac.in/",
}

# ── Exam scrape config ────────────────────────────────────────────────────────
# Each entry: (exam_folder, homepage_url, keyword_filter)
# keyword_filter: pipe-separated strings — link text must contain at least one

EXAM_CONFIGS = {
    "jee": (
        "JEE_Main",
        "https://jeemain.nta.nic.in/",
        "shift|b tech|b.tech|question paper",
    ),
    "neet": (
        "NEET",
        "https://neet.nta.nic.in/",
        "neet|question paper|qp|answer key|information bulletin",
    ),
    "cuet": (
        "CUET",
        "https://cuet.nta.nic.in/",
        "cuet|question paper|answer key|information bulletin|toppers",
    ),
}


def slugify(text: str) -> str:
    """Convert link text to a safe filename."""
    s = re.sub(r"[^\w\s-]", "", text).strip()
    s = re.sub(r"\s+", "-", s)
    return s[:80]


def scrape_pdf_links(url: str, keywords: list[str]) -> list[tuple[str, str]]:
    """
    Fetch a page and return (link_text, pdf_url) pairs matching keywords.
    """
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Could not fetch {url}: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" not in href.lower():
            continue
        text = a.get_text(strip=True)
        if not any(k in text.lower() for k in keywords):
            continue
        results.append((text, href))
    return results


def download_file(url: str, dest: Path, dry_run: bool = False) -> bool:
    if dest.exists():
        print(f"  ⏭  SKIP  {dest.name}")
        return True

    if dry_run:
        print(f"  🔍 DRY   {dest.name}")
        print(f"           {url}")
        return True

    try:
        print(f"  ⬇  {dest.name[:60]}...", end="", flush=True)
        r = requests.get(url, headers=HEADERS, verify=False, timeout=60, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        print(f" ✅ {size_kb} KB")
        return True
    except Exception as e:
        print(f" ❌ {e}")
        return False


def download_exam(exam_key: str, output_root: Path, dry_run: bool) -> tuple[int, int]:
    folder, homepage, keyword_str = EXAM_CONFIGS[exam_key]
    keywords = [k.strip() for k in keyword_str.split("|")]

    print(f"\n{'='*60}")
    print(f"Downloading {folder} question papers")
    print(f"Source: {homepage}")
    print(f"{'='*60}")

    links = scrape_pdf_links(homepage, keywords)
    print(f"Found {len(links)} matching PDFs on the site")

    ok = fail = 0
    for text, url in links:
        # Extract year from URL path
        m = re.search(r"/uploads/(\d{4})/", url)
        year = m.group(1) if m else "2026"
        fname = slugify(text) + ".pdf"
        dest = output_root / folder / year / fname
        if download_file(url, dest, dry_run):
            ok += 1
        else:
            fail += 1
        if not dry_run:
            time.sleep(DOWNLOAD_DELAY)

    print(f"\n{folder}: {ok} downloaded/skipped, {fail} failed")
    return ok, fail


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download NTA question papers for JEE/NEET/CUET"
    )
    parser.add_argument(
        "--exam", choices=["jee", "neet", "cuet", "all"], default="all"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be downloaded"
    )
    parser.add_argument(
        "--output", default=str(OUTPUT_ROOT), help="Output directory"
    )
    args = parser.parse_args()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"NTA Question Papers Downloader")
    print(f"Output: {output_root}")
    print(f"Dry run: {args.dry_run}")
    print()
    print("Note: NTA only publishes the current exam year on their live sites.")
    print("      Older papers are removed when new sessions are published.")

    exams = ["jee", "neet", "cuet"] if args.exam == "all" else [args.exam]
    total_ok = total_fail = 0

    for exam in exams:
        ok, fail = download_exam(exam, output_root, args.dry_run)
        total_ok += ok
        total_fail += fail

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_ok} files, {total_fail} failed")
    print(f"Output: {output_root}")

    # List downloaded files
    pdfs = list(output_root.rglob("*.pdf"))
    if pdfs:
        print(f"\nDownloaded files ({len(pdfs)} total):")
        for p in sorted(pdfs):
            rel = p.relative_to(output_root)
            print(f"  {rel}")


if __name__ == "__main__":
    main()
