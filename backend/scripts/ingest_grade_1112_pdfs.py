#!/usr/bin/env python3
"""
Grade 11 & 12 NCERT PDF Bulk Ingestion Script
==============================================
Reads all chapter PDFs from Desktop/cbse_ncert_pdfs/Grade_11/ and Grade_12/,
extracts text using PyMuPDF, chunks it, embeds with text-embedding-3-small,
and stores everything in the Grade 11 & 12 Supabase project.

Usage:
    cd /Users/a0247716/Pradips_Project/cbse-tutor-platform/backend
    python3 scripts/ingest_grade_1112_pdfs.py

Requirements:
    pip install pymupdf openai supabase python-dotenv

Environment variables (set in .env or export before running):
    OPENAI_API_KEY             — for embeddings
    SUPABASE_GRADE_1112_URL    — second Supabase project URL (optional, falls back to hardcoded)
    SUPABASE_GRADE_1112_SERVICE_KEY — service_role key (optional, falls back to hardcoded)
"""

import os
import sys
import time
import re
from pathlib import Path

# ── Add project root to path so app.services imports work ────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")

# ── PDF folder ────────────────────────────────────────────────────────────────
PDF_ROOT = Path("/Users/a0247716/Desktop/cbse_ncert_pdfs")

# ── NCERT chapter-number → chapter-title mapping ─────────────────────────────
# Folder name (Grade_11/Physics) → list of chapter titles in order.
# Titles come from the official NCERT chapter headings.
CHAPTER_TITLES: dict[str, list[str]] = {

    # ── Grade 11 ─────────────────────────────────────────────────────────────
    "Grade_11/Physics": [
        # Part 1 (keph101–107)
        "Physical World",
        "Units and Measurements",
        "Motion in a Straight Line",
        "Motion in a Plane",
        "Laws of Motion",
        "Work, Energy and Power",
        "Systems of Particles and Rotational Motion",
        # Part 2 (keph201–207)
        "Gravitation",
        "Mechanical Properties of Solids",
        "Mechanical Properties of Fluids",
        "Thermal Properties of Matter",
        "Thermodynamics",
        "Kinetic Theory",
        "Oscillations",
        "Waves",
    ],
    "Grade_11/Chemistry": [
        # Part 1 (kech101–106)
        "Some Basic Concepts of Chemistry",
        "Structure of Atom",
        "Classification of Elements and Periodicity in Properties",
        "Chemical Bonding and Molecular Structure",
        "States of Matter",
        "Thermodynamics",
        # Part 2 (kech201–203) — numbered 7+ in full book
        "Equilibrium",
        "Redox Reactions",
        "Hydrogen",
    ],
    "Grade_11/Mathematics": [
        # Part 1 (kemh101–110)
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
    ],
    "Grade_11/Biology": [
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
        "Transport in Plants",
        "Mineral Nutrition",
        "Photosynthesis in Higher Plants",
        "Respiration in Plants",
        "Plant Growth and Development",
        "Digestion and Absorption",
        "Breathing and Exchange of Gases",
        "Body Fluids and Circulation",
        "Excretory Products and Their Elimination",
        "Locomotion and Movement",
        "Neural Control and Coordination",
        "Chemical Coordination and Integration",
    ],
    "Grade_11/English": [
        "The Portrait of a Lady",
        "We're Not Afraid to Die",
        "Discovering Tut: the Saga Continues",
        "Landscape of the Soul",
        "The Ailing Planet: The Green Movement's Role",
    ],
    "Grade_11/Economics": [
        # Indian Economic Development (keec101–108)
        "Indian Economy on the Eve of Independence",
        "Indian Economy 1950–1990",
        "Liberalisation, Privatisation and Globalisation",
        "Poverty",
        "Human Capital Formation in India",
        "Rural Development",
        "Employment: Growth, Informalisation and Other Issues",
        "Infrastructure",
        # Statistics for Economics (kest101–108)
        "Introduction to Statistics",
        "Collection of Data",
        "Organisation of Data",
        "Presentation of Data",
        "Measures of Central Tendency",
        "Measures of Dispersion",
        "Correlation",
        "Index Numbers",
    ],
    "Grade_11/Business_Studies": [
        "Business, Trade and Commerce",
        "Forms of Business Organisation",
        "Private, Public and Global Enterprises",
        "Business Services",
        "Emerging Modes of Business",
        "Social Responsibilities of Business and Business Ethics",
        "Formation of a Company",
        "Sources of Business Finance",
        "Small Business",
        "Internal Trade",
    ],
    "Grade_11/Accountancy": [
        # Part 1 (keac101–107)
        "Introduction to Accounting",
        "Theory Base of Accounting",
        "Recording of Transactions – I",
        "Recording of Transactions – II",
        "Bank Reconciliation Statement",
        "Trial Balance and Rectification of Errors",
        "Depreciation, Provisions and Reserves",
        # Part 2 (keac201–202)
        "Bill of Exchange",
        "Financial Statements – I",
    ],
    "Grade_11/Geography": [
        # Fundamentals of Physical Geography (kegy101–106)
        "Geography as a Discipline",
        "The Origin and Evolution of the Earth",
        "Interior of the Earth",
        "Distribution of Oceans and Continents",
        "Minerals and Rocks",
        "Geomorphic Processes",
        # India — Physical Environment (kegy201–210)
        "India — Location",
        "Structure and Physiography",
        "Drainage System",
        "Climate",
        "Natural Vegetation",
        "Soils",
        "Natural Hazards and Disasters",
        "Population",  # note: kegy208–210 may be additional chapters
        "Migration",
        "Human Settlements",
    ],

    # ── Grade 12 ─────────────────────────────────────────────────────────────
    "Grade_12/Physics": [
        # Part 1 (leph101–108)
        "Electric Charges and Fields",
        "Electrostatic Potential and Capacitance",
        "Current Electricity",
        "Moving Charges and Magnetism",
        "Magnetism and Matter",
        "Electromagnetic Induction",
        "Alternating Current",
        "Electromagnetic Waves",
        # Part 2 (leph201–206)
        "Ray Optics and Optical Instruments",
        "Wave Optics",
        "Dual Nature of Radiation and Matter",
        "Atoms",
        "Nuclei",
        "Semiconductor Electronics",
    ],
    "Grade_12/Chemistry": [
        # Part 1 (lech101–105)
        "The Solid State",
        "Solutions",
        "Electrochemistry",
        "Chemical Kinetics",
        "Surface Chemistry",
        # Part 2 (lech201–205)
        "General Principles and Processes of Isolation of Elements",
        "The p-Block Elements",
        "The d- and f-Block Elements",
        "Coordination Compounds",
        "Haloalkanes and Haloarenes",
    ],
    "Grade_12/Mathematics": [
        # Part 1 (lemh101–106)
        "Relations and Functions",
        "Inverse Trigonometric Functions",
        "Matrices",
        "Determinants",
        "Continuity and Differentiability",
        "Application of Derivatives",
        # Part 2 (lemh201–207)
        "Integrals",
        "Application of Integrals",
        "Differential Equations",
        "Vector Algebra",
        "Three Dimensional Geometry",
        "Linear Programming",
        "Probability",
    ],
    "Grade_12/Biology": [
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
        "Biotechnology and its Applications",
        "Organisms and Populations",
    ],
    "Grade_12/English": [
        "The Last Lesson",
        "Lost Spring",
        "Deep Water",
        "The Rattrap",
        "Indigo",
        "Poets and Pancakes",
        "The Interview",
        "Going Places",
    ],
    "Grade_12/Economics": [
        "Introduction to Macroeconomics",
        "National Income Accounting",
        "Money and Banking",
        "Determination of Income and Employment",
        "Government Budget and the Economy",
        "Open Economy Macroeconomics",
    ],
    "Grade_12/Business_Studies": [
        # Part 1 (lebs101–108)
        "Nature and Significance of Management",
        "Principles of Management",
        "Business Environment",
        "Planning",
        "Organising",
        "Staffing",
        "Directing",
        "Controlling",
        # Part 2 (lebs201–203)
        "Financial Management",
        "Financial Markets",
        "Marketing Management",
    ],
    "Grade_12/Accountancy": [
        # Part 1 (leac101–104)
        "Accounting for Not-for-Profit Organisations",
        "Accounting for Partnership: Basic Concepts",
        "Reconstitution of a Partnership Firm – Admission of a Partner",
        "Reconstitution of a Partnership Firm – Retirement/Death of a Partner",
        # Part 2 (leac201–206)
        "Dissolution of Partnership Firm",
        "Accounting for Share Capital",
        "Issue and Redemption of Debentures",
        "Financial Statements of a Company",
        "Analysis of Financial Statements",
        "Accounting Ratios",
    ],
    "Grade_12/Geography": [
        "Human Geography: Nature and Scope",
        "The World Population: Distribution, Density and Growth",
        "Population Composition",
        "Human Development",
        "Primary Activities",
        "Secondary Activities",
        "Tertiary and Quaternary Activities",
        "Transport and Communication",
    ],
}

# ── Subject name normalisations (folder → app subject name) ──────────────────
SUBJECT_MAP = {
    "Physics":          "Physics",
    "Chemistry":        "Chemistry",
    "Mathematics":      "Mathematics",
    "Biology":          "Biology",
    "English":          "English",
    "Hindi":            "Hindi",
    "Economics":        "Economics",
    "Business_Studies": "Business Studies",
    "Accountancy":      "Accountancy",
    "Geography":        "Geography",
    "History":          "History",
    "Political_Science": "Political Science",
    "Sociology":        "Sociology",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using PyMuPDF. Returns empty string on failure."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n".join(pages).strip()
    except Exception as e:
        print(f"    ⚠️  PyMuPDF error on {pdf_path.name}: {e}")
        return ""


def clean_text(text: str) -> str:
    """Remove control characters and excessive whitespace."""
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {3,}", " ", text)
    return text.strip()


def split_into_chunks(text: str, chunk_size: int = 1200) -> list[str]:
    """Split text into ~chunk_size character word-boundary chunks."""
    words = text.split()
    chunks = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= chunk_size:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def create_embedding(text: str, openai_client) -> list[float]:
    """Create a 1536-dim embedding using text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


# ── Main ingestion ────────────────────────────────────────────────────────────

def ingest_all_pdfs(dry_run: bool = False, subjects_filter: list[str] | None = None):
    """
    Walk the PDF folder tree and ingest all chapter PDFs.

    dry_run=True: extract text and count chunks without writing to Supabase.
    subjects_filter: list of subject folder names to process (e.g. ["Physics"]).
    """
    # Lazy imports — only needed when running
    import openai
    from supabase import create_client

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌  OPENAI_API_KEY not set. Export it or add it to .env")
        sys.exit(1)

    openai_client = openai.OpenAI(api_key=openai_api_key)

    sb_url = os.getenv(
        "SUPABASE_GRADE_1112_URL",
        "https://sjfjyzaaypfzyfhhggqw.supabase.co",
    )
    sb_key = os.getenv(
        "SUPABASE_GRADE_1112_SERVICE_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqZmp5emFheXBmenlmaGhnZ3F3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjE2NDM2MywiZXhwIjoyMDk3NzQwMzYzfQ.VNbQ2cHF0sPSoR7zy5uVi993SHXtLomK8eJkeu6LwTs",
    )

    if not dry_run:
        sb = create_client(sb_url, sb_key)
        print(f"✅  Connected to Supabase: {sb_url}")
    else:
        sb = None
        print("🔍  DRY RUN — no data will be written to Supabase\n")

    total_docs = 0
    total_chunks = 0
    skipped = 0
    errors = 0

    for grade_folder in sorted(PDF_ROOT.iterdir()):
        if not grade_folder.is_dir() or grade_folder.name.startswith("."):
            continue
        grade_name = grade_folder.name.replace("_", " ")  # "Grade 11"

        for subject_folder in sorted(grade_folder.iterdir()):
            if not subject_folder.is_dir() or subject_folder.name.startswith("."):
                continue

            subject_key = subject_folder.name  # e.g. "Physics"
            if subjects_filter and subject_key not in subjects_filter:
                continue

            subject_name = SUBJECT_MAP.get(subject_key, subject_key)
            folder_key = f"{grade_folder.name}/{subject_key}"
            chapter_titles = CHAPTER_TITLES.get(folder_key, [])

            # Collect PDF files sorted by filename (preserves chapter order)
            pdf_files = sorted(subject_folder.rglob("*.pdf"))
            if not pdf_files:
                continue

            print(f"\n📚  {grade_name} / {subject_name}  ({len(pdf_files)} files)")

            for idx, pdf_path in enumerate(pdf_files):
                # Derive chapter title from the mapping (0-based index)
                if idx < len(chapter_titles):
                    chapter_title = chapter_titles[idx]
                else:
                    # Fallback: use filename stem prettified
                    chapter_title = pdf_path.stem.replace("_", " ").title()

                print(f"  [{idx+1:3d}/{len(pdf_files)}]  {pdf_path.name}  →  {chapter_title}")

                # Extract text
                raw_text = extract_text_from_pdf(pdf_path)
                if not raw_text:
                    print(f"         ⚠️  No text extracted — skipping")
                    skipped += 1
                    continue

                text = clean_text(raw_text)
                chunks = split_into_chunks(text)
                print(f"         ✓  {len(text):,} chars  →  {len(chunks)} chunks")

                if dry_run:
                    total_chunks += len(chunks)
                    total_docs += 1
                    continue

                # ── Write to Supabase ─────────────────────────────────────
                try:
                    # 1. Insert rag_document row
                    doc_row = {
                        "uploaded_by": "ingest_script",
                        "board": "CBSE",
                        "grade": grade_name,
                        "subject": subject_name,
                        "chapter": chapter_title,
                        "title": f"{subject_name} — {chapter_title}",
                        "source_type": "pdf",
                    }
                    doc_resp = sb.table("rag_documents").insert(doc_row).execute()
                    if not doc_resp.data:
                        print(f"         ❌  Failed to insert rag_document — skipping")
                        errors += 1
                        continue

                    document_id = doc_resp.data[0]["id"]

                    # 2. Embed and insert chunks in batches of 50
                    chunk_rows = []
                    for chunk_idx, chunk in enumerate(chunks):
                        embedding = create_embedding(chunk, openai_client)
                        chunk_rows.append({
                            "document_id": document_id,
                            "chunk_text": chunk,
                            "chunk_index": chunk_idx,
                            "embedding": embedding,
                        })
                        # Rate-limit: ~150 embedding calls/min on tier-1
                        if (chunk_idx + 1) % 50 == 0:
                            sb.table("rag_chunks").insert(chunk_rows).execute()
                            chunk_rows = []
                            time.sleep(0.5)

                    if chunk_rows:
                        sb.table("rag_chunks").insert(chunk_rows).execute()

                    total_docs += 1
                    total_chunks += len(chunks)
                    print(f"         ✅  Stored doc_id={document_id}, {len(chunks)} chunks")

                    # Small delay between files to avoid hitting API rate limits
                    time.sleep(0.3)

                except Exception as e:
                    print(f"         ❌  Error: {e}")
                    errors += 1

    print(f"\n{'─'*60}")
    print(f"{'DRY RUN COMPLETE' if dry_run else 'INGESTION COMPLETE'}")
    print(f"  Documents : {total_docs}")
    print(f"  Chunks    : {total_chunks}")
    print(f"  Skipped   : {skipped}")
    print(f"  Errors    : {errors}")
    if total_chunks > 0:
        approx_cost = total_chunks * 300 * 0.02 / 1_000_000
        print(f"  Embedding cost estimate: ${approx_cost:.4f}")
    print(f"{'─'*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest Grade 11 & 12 NCERT PDFs into the second Supabase project."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract text and count chunks without writing to Supabase",
    )
    parser.add_argument(
        "--subjects", nargs="+", metavar="SUBJECT",
        help="Only process these subjects (e.g. Physics Chemistry). Default: all.",
    )
    args = parser.parse_args()

    ingest_all_pdfs(dry_run=args.dry_run, subjects_filter=args.subjects)
