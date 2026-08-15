#!/usr/bin/env python3
"""
NCERT Exemplar Problems Downloader — Grade 11 & Grade 12
=========================================================
Downloads NCERT Exemplar Problem PDFs from ncert.nic.in for
Grade 11 (Class XI) and Grade 12 (Class XII) — Maths, Physics,
Chemistry, and Biology.

URL pattern:
  https://ncert.nic.in/pdf/publication/exemplarproblem/classXI/{subject}/{code}.pdf
  https://ncert.nic.in/pdf/publication/exemplarproblem/classXII/{subject}/{code}.pdf

Output: ~/Desktop/cbse_ncert_pdfs/Exemplar/Grade_11/  and  .../Grade_12/

Usage:
    cd backend
    python3 scripts/download_ncert_exemplar_grade1112.py           # all
    python3 scripts/download_ncert_exemplar_grade1112.py --grade 11
    python3 scripts/download_ncert_exemplar_grade1112.py --grade 12
    python3 scripts/download_ncert_exemplar_grade1112.py --subjects Maths Physics
    python3 scripts/download_ncert_exemplar_grade1112.py --dry-run
"""

from __future__ import annotations

import argparse
import time
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Paths & Config ─────────────────────────────────────────────────────────────

OUTPUT_ROOT    = Path.home() / "Desktop" / "cbse_ncert_pdfs" / "Exemplar"
NCERT_EXEMPLAR = "https://ncert.nic.in/pdf/publication/exemplarproblem"
DOWNLOAD_DELAY = 0.8
SSL_VERIFY     = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ncert.nic.in/exemplar-problems.php",
}

# ── Catalogue ──────────────────────────────────────────────────────────────────
# (grade_label, folder_name, class_roman, subject_url, subject_folder, code_prefix, max_chapters)
# max_chapters: probe up to this many chapters; stops on first 404.

# Verified June 2026 — only these subjects are published on ncert.nic.in as exemplar PDFs.
# Grade 11 Physics, Grade 11 Chemistry, Grade 12 Chemistry return 404 on all chapter codes.
EXEMPLAR_BOOKS_1112 = [
    # Grade 11 — Maths and Biology only (Physics/Chemistry not published by NCERT)
    ("Grade 11", "Grade_11", "classXI",  "mathematics", "Maths",   "keep2", 16),
    ("Grade 11", "Grade_11", "classXI",  "biology",     "Biology", "keep4", 22),
    # Grade 12 — Maths, Physics, Biology (Chemistry not published by NCERT)
    ("Grade 12", "Grade_12", "classXII", "mathematics", "Maths",   "leep2", 13),
    ("Grade 12", "Grade_12", "classXII", "physics",     "Physics", "leep1", 15),
    ("Grade 12", "Grade_12", "classXII", "biology",     "Biology", "leep4", 16),
]

# ── Chapter name maps ──────────────────────────────────────────────────────────

CHAPTER_NAMES: dict[str, list[str]] = {
    # Grade 11 Maths (16 chapters)
    "keep2": [
        "Sets",
        "Relations and Functions",
        "Trigonometric Functions",
        "Principle of Mathematical Induction",
        "Complex Numbers and Quadratic Equations",
        "Linear Inequalities",
        "Permutations and Combinations",
        "Binomial Theorem",
        "Sequences and Series",
        "Straight Lines",
        "Conic Sections",
        "Introduction to Three Dimensional Geometry",
        "Limits and Derivatives",
        "Mathematical Reasoning",
        "Statistics",
        "Probability",
    ],
    # Grade 11 Physics (14 chapters)
    "keep1": [
        "Units and Measurements",
        "Motion in a Straight Line",
        "Motion in a Plane",
        "Laws of Motion",
        "Work, Energy and Power",
        "System of Particles and Rotational Motion",
        "Gravitation",
        "Mechanical Properties of Solids",
        "Mechanical Properties of Fluids",
        "Thermal Properties of Matter",
        "Thermodynamics",
        "Kinetic Theory",
        "Oscillations",
        "Waves",
    ],
    # Grade 11 Chemistry (14 chapters)
    "keep3": [
        "Some Basic Concepts of Chemistry",
        "Structure of Atom",
        "Classification of Elements and Periodicity in Properties",
        "Chemical Bonding and Molecular Structure",
        "Thermodynamics",
        "Equilibrium",
        "Redox Reactions",
        "Organic Chemistry: Some Basic Principles and Techniques",
        "Hydrocarbons",
        "The s-Block Elements",
        "The p-Block Elements",
        "Hydrogen",
        "Environmental Chemistry",
        "States of Matter",
    ],
    # Grade 11 Biology (22 chapters)
    "keep4": [
        "The Living World",
        "Biological Classification",
        "Plant Kingdom",
        "Animal Kingdom",
        "Morphology of Flowering Plants",
        "Anatomy of Flowering Plants",
        "Structural Organisation in Animals",
        "Cell: The Unit of Life",
        "Biomolecules",
        "Cell Cycle and Cell Division",
        "Photosynthesis in Higher Plants",
        "Respiration in Plants",
        "Plant Growth and Development",
        "Breathing and Exchange of Gases",
        "Body Fluids and Circulation",
        "Excretory Products and Their Elimination",
        "Locomotion and Movement",
        "Neural Control and Coordination",
        "Chemical Coordination and Integration",
        "Digestion and Absorption",
        "Mineral Nutrition",
        "Transport in Plants",
    ],
    # Grade 12 Maths (13 chapters)
    "leep2": [
        "Relations and Functions",
        "Inverse Trigonometric Functions",
        "Matrices",
        "Determinants",
        "Continuity and Differentiability",
        "Application of Derivatives",
        "Integrals",
        "Application of Integrals",
        "Differential Equations",
        "Vector Algebra",
        "Three Dimensional Geometry",
        "Linear Programming",
        "Probability",
    ],
    # Grade 12 Physics (15 chapters)
    "leep1": [
        "Electric Charges and Fields",
        "Electrostatic Potential and Capacitance",
        "Current Electricity",
        "Moving Charges and Magnetism",
        "Magnetism and Matter",
        "Electromagnetic Induction",
        "Alternating Current",
        "Electromagnetic Waves",
        "Ray Optics and Optical Instruments",
        "Wave Optics",
        "Dual Nature of Radiation and Matter",
        "Atoms",
        "Nuclei",
        "Semiconductor Electronics: Materials, Devices and Simple Circuits",
        "Communication Systems",
    ],
    # Grade 12 Chemistry (16 chapters)
    "leep3": [
        "Solutions",
        "Electrochemistry",
        "Chemical Kinetics",
        "The d and f Block Elements",
        "Coordination Compounds",
        "Haloalkanes and Haloarenes",
        "Alcohols, Phenols and Ethers",
        "Aldehydes, Ketones and Carboxylic Acids",
        "Amines",
        "Biomolecules",
        "Polymers",
        "Chemistry in Everyday Life",
        "The Solid State",
        "Surface Chemistry",
        "General Principles and Processes of Isolation of Elements",
        "The p-Block Elements",
    ],
    # Grade 12 Biology (16 chapters) — corrected 2026-08-15, content-verified
    # against each PDF's own self-declared "CHAPTER N" header (leep401.pdf
    # through leep416.pdf). The previous list was missing "Reproduction in
    # Organisms" (the real Chapter 1) entirely, which cascaded an off-by-one
    # shift through the rest, and had a fabricated "Animal Husbandry" entry
    # at position 16 that does not exist in this exemplar book at all — the
    # real Chapter 16 is "Environmental Issues". See
    # docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §5 for the full investigation.
    "leep4": [
        "Reproduction in Organisms",
        "Sexual Reproduction in Flowering Plants",
        "Human Reproduction",
        "Reproductive Health",
        "Principles of Inheritance and Variation",
        "Molecular Basis of Inheritance",
        "Evolution",
        "Human Health and Disease",
        "Strategies for Enhancement in Food Production",
        "Microbes in Human Welfare",
        "Biotechnology: Principles and Processes",
        "Biotechnology and Its Applications",
        "Organisms and Populations",
        "Ecosystem",
        "Biodiversity and Conservation",
        "Environmental Issues",
    ],
}


def get_chapter_name(code_prefix: str, chapter_num: int) -> str:
    """Return the chapter name for a given code prefix and 1-based chapter number."""
    names = CHAPTER_NAMES.get(code_prefix, [])
    idx = chapter_num - 1
    if 0 <= idx < len(names):
        return names[idx]
    return f"Chapter {chapter_num}"


def download_book(
    grade_label: str,
    folder_name: str,
    class_roman: str,
    subject_url: str,
    subject_folder: str,
    code_prefix: str,
    max_chapters: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Download all chapters for one exemplar book. Returns (downloaded, skipped)."""
    out_dir = OUTPUT_ROOT / folder_name / subject_folder
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = skipped = 0

    for n in range(1, max_chapters + 1):
        code = f"{code_prefix}{n:02d}"
        url = f"{NCERT_EXEMPLAR}/{class_roman}/{subject_url}/{code}.pdf"
        dest = out_dir / f"{code}.pdf"

        if dest.exists() and dest.stat().st_size > 1000:
            print(f"    skip (exists) {code}.pdf")
            skipped += 1
            continue

        if dry_run:
            print(f"    [dry-run] would download → {url}")
            continue

        try:
            r = requests.get(url, headers=HEADERS, timeout=30, verify=SSL_VERIFY)
            if r.status_code == 200 and len(r.content) > 1000:
                dest.write_bytes(r.content)
                chapter_name = get_chapter_name(code_prefix, n)
                print(f"    ✓ {code}.pdf  ({len(r.content)//1024}KB) — {chapter_name}")
                downloaded += 1
            elif r.status_code == 404:
                print(f"    404 — stopping at chapter {n} (last chapter found: {n-1})")
                break
            else:
                print(f"    WARN {code}.pdf → HTTP {r.status_code}")
        except Exception as e:
            print(f"    ERROR {code}.pdf → {e}")

        time.sleep(DOWNLOAD_DELAY)

    # Also try to download the answers PDF ({code_prefix}an.pdf)
    ans_code = f"{code_prefix}an"
    ans_url = f"{NCERT_EXEMPLAR}/{class_roman}/{subject_url}/{ans_code}.pdf"
    ans_dest = out_dir / f"{ans_code}.pdf"
    if not dry_run and not (ans_dest.exists() and ans_dest.stat().st_size > 1000):
        try:
            r = requests.get(ans_url, headers=HEADERS, timeout=30, verify=SSL_VERIFY)
            if r.status_code == 200 and len(r.content) > 1000:
                ans_dest.write_bytes(r.content)
                print(f"    ✓ {ans_code}.pdf (answers)  ({len(r.content)//1024}KB)")
                downloaded += 1
            time.sleep(DOWNLOAD_DELAY)
        except Exception:
            pass

    return downloaded, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download NCERT Exemplar PDFs for Grade 11 and 12."
    )
    parser.add_argument("--grade", choices=["11", "12"], help="Only one grade")
    parser.add_argument(
        "--subjects", nargs="+",
        choices=["Maths", "Physics", "Chemistry", "Biology"],
        help="Filter subjects",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print URLs only")
    args = parser.parse_args()

    print("=" * 60)
    print("NCERT Exemplar Downloader — Grade 11 & 12")
    print(f"Output: {OUTPUT_ROOT}")
    print("=" * 60)

    total_dl = total_skip = 0

    for grade_label, folder_name, class_roman, subject_url, subject_folder, code_prefix, max_ch in EXEMPLAR_BOOKS_1112:
        grade_num = grade_label.split()[-1]
        if args.grade and grade_num != args.grade:
            continue
        if args.subjects and subject_folder not in args.subjects:
            continue

        print(f"\n📚 {grade_label} — {subject_folder}")
        dl, sk = download_book(
            grade_label, folder_name, class_roman, subject_url,
            subject_folder, code_prefix, max_ch, dry_run=args.dry_run,
        )
        total_dl += dl
        total_skip += sk

    print("\n" + "=" * 60)
    print(f"Done.  Downloaded: {total_dl}   Skipped (already exist): {total_skip}")
    print(f"PDFs saved to: {OUTPUT_ROOT}")
    print("\nNext step:")
    print("  python3 scripts/upload_ncert_exemplar_grade1112_rag.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
