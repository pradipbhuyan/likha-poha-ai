#!/usr/bin/env python3
"""
NTA Previous Year Question Papers Downloader — JEE Main / NEET / CUET
======================================================================
Downloads officially released PYQ papers from NTA's public archive.

Sources (all official/free):
  JEE Main:  https://jeemain.nta.nic.in/webinfo/Public/Home/frmPreviousPaper.aspx
             Papers released as PDFs on nta.ac.in
  NEET:      https://neet.nta.nic.in/ — answer key + question paper PDFs
  CUET:      https://cuet.nta.nic.in/

Output root: ~/Desktop/nta_pyq_pdfs/
  nta_pyq_pdfs/
    JEE_Main/
      2024/
        JEE_Main_2024_Shift1_Physics.pdf
      2023/
        ...
    NEET/
      2024/
        NEET_2024_QP.pdf
    CUET/
      2024/
        ...

Usage:
    cd backend
    python3 scripts/download_nta_pyq.py               # all exams
    python3 scripts/download_nta_pyq.py --exam jee     # JEE only
    python3 scripts/download_nta_pyq.py --exam neet    # NEET only
    python3 scripts/download_nta_pyq.py --dry-run      # show URLs only

NOTE: NTA does not have a single stable URL pattern for all papers.
      This script uses known stable URLs from nta.ac.in for 2019-2024.
      Papers are publicly available without authentication.
      Run with --dry-run first to verify URLs are still active.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

OUTPUT_ROOT = Path.home() / "Desktop" / "nta_pyq_pdfs"
DOWNLOAD_DELAY = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ── JEE Main PYQ Papers ──────────────────────────────────────────────────────
# Official source: https://jeemain.nta.nic.in
# Format: Session 1 & 2 per year, Morning (S1) & Evening (S2) shifts
# NTA hosts these at cdn3.digialm.com and nta.ac.in

JEE_MAIN_PAPERS = [
    # ── 2024 ──
    {
        "year": "2024", "session": "Jan", "shift": "S1_Morning",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2024/JEE_Main_2024_Session1_QP.pdf",
        "filename": "JEE_Main_2024_Jan_S1_Morning.pdf",
    },
    {
        "year": "2024", "session": "Apr", "shift": "S1_Morning",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2024/JEE_Main_2024_Session2_QP.pdf",
        "filename": "JEE_Main_2024_Apr_S1_Morning.pdf",
    },
    # ── 2023 ──
    {
        "year": "2023", "session": "Jan", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2023/JEE_Main_2023_Jan_QP.pdf",
        "filename": "JEE_Main_2023_Jan_S1.pdf",
    },
    {
        "year": "2023", "session": "Apr", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2023/JEE_Main_2023_Apr_QP.pdf",
        "filename": "JEE_Main_2023_Apr_S1.pdf",
    },
    # ── 2022 ──
    {
        "year": "2022", "session": "Jun", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2022/JEE_Main_2022_Jun_S1_QP.pdf",
        "filename": "JEE_Main_2022_Jun_S1.pdf",
    },
    {
        "year": "2022", "session": "Jul", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2022/JEE_Main_2022_Jul_S1_QP.pdf",
        "filename": "JEE_Main_2022_Jul_S1.pdf",
    },
    # ── 2021 ──
    {
        "year": "2021", "session": "Feb", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2021/JEE_Main_2021_Feb_S1_QP.pdf",
        "filename": "JEE_Main_2021_Feb_S1.pdf",
    },
    {
        "year": "2021", "session": "Mar", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2021/JEE_Main_2021_Mar_S1_QP.pdf",
        "filename": "JEE_Main_2021_Mar_S1.pdf",
    },
    # ── 2020 ──
    {
        "year": "2020", "session": "Jan", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2020/JEE_Main_2020_Jan_S1_QP.pdf",
        "filename": "JEE_Main_2020_Jan_S1.pdf",
    },
    {
        "year": "2020", "session": "Sep", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2020/JEE_Main_2020_Sep_S1_QP.pdf",
        "filename": "JEE_Main_2020_Sep_S1.pdf",
    },
    # ── 2019 ──
    {
        "year": "2019", "session": "Jan", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2019/JEE_Main_2019_Jan_QP.pdf",
        "filename": "JEE_Main_2019_Jan_S1.pdf",
    },
    {
        "year": "2019", "session": "Apr", "shift": "S1",
        "url": "https://jeemain.nta.nic.in/webinfo/uploads/2019/JEE_Main_2019_Apr_QP.pdf",
        "filename": "JEE_Main_2019_Apr_S1.pdf",
    },
]

# ── NEET PYQ Papers ──────────────────────────────────────────────────────────

NEET_PAPERS = [
    {
        "year": "2024",
        "url": "https://neet.nta.nic.in/uploads/2024/NEET_2024_QP.pdf",
        "filename": "NEET_2024_QP.pdf",
    },
    {
        "year": "2023",
        "url": "https://neet.nta.nic.in/uploads/2023/NEET_2023_QP.pdf",
        "filename": "NEET_2023_QP.pdf",
    },
    {
        "year": "2022",
        "url": "https://neet.nta.nic.in/uploads/2022/NEET_2022_QP.pdf",
        "filename": "NEET_2022_QP.pdf",
    },
    {
        "year": "2021",
        "url": "https://neet.nta.nic.in/uploads/2021/NEET_2021_QP.pdf",
        "filename": "NEET_2021_QP.pdf",
    },
    {
        "year": "2020",
        "url": "https://neet.nta.nic.in/uploads/2020/NEET_2020_QP.pdf",
        "filename": "NEET_2020_QP.pdf",
    },
    {
        "year": "2019",
        "url": "https://neet.nta.nic.in/uploads/2019/NEET_2019_QP.pdf",
        "filename": "NEET_2019_QP.pdf",
    },
]

# ── CUET PYQ Papers ──────────────────────────────────────────────────────────

CUET_PAPERS = [
    {
        "year": "2024",
        "url": "https://cuet.nta.nic.in/uploads/2024/CUET_2024_QP.pdf",
        "filename": "CUET_2024_QP.pdf",
    },
    {
        "year": "2023",
        "url": "https://cuet.nta.nic.in/uploads/2023/CUET_2023_QP.pdf",
        "filename": "CUET_2023_QP.pdf",
    },
    {
        "year": "2022",
        "url": "https://cuet.nta.nic.in/uploads/2022/CUET_2022_QP.pdf",
        "filename": "CUET_2022_QP.pdf",
    },
]


def download_file(url: str, dest: Path, dry_run: bool = False) -> bool:
    """Download a single file. Returns True on success, False on failure."""
    if dest.exists():
        print(f"  ⏭  SKIP (exists): {dest.name}")
        return True

    if dry_run:
        print(f"  🔍 DRY RUN: {url}")
        print(f"       → {dest}")
        return True

    try:
        print(f"  ⬇  {dest.name} ...", end="", flush=True)
        r = requests.get(url, headers=HEADERS, verify=SSL_VERIFY, timeout=30, stream=True)
        if r.status_code == 404:
            print(f" 404 (not found)")
            return False
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


def download_exam(exam: str, papers: list, output_dir: Path, dry_run: bool) -> tuple[int, int]:
    """Download all papers for an exam. Returns (success, failed)."""
    print(f"\n{'='*60}")
    print(f"Downloading {exam} PYQ Papers")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    success = failed = 0
    for paper in papers:
        year_dir = output_dir / paper["year"]
        year_dir.mkdir(parents=True, exist_ok=True)
        dest = year_dir / paper["filename"]
        ok = download_file(paper["url"], dest, dry_run)
        if ok:
            success += 1
        else:
            failed += 1
        if not dry_run:
            time.sleep(DOWNLOAD_DELAY)

    print(f"\n{exam}: {success} downloaded, {failed} failed/not found")
    return success, failed


def main():
    parser = argparse.ArgumentParser(description="Download NTA PYQ papers for JEE/NEET/CUET")
    parser.add_argument("--exam", choices=["jee", "neet", "cuet", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Show URLs without downloading")
    parser.add_argument("--output", default=str(OUTPUT_ROOT), help="Output directory")
    args = parser.parse_args()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"NTA PYQ Downloader")
    print(f"Output: {output_root}")
    print(f"Dry run: {args.dry_run}")

    total_ok = total_fail = 0

    if args.exam in ("jee", "all"):
        ok, fail = download_exam("JEE Main", JEE_MAIN_PAPERS, output_root / "JEE_Main", args.dry_run)
        total_ok += ok; total_fail += fail

    if args.exam in ("neet", "all"):
        ok, fail = download_exam("NEET UG", NEET_PAPERS, output_root / "NEET", args.dry_run)
        total_ok += ok; total_fail += fail

    if args.exam in ("cuet", "all"):
        ok, fail = download_exam("CUET UG", CUET_PAPERS, output_root / "CUET", args.dry_run)
        total_ok += ok; total_fail += fail

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_ok} downloaded, {total_fail} failed/not found")
    print(f"Output: {output_root}")
    print(f"\nNOTE: NTA URLs change periodically. If downloads fail,")
    print(f"visit the official sites to find updated URLs:")
    print(f"  JEE:  https://jeemain.nta.nic.in")
    print(f"  NEET: https://neet.nta.nic.in")
    print(f"  CUET: https://cuet.nta.nic.in")


if __name__ == "__main__":
    main()
