#!/usr/bin/env python3
"""
NCERT Exemplar Problems Downloader — Grade 8, 9, 10 (Maths & Science)
=====================================================================
Downloads NCERT Exemplar Problem PDFs from ncert.nic.in and saves them
to the project's RAG DB/Exemplar/ folder, ready for RAG ingestion.

URL pattern (confirmed from ncert.nic.in/exemplar-problems.php):
  Maths:   https://ncert.nic.in/pdf/publication/exemplarproblem/class{VIII/IX/X}/mathematics/{code}.pdf
  Science: https://ncert.nic.in/pdf/publication/exemplarproblem/class{VIII/IX/X}/science/{code}.pdf

Content:
  Grade 8  Maths:   heep201..heep213 + heep2an (answers)   → 13 units
  Grade 8  Science: heep101..heep118 + heep1an (answers)   → 18 chapters
  Grade 9  Maths:   ieep201..ieep216 + ieep2an (answers)   → 16 units
  Grade 9  Science: ieep101..ieep117 + ieep1an (answers)   → 17 chapters
  Grade 10 Maths:   jeep201..jeep215 + jeep2an (answers)   → 15 units
  Grade 10 Science: jeep101..jeep118 + jeep1an (answers)   → 18 chapters

Usage:
    cd backend
    python3 scripts/download_ncert_exemplar.py              # all grades
    python3 scripts/download_ncert_exemplar.py --grades 9 10
    python3 scripts/download_ncert_exemplar.py --subjects Maths
    python3 scripts/download_ncert_exemplar.py --dry-run
"""

from __future__ import annotations

import argparse
import time
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Paths & Config ─────────────────────────────────────────────────────────────

RAG_DB_ROOT    = Path(__file__).resolve().parents[2] / "RAG DB"
EXEMPLAR_ROOT  = RAG_DB_ROOT / "Exemplar"
NCERT_EXEMPLAR = "https://ncert.nic.in/pdf/publication/exemplarproblem"
DOWNLOAD_DELAY = 0.8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ncert.nic.in/exemplar-problems.php",
}

# ── Catalogue — verified from NCERT exemplar-problems.php (June 2026) ─────────
# Each entry: (grade_label, folder_name, subject_folder, base_code, start_num, end_num)
# base_code: the file prefix (e.g. "heep2" for G8 Maths)
# Files are: {base_code}{nn:02d}.pdf + {base_code}an.pdf (answers)

EXEMPLAR_BOOKS = [
    # Grade 8
    ("Grade 8",  "Grade_8",  "Maths",   "mathematics", "heep2", 1, 13),
    ("Grade 8",  "Grade_8",  "Science", "science",     "heep1", 1, 18),
    # Grade 9
    ("Grade 9",  "Grade_9",  "Maths",   "mathematics", "ieep2", 1, 16),
    ("Grade 9",  "Grade_9",  "Science", "science",     "ieep1", 1, 17),
    # Grade 10
    ("Grade 10", "Grade_10", "Maths",   "mathematics", "jeep2", 1, 15),
    ("Grade 10", "Grade_10", "Science", "science",     "jeep1", 1, 18),
]

# ── Unit names (from ncert.nic.in exemplar page HTML) ─────────────────────────

EXEMPLAR_UNIT_NAMES = {
    # Grade 8 Maths — corrected 2026-08-15, content-verified against each
    # PDF's own "Main Concepts and Results" body text (heep212 also has a
    # self-declared "UNIT 12" header confirming position 12 independently).
    # The previous heep206/208/209/210/211/213 assignments were a cyclic
    # mislabeling. See docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §5a.
    "heep201": "Rational Numbers",
    "heep202": "Data Handling",
    "heep203": "Square-Square Root and Cube-Cube Root",
    "heep204": "Linear Equation in One Variable",
    "heep205": "Understanding Quadrilaterals and Practical Geometry",
    "heep206": "Visualising Solid Shapes",
    "heep207": "Algebraic Expressions and Identities",
    "heep208": "Exponents and Powers",
    "heep209": "Comparing Quantities",
    "heep210": "Direct and Inverse Proportions",
    "heep211": "Mensuration",
    "heep212": "Introduction to Graphs",
    "heep213": "Playing with Numbers",
    # Grade 8 Science — corrected 2026-08-15, content-verified against each
    # PDF's own self-declared "N ChapterTitle" header (heep101 through
    # heep118 all have one, cleanly). Positions 8-18 (11 of 18 chapters)
    # were mislabeled/scrambled in the previous version; 1-7 were correct.
    # "Force and Pressure"/"Stars and the Solar System" match the frontend
    # TOPIC_CARDS naming (the PDF's own headers are terser: "Force" and
    # "Stars and Solar System"). See
    # docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §5a.
    "heep101": "Crop Production and Management",
    "heep102": "Microorganisms: Friend and Foe",
    "heep103": "Synthetic Fibres and Plastics",
    "heep104": "Materials: Metals and Non-Metals",
    "heep105": "Coal and Petroleum",
    "heep106": "Combustion and Flame",
    "heep107": "Conservation of Plants and Animals",
    "heep108": "Cell - Structure and Functions",
    "heep109": "Reproduction in Animals",
    "heep110": "Reaching the Age of Adolescence",
    "heep111": "Force and Pressure",
    "heep112": "Friction",
    "heep113": "Sound",
    "heep114": "Chemical Effects of Electric Current",
    "heep115": "Some Natural Phenomena",
    "heep116": "Light",
    "heep117": "Stars and the Solar System",
    "heep118": "Pollution of Air and Water",
    # Grade 9 Maths
    "ieep201": "Number Systems",
    "ieep202": "Polynomials",
    "ieep203": "Coordinate Geometry",
    "ieep204": "Linear Equations in Two Variables",
    "ieep205": "Introduction to Euclid's Geometry",
    "ieep206": "Lines and Angles",
    "ieep207": "Triangles",
    "ieep208": "Quadrilaterals",
    "ieep209": "Areas of Parallelograms and Triangles",
    "ieep210": "Circles",
    "ieep211": "Constructions",
    "ieep212": "Heron's Formula",
    "ieep213": "Surface Areas and Volumes",
    "ieep214": "Statistics",
    "ieep215": "Probability",
    "ieep216": "Coordinate Geometry (Advanced)",
    # Grade 9 Science
    "ieep101": "Matter in Our Surroundings",
    "ieep102": "Is Matter Around Us Pure",
    "ieep103": "Atoms and Molecules",
    "ieep104": "Structure of the Atom",
    "ieep105": "The Fundamental Unit of Life",
    "ieep106": "Tissues",
    "ieep107": "Diversity in Living Organisms",
    "ieep108": "Motion",
    "ieep109": "Force and Laws of Motion",
    "ieep110": "Gravitation",
    "ieep111": "Work and Energy",
    "ieep112": "Sound",
    "ieep113": "Why Do We Fall Ill",
    "ieep114": "Natural Resources",
    "ieep115": "Improvement in Food Resources",
    "ieep116": "Cells - Their Structure and Functions",
    "ieep117": "Animals - Their Structure and Functions",
    # Grade 10 Maths
    "jeep201": "Real Numbers",
    "jeep202": "Polynomials",
    "jeep203": "Pair of Linear Equations in Two Variables",
    "jeep204": "Quadratic Equations",
    "jeep205": "Arithmetic Progressions",
    "jeep206": "Triangles",
    "jeep207": "Coordinate Geometry",
    "jeep208": "Introduction to Trigonometry and Its Applications",
    "jeep209": "Circles",
    "jeep210": "Constructions",
    "jeep211": "Areas Related to Circles",
    "jeep212": "Surface Areas and Volumes",
    # jeep213 is the real, sole "CHAPTER 13: STATISTICS AND PROBABILITY"
    # (self-declared header, content-verified 2026-08-15) — Grade 10 Maths
    # Exemplar has only 13 real chapters. jeep214/215 are NOT chapters at
    # all; they're "SET-I"/"SET-II DESIGN OF THE QUESTION PAPER" sample-
    # paper blueprints bundled at the end of the download range (same bonus-
    # file pattern as Grade 9/10's other "last unit" entries — see
    # docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §5b — except this one WAS
    # wrongly chapter-mapped and DOES collide with real TOPIC_CARDS entries:
    # ExemplarResearchPage.jsx's Grade 10 Maths "Statistics" and
    # "Probability" cards both need jeep213's content — see the
    # MULTI_CARD_CHAPTER_ALIASES in prepare_gpt55_exemplar_explanation_prompts.py.
    "jeep213": "Statistics and Probability",
    # Grade 10 Science
    "jeep101": "Chemical Reactions and Equations",
    "jeep102": "Acids, Bases and Salts",
    "jeep103": "Metals and Non-metals",
    "jeep104": "Carbon and Its Compounds",
    "jeep105": "Periodic Classification of Elements",
    "jeep106": "Life Processes",
    "jeep107": "Control and Coordination",
    "jeep108": "How Do Organisms Reproduce",
    "jeep109": "Heredity and Evolution",
    "jeep110": "Light - Reflection and Refraction",
    "jeep111": "Human Eye and the Colourful World",
    "jeep112": "Electricity",
    "jeep113": "Magnetic Effects of Electric Current",
    "jeep114": "Sources of Energy",
    "jeep115": "Our Environment",
    "jeep116": "Management of Natural Resources",
    "jeep117": "Carbon and Its Compounds (Advanced)",
    "jeep118": "Chemical Reactions and Equations (Advanced)",
}


def build_url(class_folder: str, subject_folder: str, filename: str) -> str:
    return f"{NCERT_EXEMPLAR}/{class_folder}/{subject_folder}/{filename}.pdf"


CLASS_FOLDER = {
    "Grade_8":  "classVIII",
    "Grade_9":  "classIX",
    "Grade_10": "classX",
}


def download_file(url: str, out_path: Path, dry_run: bool, skip_existing: bool) -> bool:
    """Download one PDF. Returns True if downloaded/skipped-as-existing."""
    if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
        print(f"    [skip] {out_path.name} already exists")
        return True

    if dry_run:
        try:
            r = requests.head(url, headers=HEADERS, timeout=10,
                              allow_redirects=True, verify=False)
            if r.status_code == 200:
                print(f"    [would download] {out_path.name}")
                return True
            else:
                print(f"    [not available] {out_path.name} → HTTP {r.status_code}")
                return False
        except Exception as e:
            print(f"    [error] {e}")
            return False
        finally:
            time.sleep(0.1)

    try:
        r = requests.get(url, headers=HEADERS, timeout=30,
                         stream=True, verify=False)
    except Exception as e:
        print(f"    [ERROR] {url}: {e}")
        return False

    if r.status_code == 200:
        content = b"".join(r.iter_content(chunk_size=8192))
        if len(content) < 500:
            print(f"    [too small] {out_path.name} — skipping")
            return False
        out_path.write_bytes(content)
        print(f"    ✅ {out_path.name}  ({len(content) // 1024} KB)")
        time.sleep(DOWNLOAD_DELAY)
        return True
    elif r.status_code == 404:
        print(f"    [404] {out_path.name} — not available")
        return False
    else:
        print(f"    [HTTP {r.status_code}] {out_path.name}")
        return False


def run_downloader(
    grades_filter: list[int] | None,
    subject_filter: list[str] | None,
    dry_run: bool,
    skip_existing: bool,
) -> None:
    total = 0
    summary: dict[str, int] = {}

    print()
    print("  NCERT Exemplar Problems Downloader — Grade 8, 9, 10")
    print(f"  Output: {EXEMPLAR_ROOT}")
    if dry_run:
        print("  Mode: DRY RUN")
    print()

    EXEMPLAR_ROOT.mkdir(parents=True, exist_ok=True)

    for (grade_label, folder_name, subject, subject_folder, base_code, start, end) in EXEMPLAR_BOOKS:
        grade_num = int(grade_label.split()[-1])

        if grades_filter and grade_num not in grades_filter:
            continue
        if subject_filter and not any(sf.lower() in subject.lower() for sf in subject_filter):
            continue

        class_folder = CLASS_FOLDER[folder_name]
        dest_dir = EXEMPLAR_ROOT / folder_name / subject
        dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  {grade_label} — {subject} Exemplar  [{base_code}xx]")
        print(f"  URL: {NCERT_EXEMPLAR}/{class_folder}/{subject_folder}/")
        print(f"  Output: {dest_dir}")
        print(f"{'='*60}")

        book_count = 0
        for unit_num in range(start, end + 1):
            filename = f"{base_code}{unit_num:02d}"
            url = build_url(class_folder, subject_folder, filename)
            out_path = dest_dir / f"{filename}.pdf"
            unit_name = EXEMPLAR_UNIT_NAMES.get(filename, f"Unit {unit_num}")
            print(f"  Unit {unit_num:02d}: {unit_name}")
            if download_file(url, out_path, dry_run, skip_existing):
                book_count += 1

        # Also download the answers file
        ans_filename = f"{base_code}an"
        ans_url = build_url(class_folder, subject_folder, ans_filename)
        ans_path = dest_dir / f"{ans_filename}.pdf"
        print(f"  Answers: {ans_filename}")
        download_file(ans_url, ans_path, dry_run, skip_existing)

        total += book_count
        summary[f"{grade_label} / {subject}"] = book_count

    print(f"\n\n{'='*60}")
    print(f"  DOWNLOAD COMPLETE — {total} exemplar unit PDFs")
    print(f"{'='*60}")
    for key, n in summary.items():
        if n:
            print(f"  {key}: {n} units")
    print(f"\n  Output folder: {EXEMPLAR_ROOT}")
    print()
    print("  Next step:")
    print("    python3 scripts/upload_ncert_exemplar_rag.py")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download NCERT Exemplar Problems — Grade 8, 9, 10"
    )
    parser.add_argument("--grades", nargs="+", type=int, choices=[8, 9, 10],
                        help="Download specific grades (default: 8 9 10)")
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT",
                        help="Filter: Maths or Science")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without saving")
    parser.add_argument("--no-skip", action="store_true",
                        help="Re-download even if file already exists")
    args = parser.parse_args()

    run_downloader(
        grades_filter=args.grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
    )


if __name__ == "__main__":
    main()
