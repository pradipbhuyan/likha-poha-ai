#!/usr/bin/env python3
"""
RAG Upload Script — NCERT Grade 11 & Grade 12
=============================================
Reads every chapter PDF from ~/Desktop/cbse_ncert_pdfs/,
extracts text, chunks it, creates OpenAI embeddings, and stores
in rag_documents + rag_chunks (Supabase).

CHAPTER NAME EXTRACTION (zero manual correction):
  Each NCERT book has a prefatory PDF ({book_code}ps.pdf) containing
  the Table of Contents with exact chapter names and page numbers.
  We download that ps.pdf, parse the TOC, and use those names.
  This gives 100% accurate chapter names straight from NCERT.

  Example line in TOC:  "2. Relations and Functions 24"
  Parsed as: chapter 2 → "Relations and Functions"

Prerequisites:
  Run download_ncert_grade11_12.py first to get all chapter PDFs.

Usage:
    cd backend
    python3 scripts/upload_ncert_grade11_12_rag.py               # all
    python3 scripts/upload_ncert_grade11_12_rag.py --grade 11    # Grade 11 only
    python3 scripts/upload_ncert_grade11_12_rag.py --grade 12    # Grade 12 only
    python3 scripts/upload_ncert_grade11_12_rag.py --subjects Physics
    python3 scripts/upload_ncert_grade11_12_rag.py --dry-run
    python3 scripts/upload_ncert_grade11_12_rag.py --force  # re-upload existing
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pdfplumber
import requests
import urllib3

# Grade 11/12 content must go to the second Supabase project (grade_1112_client),
# NOT the primary admin_client (Supabase 1).
# search_textbook_content for Grade 11/12 reads from grade_1112_client.
# If we write to admin_client here, the content is never found by the lesson/doubt search.
from app.services.supabase_grade_1112_client import grade_1112_client as supabase
from app.services.rag_service import create_embedding

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Configuration ──────────────────────────────────────────────────────────────

PDF_ROOT = Path.home() / "Desktop" / "cbse_ncert_pdfs"
NCERT_BASE = "https://ncert.nic.in/textbook/pdf"
BOARD = "CBSE"
UPLOADED_BY = "4f443815-66b3-49a3-a746-04cd34eb7abf"  # Pradip Admin

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
EMBED_DELAY = 0.12
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ncert.nic.in/textbook.php",
}

# ── Subject folder → canonical subject name ────────────────────────────────────

FOLDER_TO_SUBJECT = {
    "Physics":           "Physics",
    "Chemistry":         "Chemistry",
    "Mathematics":       "Mathematics",
    "Biology":           "Biology",
    "English":           "English",
    "Hindi":             "Hindi",
    "Economics":         "Economics",
    "Business_Studies":  "Business Studies",
    "Accountancy":       "Accountancy",
    "History":           "History",
    "Geography":         "Geography",
    "Political_Science": "Political Science",
    "Sociology":         "Sociology",
}

# ── Book catalogue: all book codes per grade ─────────────────────────────────────

GRADE_11_BOOK_CODES = [
    "keph1", "keph2",   # Physics Part 1 & 2
    "kech1", "kech2",   # Chemistry Part 1 & 2
    "kemh1", "kemh2",   # Mathematics Part 1 & 2 (combined book → kemh1ps)
    "kebo1",            # Biology
    "keeh1", "kesp1",   # English Hornbill + Snapshots
    "khah1", "khvt1",   # Hindi Aroh + Vitan
    "keec1", "kest1",   # Economics
    "kebs1", "kebs2",   # Business Studies
    "keac1", "keac2",   # Accountancy
    "kehe1", "kehe2",   # History Part 1 & 2
    "kegy1", "kegy2",   # Geography
    "keps1", "keps2",   # Political Science
    # Sociology: PDFs not available on NCERT portal yet (2024 curriculum)
]

GRADE_12_BOOK_CODES = [
    "leph1", "leph2",   # Physics
    "lech1", "lech2",   # Chemistry
    "lemh1", "lemh2",   # Mathematics
    "lebo1",            # Biology
    "lefl1", "levs1",   # English Flamingo + Vistas
    "lhah1", "lhvt1",   # Hindi
    "leec1", "lema1",   # Economics
    "lebs1", "lebs2",   # Business Studies
    "leac1", "leac2",   # Accountancy
    "lehe1", "lehe2",   # History Part 1 & 2
    "legy1", "legz1",   # Geography
    "leps1", "leps2",   # Political Science
    # Sociology: PDFs not available on NCERT portal yet (2024 curriculum)
]

# book code → subject folder mapping
BOOK_TO_FOLDER = {
    "keph1": "Physics", "keph2": "Physics",
    "kech1": "Chemistry", "kech2": "Chemistry",
    "kemh1": "Mathematics", "kemh2": "Mathematics",
    "kebo1": "Biology",
    "keeh1": "English", "kesp1": "English",
    "khah1": "Hindi", "khvt1": "Hindi",
    "keec1": "Economics", "kest1": "Economics",
    "kebs1": "Business_Studies", "kebs2": "Business_Studies",
    "keac1": "Accountancy", "keac2": "Accountancy",
    "kehe1": "History", "kehe2": "History",
    "kegy1": "Geography", "kegy2": "Geography",
    "keps1": "Political_Science", "keps2": "Political_Science",
    "leph1": "Physics", "leph2": "Physics",
    "lech1": "Chemistry", "lech2": "Chemistry",
    "lemh1": "Mathematics", "lemh2": "Mathematics",
    "lebo1": "Biology",
    "lefl1": "English", "levs1": "English",
    "lhah1": "Hindi", "lhvt1": "Hindi",
    "leec1": "Economics", "lema1": "Economics",
    "lebs1": "Business_Studies", "lebs2": "Business_Studies",
    "leac1": "Accountancy", "leac2": "Accountancy",
    "lehe1": "History", "lehe2": "History",
    "legy1": "Geography", "legz1": "Geography",
    "leps1": "Political_Science", "leps2": "Political_Science",
}

# book code → grade label
BOOK_TO_GRADE = {
    **{code: "Grade 11" for code in GRADE_11_BOOK_CODES},
    **{code: "Grade 12" for code in GRADE_12_BOOK_CODES},
}

# ── Hardcoded chapter overrides ───────────────────────────────────────────────
# Used for books where ps.pdf TOC extraction is unreliable (wrong chapters,
# garbled format, or missing TOC entirely).
# NCERT chapter names are stable — this dict is the authoritative source.
# chapter file numbering is 01-based within each Part (keph201 = Ch1 of Part2).

CHAPTER_OVERRIDES: dict[str, dict[int, str]] = {

    # ── Grade 11 ──────────────────────────────────────────────────────────────

    # keph2ps.pdf has Part 1 TOC (wrong) — override with actual Part 2 chapters
    "keph2": {
        1: "Mechanical Properties of Solids",
        2: "Mechanical Properties of Fluids",
        3: "Thermal Properties of Matter",
        4: "Thermodynamics",
        5: "Kinetic Theory",
        6: "Oscillations",
        7: "Waves",
    },
    "kech1": {
        1: "Some Basic Concepts of Chemistry",
        2: "Structure of Atom",
        3: "Classification of Elements and Periodicity in Properties",
        4: "Chemical Bonding and Molecular Structure",
        5: "Thermodynamics",
        6: "Equilibrium",
    },
    "kech2": {
        1: "Redox Reactions",
        2: "Hydrogen",
        3: "The s-Block Elements",
        4: "The p-Block Elements",
        5: "Organic Chemistry — Some Basic Principles and Techniques",
        6: "Hydrocarbons",
        7: "Environmental Chemistry",
    },
    "kebo1": {
        1: "The Living World",
        2: "Biological Classification",
        3: "Plant Kingdom",
        4: "Animal Kingdom",
        5: "Morphology of Flowering Plants",
        6: "Anatomy of Flowering Plants",
        7: "Structural Organisation in Animals",
        8: "Cell: The Unit of Life",
        9: "Biomolecules",
        10: "Cell Cycle and Cell Division",
        11: "Photosynthesis in Higher Plants",
        12: "Respiration in Plants",
        13: "Plant Growth and Development",
        14: "Breathing and Exchange of Gases",
        15: "Body Fluids and Circulation",
        16: "Excretory Products and their Elimination",
        17: "Locomotion and Movement",
        18: "Neural Control and Coordination",
        19: "Chemical Coordination and Integration",
    },
    "keeh1": {
        1: "The Portrait of a Lady",
        2: "We're Not Afraid to Die — If We Can All Be Together",
        3: "Discovering Tut: The Saga Continues",
        4: "Landscape of the Soul",
        5: "The Ailing Planet: The Green Movement's Role",
        6: "The Browning Version",
        7: "The Adventure",
        8: "Silk Road",
    },
    "kesp1": {
        1: "The Summer of the Beautiful White Horse",
        2: "The Address",
        3: "Ranga's Marriage",
        4: "Albert Einstein at School",
        5: "Mother's Day",
        6: "The Ghat of the Only World",
        7: "Birth",
        8: "The Tale of Melon City",
    },
    "khah1": {
        1: "हम तौ एक एक करि जाना — कबीर",
        2: "मेरे तो गिरधर गोपाल — मीरा",
        3: "पथिक — रामनरेश त्रिपाठी",
        4: "वे आँखें — सुमित्रानंदन पंत",
        5: "घर की याद — भवानीप्रसाद मिश्र",
        6: "चंपा काले-काले अच्छर नहीं चीन्हती — त्रिलोचन",
        7: "गज़ल — दुष्यंत कुमार",
        8: "हे भूख! मत मचल — अक्कमहादेवी",
        9: "सबसे खतरनाक — पाश",
        10: "आओ, मिलकर बचाएँ — निर्मला पुतुल",
        11: "नमक का दारोगा",
        12: "मियाँ नसीरुद्दीन",
        13: "अपू के साथ ढाई साल",
        14: "विदाई-संभाषण",
        15: "गलता लोहा",
        16: "स्पीति में बारिश",
        17: "रजनी",
        18: "जामुन का पेड़",
        19: "भारत माता",
        20: "आत्मा का ताप",
    },
    "khvt1": {
        1: "भारतीय गायिकाओं में बेजोड़: लता मंगेशकर",
        2: "राजस्थान की रजत बूँदें",
        3: "आलो-आँधारि",
    },
    "keec1": {
        1: "Indian Economy on the Eve of Independence",
        2: "Indian Economy 1950-1990",
        3: "Liberalisation, Privatisation and Globalisation: An Appraisal",
        4: "Poverty",
        5: "Human Capital Formation in India",
        6: "Rural Development",
        7: "Employment: Growth, Informalisation and Other Issues",
        8: "Infrastructure",
        9: "Environment and Sustainable Development",
        10: "Comparative Development Experiences of India and Its Neighbours",
    },
    "kest1": {
        1: "Introduction",
        2: "Collection of Data",
        3: "Organisation of Data",
        4: "Presentation of Data",
        5: "Measures of Central Tendency",
        6: "Measures of Dispersion",
        7: "Correlation",
        8: "Index Numbers",
        9: "Use of Statistical Tools",
    },
    "kebs1": {
        1: "Nature and Purpose of Business",
        2: "Forms of Business Organisation",
        3: "Private, Public and Global Enterprises",
        4: "Business Services",
        5: "Emerging Modes of Business",
        6: "Social Responsibility of Business and Business Ethics",
    },
    "kebs2": {
        1: "Sources of Business Finance",
        2: "Small Business",
        3: "Internal Trade",
        4: "International Business",
    },
    "keac1": {
        1: "Introduction to Accounting",
        2: "Theory Base of Accounting",
        3: "Recording of Transactions I",
        4: "Recording of Transactions II",
        5: "Bank Reconciliation Statement",
        6: "Trial Balance and Rectification of Errors",
        7: "Depreciation, Provisions and Reserves",
        8: "Bills of Exchange",
    },
    "keac2": {
        1: "Financial Statements I",
        2: "Financial Statements II",
        3: "Accounts from Incomplete Records",
        4: "Computers in Accounting",
        5: "Accounting Software: Tally",
    },
    "kehe1": {
        1: "From the Beginning of Time",
        2: "Writing and City Life",
        3: "An Empire Across Three Continents",
        4: "The Central Islamic Lands",
        5: "Nomadic Empires",
        6: "The Three Orders",
        7: "Changing Cultural Traditions",
    },
    "kehe2": {
        1: "Confrontation of Cultures",
        2: "The Industrial Revolution",
        3: "Displacing Indigenous Peoples",
        4: "Paths to Modernisation",
    },
    "keps1": {
        1: "Political Theory: An Introduction",
        2: "Freedom",
        3: "Equality",
        4: "Social Justice",
        5: "Rights",
        6: "Citizenship",
        7: "Nationalism",
        8: "Secularism",
    },
    "keps2": {
        1: "Constitution: Why and How?",
        2: "Rights in the Indian Constitution",
        3: "Election and Representation",
        4: "Executive",
        5: "Legislature",
        6: "Judiciary",
        7: "Federalism",
        8: "Local Governments",
        9: "Constitution as a Living Document",
        10: "The Philosophy of the Constitution",
    },
    "kes01": {
        1: "Sociology and Society",
        2: "Terms, Concepts and their Use in Sociology",
        3: "Understanding Social Institutions",
        4: "Culture and Socialisation",
        5: "Doing Sociology: Research Methods",
    },
    "kes02": {
        1: "Social Structure, Stratification and Social Processes in Society",
        2: "Social Change and Social Order in Rural and Urban Society",
        3: "Environment and Society",
        4: "Introducing Western Sociologists",
        5: "Indian Sociologists",
    },
    "kegy1": {
        1: "Geography as a Discipline",
        2: "The Origin and Evolution of the Earth",
        3: "Interior of the Earth",
        4: "Distribution of Oceans and Continents",
        5: "Minerals and Rocks",
        6: "Geomorphic Processes",
        7: "Landforms and their Evolution",
        8: "Composition and Structure of Atmosphere",
        9: "Solar Radiation, Heat Balance and Temperature",
        10: "Atmospheric Circulation and Weather Systems",
        11: "Water in the Atmosphere",
        12: "World Climate and Climate Change",
        13: "Water (Oceans)",
        14: "Movements of Ocean Water",
        15: "Life on the Earth",
        16: "Biodiversity and Conservation",
    },
    "kegy2": {
        1: "India — Location",
        2: "Structure and Physiography",
        3: "Drainage System",
        4: "Climate",
        5: "Natural Vegetation",
        6: "Soils",
        7: "Natural Hazards and Disasters",
    },

    # ── Grade 12 ──────────────────────────────────────────────────────────────

    "leph2": {
        1: "Wave Optics",
        2: "Ray Optics and Optical Instruments",
        3: "Dual Nature of Radiation and Matter",
        4: "Atoms",
        5: "Nuclei",
        6: "Semiconductor Electronics: Materials, Devices and Simple Circuits",
    },
    "lech1": {
        1: "The Solid State",
        2: "Solutions",
        3: "Electrochemistry",
        4: "Chemical Kinetics",
        5: "Surface Chemistry",
        6: "General Principles and Processes of Isolation of Elements",
        7: "The p-Block Elements",
    },
    "lech2": {
        1: "The d and f Block Elements",
        2: "Coordination Compounds",
        3: "Haloalkanes and Haloarenes",
        4: "Alcohols, Phenols and Ethers",
        5: "Aldehydes, Ketones and Carboxylic Acids",
        6: "Amines",
        7: "Biomolecules",
        8: "Polymers",
        9: "Chemistry in Everyday Life",
    },
    "lebo1": {
        1: "Reproduction in Organisms",
        2: "Sexual Reproduction in Flowering Plants",
        3: "Human Reproduction",
        4: "Reproductive Health",
        5: "Principles of Inheritance and Variation",
        6: "Molecular Basis of Inheritance",
        7: "Evolution",
        8: "Human Health and Disease",
        9: "Strategies for Enhancement in Food Production",
        10: "Microbes in Human Welfare",
        11: "Biotechnology: Principles and Processes",
        12: "Biotechnology and its Applications",
        13: "Organisms and Populations",
        14: "Ecosystem",
        15: "Biodiversity and Conservation",
        16: "Environmental Issues",
    },
    "lefl1": {
        1: "The Last Lesson",
        2: "Lost Spring",
        3: "Deep Water",
        4: "The Rattrap",
        5: "Indigo",
        6: "Poets and Pancakes",
        7: "The Interview",
        8: "Going Places",
    },
    "levs1": {
        1: "The Third Level",
        2: "The Tiger King",
        3: "Journey to the End of the Earth",
        4: "The Enemy",
        5: "Should Wizard Hit Mommy?",
        6: "On the Face of It",
        7: "Evans Tries an O-Level",
        8: "Memories of Childhood",
    },
    "lhah1": {
        1: "आत्म-परिचय / एक गीत — हरिवंशराय बच्चन",
        2: "पतंग — आलोक धन्वा",
        3: "कविता के बहाने / बात सीधी थी पर — कुँवर नारायण",
        4: "कैमरे में बंद अपाहिज — रघुवीर सहाय",
        5: "सहर्ष स्वीकारा है — गजानन माधव मुक्तिबोध",
        6: "उषा — शमशेर बहादुर सिंह",
        7: "बादल राग — सूर्यकान्त त्रिपाठी निराला",
        8: "कवितावली / लक्ष्मण-मूर्छा और राम का विलाप — तुलसीदास",
        9: "रुबाइयाँ / गज़ल — फिराक गोरखपुरी",
        10: "छोटा मेरा खेत / बगुलों के पंख — उमाशंकर जोशी",
        11: "भक्तिन",
        12: "बाजार दर्शन",
        13: "काले मेघा पानी दे",
        14: "पहलवान की ढोलक",
        15: "चार्ली चैप्लिन यानी हम सब",
        16: "नमक",
        17: "शिरीष के फूल",
        18: "श्रम-विभाजन और जाति-प्रथा / मेरी कल्पना का आदर्श समाज",
    },
    "lhvt1": {
        1: "सिल्वर वेडिंग",
        2: "जूझ",
        3: "अतीत में दबे पाँव",
        4: "डायरी के पन्ने",
    },
    "leec1": {
        1: "Introduction",
        2: "National Income Accounting",
        3: "Money and Banking",
        4: "Determination of Income and Employment",
        5: "Government Budget and the Economy",
        6: "Open Economy Macroeconomics",
    },
    "lema1": {
        1: "Introduction to Macro Economics",
        2: "National Income Accounting",
        3: "Money and Banking",
        4: "Income Determination",
        5: "Government Budget and the Economy",
        6: "Open Economy Macroeconomics",
    },
    "lebs1": {
        1: "Nature and Significance of Management",
        2: "Principles of Management",
        3: "Business Environment",
        4: "Planning",
        5: "Organising",
        6: "Staffing",
    },
    "lebs2": {
        1: "Directing",
        2: "Controlling",
        3: "Financial Management",
        4: "Financial Markets",
        5: "Marketing Management",
        6: "Consumer Protection",
        7: "Entrepreneurship Development",
    },
    "leac1": {
        1: "Accounting for Partnership: Basic Concepts",
        2: "Change in Profit Sharing Ratio Among the Existing Partners",
        3: "Admission of a Partner",
        4: "Retirement and Death of a Partner",
        5: "Dissolution of a Partnership Firm",
    },
    "leac2": {
        1: "Accounting for Share Capital",
        2: "Issue and Redemption of Debentures",
        3: "Financial Statements of a Company",
        4: "Analysis of Financial Statements",
        5: "Accounting Ratios",
        6: "Cash Flow Statement",
    },
    "lehe1": {
        1: "Bricks, Beads and Bones",
        2: "Kings, Farmers and Towns",
        3: "Kinship, Caste and Class",
        4: "Thinkers, Beliefs and Buildings",
        5: "Through the Eyes of Travellers",
        6: "Bhakti-Sufi Traditions",
        7: "An Imperial Capital: Vijayanagara",
    },
    "lehe2": {
        1: "Peasants, Zamindars and the State",
        2: "Colonialism and the Countryside",
        3: "Rebels and the Raj",
        4: "Colonial Cities",
        5: "Mahatma Gandhi and the Nationalist Movement",
        6: "Partition: Understanding and Interpreting",
        7: "The Making of the Constitution",
    },
    "leps1": {
        1: "The Cold War Era",
        2: "The End of Bipolarity",
        3: "US Hegemony in World Politics",
        4: "Alternative Centres of Power",
        5: "Contemporary South Asia",
        6: "International Organisations",
        7: "Security in the Contemporary World",
    },
    "leps2": {
        1: "Challenges of Nation-Building",
        2: "Era of One-Party Dominance",
        3: "Politics of Planned Development",
        4: "India's External Relations",
        5: "Challenges to and Restoration of the Congress System",
        6: "The Crisis of Democratic Order",
        7: "Rise of Popular Movements",
        8: "Regional Aspirations",
    },
    "legy1": {
        1: "Human Geography: Nature and Scope",
        2: "The World Population: Distribution, Density and Growth",
        3: "Population Composition",
        4: "Human Development",
        5: "Primary Activities",
        6: "Secondary Activities",
        7: "Tertiary and Quaternary Activities",
        8: "Transport and Communication",
        9: "International Trade",
        10: "Human Settlements",
    },
    "legz1": {
        1: "Population: Distribution, Density, Growth and Composition",
        2: "Migration: Types, Causes and Consequences",
        3: "Human Development",
        4: "Human Settlements",
        5: "Land Resources and Agriculture",
        6: "Water Resources",
        7: "Mineral and Energy Resources",
        8: "Manufacturing Industries",
        9: "Planning and Sustainable Development in Indian Context",
        10: "Transport and Communication",
        11: "International Trade",
        12: "Geographical Perspective on Selected Issues and Problems",
    },
    "les01": {
        1: "Indian Society: A Profile",
        2: "Demographic Structure of the Indian Society",
        3: "Social Institutions: Continuity and Change",
        4: "Market as a Social Institution",
        5: "Patterns of Social Inequality and Exclusion",
        6: "The Challenges of Cultural Diversity",
        7: "Suggestions for Project Work",
    },
    "les02": {
        1: "Structural Change",
        2: "Cultural Change",
        3: "The Story of Indian Democracy",
        4: "Change and Development in Rural Society",
        5: "Change and Development in Industrial Society",
        6: "Globalisation and Social Change",
        7: "Mass Media and Communications",
        8: "Social Movements",
    },
}


# ── TOC Extraction ────────────────────────────────────────────────────────────

def download_pdf_bytes(url: str) -> bytes | None:
    """Download a PDF from URL, return bytes or None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30, verify=False)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content
    except Exception as e:
        print(f"    [warn] Could not download {url}: {e}")
    return None


def extract_toc_from_ps_pdf(book_code: str) -> dict[int, str]:
    """
    Download {book_code}ps.pdf from NCERT and parse the Table of Contents.
    Returns dict: {chapter_number_int: "Chapter Name"}

    NCERT books use TWO different TOC formats:

    FORMAT A (Maths, Economics, Biology, etc.):
        "1. Sets 1"
        "2. Relations and Functions 24"

    FORMAT B (Physics, Chemistry, History, etc.):
        "C H A P T E R 1"
        "UNITS AND MEASUREMENTS"
        (chapter name is ALL CAPS on the line after the chapter header)
    """
    ps_url = f"{NCERT_BASE}/{book_code}ps.pdf"
    pdf_bytes = download_pdf_bytes(ps_url)
    if not pdf_bytes:
        return {}

    chapters: dict[int, str] = {}

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            all_pages = [page.extract_text() or "" for page in pdf.pages]

            # Find the CONTENTS page — scan all pages that have "CHAPTER" keyword
            # (some ps.pdfs have garbled "CONTENTS" headers due to PDF encoding)
            contents_pages = []
            for i, text in enumerate(all_pages):
                if (re.search(r'\bCONTENTS\b|\bContents\b', text) or
                        re.search(r'\bCHAPTER\s+\d', text, re.IGNORECASE)):
                    contents_pages.append(i)

            # Parse all identified content pages (TOC may span multiple pages)
            pages_to_parse = contents_pages if contents_pages else range(len(all_pages))
            for i in pages_to_parse:
                text = all_pages[i]
                # Also include the next page (TOC often continues)
                if i + 1 < len(all_pages):
                    text = text + "\n" + all_pages[i + 1]
                result = _parse_toc_format_a(text)
                if result:
                    chapters.update(result)
                result = _parse_toc_format_b(text)
                if result:
                    chapters.update(result)

    except Exception as e:
        print(f"    [warn] Could not parse {book_code}ps.pdf TOC: {e}")

    return chapters


def _parse_toc_format_a(text: str) -> dict[int, str]:
    """
    FORMAT A: Maths/Economics/Biology style
      "1. Sets 1"
      "2. Relations and Functions 24"
    Only matches lines where the chapter name is SHORT (< 80 chars) —
    this prevents matching activity paragraphs that start with a number.
    """
    chapters: dict[int, str] = {}
    line_re = re.compile(
        r'^(\d{1,2})\.\s+'                              # chapter number
        r'([A-Za-z\u0900-\u097F][^.\n]{3,60}?)'         # title: 4-60 chars, no dots
        r'\s+(\d{1,3})\s*$',                             # page number
        re.MULTILINE,
    )
    skip = {'foreword', 'preface', 'appendix', 'answers', 'contents',
            'index', 'bibliography', 'glossary', 'acknowledgements'}

    for m in line_re.finditer(text):
        ch_num = int(m.group(1))
        ch_name = re.sub(r'\s+', ' ', m.group(2)).strip()
        if ch_name.lower() in skip:
            continue
        if len(ch_name) <= 3:
            continue
        # Reject if it looks like a sub-section (1.1, 2.3 etc.)
        if re.match(r'^\d+\.\d', m.group(0)):
            continue
        if ch_num not in chapters:
            chapters[ch_num] = ch_name

    return chapters


def _parse_toc_format_b(text: str) -> dict[int, str]:
    """
    FORMAT B: Physics/Chemistry/History style — "CHAPTER N" followed by title.

    Handles all three NCERT sub-variants:
      B1 (keph1 style):  "C H A P T E R 1\nUNITS AND MEASUREMENTS\n"   (ALL CAPS title)
      B2 (keph2 style):  "CHAPTER 1\nUnits and measUrements 1\n"       (mixed case + page)
      B3 (Grade 12):     "Chapter One\nELECTRIC CHARGES AND FIELDS\n"  (word number)
    """
    chapters: dict[int, str] = {}

    word_to_num = {
        'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
        'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10,
        'ELEVEN': 11, 'TWELVE': 12, 'THIRTEEN': 13, 'FOURTEEN': 14,
        'FIFTEEN': 15, 'SIXTEEN': 16, 'SEVENTEEN': 17, 'EIGHTEEN': 18,
        'NINETEEN': 19, 'TWENTY': 20,
    }

    # Master pattern: CHAPTER (spaced or normal) + number/word + newline + title line
    # NOTE: use [ \t]* (not \s*) before \n — \s would eat the newline itself
    chapter_header_re = re.compile(
        r'(?:C\s*H\s*A\s*P\s*T\s*E\s*R|CHAPTER|Chapter)[ \t]+'
        r'(\d{1,2}|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|'
        r'ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|'
        r'EIGHTEEN|NINETEEN|TWENTY)[ \t]*\n'
        r'([A-Za-z][^\n]{3,80})',   # title: mixed case ok, 4-80 chars
        re.MULTILINE,
    )

    for m in chapter_header_re.finditer(text):
        num_str = m.group(1).strip()
        raw_name = m.group(2).strip()

        # Remove trailing page number if present: "Motion in a Plane 37"
        raw_name = re.sub(r'\s+\d{1,3}\s*$', '', raw_name).strip()
        # Remove trailing dots/extra whitespace
        raw_name = re.sub(r'\s+', ' ', raw_name).rstrip('.').strip()

        if num_str.isdigit():
            ch_num = int(num_str)
        else:
            ch_num = word_to_num.get(num_str.upper(), 0)
            if ch_num == 0:
                continue

        if len(raw_name) < 3:
            continue

        # Normalise capitalisation — NCERT ps.pdfs have inconsistent casing:
        # some are ALL CAPS, some are proper Title Case, some have garbled
        # mixed case like "Units and measUrements" or "laws oF motion".
        # Strategy: always apply title-case to get clean names.
        ch_name = raw_name.title()

        # Fix over-capitalised joining/preposition words (side-effect of .title())
        for word, fixed in [(' And ', ' and '), (' Of ', ' of '), (' The ', ' the '),
                             (' In ', ' in '), (' A ', ' a '), (' An ', ' an '),
                             (' For ', ' for '), (' With ', ' with '),
                             (' To ', ' to '), (' By ', ' by '), (' On ', ' on '),
                             (' At ', ' at '), (' As ', ' as '), (' Or ', ' or ')]:
            ch_name = ch_name.replace(word, fixed)

        # Fix specific NCERT patterns that title() handles wrong:
        # "S-Block" → keep, "D-Block" → keep
        # Roman numerals: "Ii" → "II", "Iii" → "III" etc.
        ch_name = re.sub(r'\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|Xi|Xii)\b',
                         lambda m: m.group().upper(), ch_name)

        # Always capitalise first character
        if ch_name:
            ch_name = ch_name[0].upper() + ch_name[1:]

        if ch_num not in chapters:
            chapters[ch_num] = ch_name

    return chapters


# ── Text extraction & chunking ─────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract and clean all text from a chapter PDF."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Remove common NCERT headers/footers
                text = re.sub(r'\bReprint\s+\d{4}-\d{2,4}\b', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\bNCERT\b.*?\n', '', text)
                text = re.sub(r'\bPage\s*\|\s*\d+\b', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\n{3,}', '\n\n', text)
                pages.append(text.strip())
        return '\n\n'.join(p for p in pages if p)
    except Exception as e:
        print(f"    [error] Could not extract {pdf_path.name}: {e}")
        return ""


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, current_len = [], [], 0

    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > size and current:
            chunks.append(' '.join(current))
            tail = ' '.join(current)
            current = [tail[-overlap:]] if overlap else []
            current_len = len(current[0]) if current else 0
        current.append(sentence)
        current_len += s_len

    if current:
        chunks.append(' '.join(current))

    return [c.strip() for c in chunks if len(c.strip()) > 30]


# ── Supabase helpers ───────────────────────────────────────────────────────────

def get_or_create_rag_document(grade: str, subject: str, chapter: str) -> str:
    """Return existing doc_id or create a new rag_documents record."""
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

    result = supabase.table("rag_documents").insert({
        "grade": grade,
        "board": BOARD,
        "subject": subject,
        "chapter": chapter,
        "title": f"{chapter} — {grade} {subject}",
        "source_type": "pdf",
        "uploaded_by": UPLOADED_BY,
    }).execute()
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


def doc_has_chunks(grade: str, subject: str, chapter: str) -> bool:
    """Return True if rag_chunks already exist for this chapter."""
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


# ── TOC cache (downloaded once per book) ──────────────────────────────────────

_toc_cache: dict[str, dict[int, str]] = {}


def get_toc(book_code: str) -> dict[int, str]:
    """Return cached TOC for book_code, downloading if needed."""
    if book_code not in _toc_cache:
        print(f"  → Downloading TOC for {book_code}ps.pdf ...")
        toc = extract_toc_from_ps_pdf(book_code)
        if toc:
            print(f"    {len(toc)} chapter names extracted")
            for ch, name in sorted(toc.items())[:5]:
                print(f"    Ch {ch}: {name}")
            if len(toc) > 5:
                print(f"    ... and {len(toc)-5} more")
        else:
            print(f"    [warn] No TOC found — will use fallback naming")
        _toc_cache[book_code] = toc
    return _toc_cache[book_code]


def _extract_title_from_chapter_pdf(pdf_path: Path, chapter_num: int) -> str | None:
    """
    Extract chapter name from the chapter PDF's first 1-2 pages.
    Used as fallback when ps.pdf TOC extraction fails.

    Handles:
    - Physics: "C E\nHAPTER IGHT\nMECHANICAL PROPERTIES OF SOLIDS"
    - Chemistry: "UNIT 1\nSOME BASIC CONCEPTS OF CHEMISTRY"
    - Biology sidebar: "Chapter 1\nThe Living World"
    - Mathematics: "1\nChapter\nSETS"
    """
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = ""
            for page in pdf.pages[:3]:
                text += (page.extract_text() or "") + "\n"
    except Exception:
        return None

    # Pattern 1: "CHAPTER {WORD}" followed by chapter title (Physics style)
    # Matches: "C E\nHAPTER IGHT\nMECHANICAL PROPERTIES OF SOLIDS"
    # or: "Chapter Eight\nMECHANICAL PROPERTIES OF SOLIDS"
    m = re.search(
        r'(?:C\s*H\s*A\s*P\s*T\s*E\s*R|CHAPTER|Chapter)[ \t]*\S*[ \t]*\n'
        r'([A-Z][A-Z\s,\':&\-–/()\d.]{5,60})\n',
        text, re.MULTILINE
    )
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if len(raw) > 4:
            return _normalise_title(raw)

    # Pattern 2: "UNIT N\nTITLE" (Chemistry style)
    m = re.search(
        r'^UNIT\s+\d+[ \t]*\n([A-Z][A-Z\s,\':&\-–/()\d.]{5,70})\n',
        text, re.MULTILINE
    )
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if len(raw) > 4:
            return _normalise_title(raw)

    # Pattern 3: Biology sidebar "Chapter N\nThe Living World"
    m = re.search(
        rf'Chapter\s+{chapter_num}[ \t]*\n([A-Z][a-zA-Z\s,\':&\-–/()\d.]+)\n',
        text, re.MULTILINE
    )
    if m:
        raw = re.sub(r'\s+', ' ', m.group(1)).strip()
        if 3 < len(raw) < 80:
            return _normalise_title(raw)

    return None


def _normalise_title(raw: str) -> str:
    """Apply consistent title-casing to a chapter name string."""
    ch_name = raw.title()
    for word, fixed in [(' And ', ' and '), (' Of ', ' of '), (' The ', ' the '),
                         (' In ', ' in '), (' A ', ' a '), (' An ', ' an '),
                         (' For ', ' for '), (' With ', ' with '),
                         (' To ', ' to '), (' By ', ' by '), (' On ', ' on '),
                         (' At ', ' at '), (' As ', ' as '), (' Or ', ' or ')]:
        ch_name = ch_name.replace(word, fixed)
    ch_name = re.sub(r'\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|Xi|Xii)\b',
                     lambda m: m.group().upper(), ch_name)
    if ch_name:
        ch_name = ch_name[0].upper() + ch_name[1:]
    return ch_name


def get_chapter_name(book_code: str, chapter_num: int, pdf_path: Path | None = None) -> str:
    """
    Get chapter name using this priority:
    1. CHAPTER_OVERRIDES hardcoded dict (highest trust — manually verified)
    2. TOC from ps.pdf (auto-extracted from NCERT)
    3. First-page extraction from the chapter PDF itself
    4. Fallback: '{Subject} Chapter {N}' (never fails)
    """
    # Priority 1: hardcoded override (takes precedence over ps.pdf for books
    # where the TOC is wrong, missing, or garbled)
    if book_code in CHAPTER_OVERRIDES:
        override = CHAPTER_OVERRIDES[book_code].get(chapter_num)
        if override:
            return override

    # Priority 2: TOC from ps.pdf
    toc = get_toc(book_code)
    if chapter_num in toc:
        return toc[chapter_num]

    # Priority 3: extract from the chapter PDF's first page
    if pdf_path and pdf_path.exists():
        extracted = _extract_title_from_chapter_pdf(pdf_path, chapter_num)
        if extracted:
            return extracted

    subject_folder = BOOK_TO_FOLDER.get(book_code, "Unknown")
    subject = FOLDER_TO_SUBJECT.get(subject_folder, subject_folder)
    return f"{subject} — Chapter {chapter_num}"


# ── Main processing ───────────────────────────────────────────────────────────

def parse_book_code_and_chapter(pdf_path: Path) -> tuple[str, int] | None:
    """
    Extract book_code and chapter number from filename.
    e.g. "keph101.pdf" → ("keph1", 1)
         "kemh214.pdf" → ("kemh2", 14)
         "lebo108.pdf" → ("lebo1", 8)
    """
    stem = pdf_path.stem  # e.g. "keph101"
    # Match: 4-5 char book code + 2-digit chapter number
    m = re.match(r'^([a-z]{3,5}\d?)(\d{2})$', stem)
    if not m:
        return None
    book_code = m.group(1)
    chapter_num = int(m.group(2))
    return book_code, chapter_num


def process_book(
    grade_dir: Path,
    book_code: str,
    grade: str,
    subject: str,
    dry_run: bool,
    force: bool,
) -> int:
    """Process all chapter PDFs for one book code. Returns chapters uploaded."""
    folder_name = BOOK_TO_FOLDER.get(book_code, "")
    if not folder_name:
        return 0

    subject_dir = grade_dir / folder_name
    if not subject_dir.exists():
        return 0

    # Find all PDFs for this book code
    pdfs = sorted(subject_dir.glob(f"{book_code}*.pdf"))
    if not pdfs:
        return 0

    print(f"\n  📖 {book_code} ({subject}) — {len(pdfs)} chapters")

    # Pre-fetch TOC (downloads ps.pdf once for the whole book)
    get_toc(book_code)

    uploaded = 0
    for pdf_path in pdfs:
        parsed = parse_book_code_and_chapter(pdf_path)
        if not parsed:
            print(f"    [skip] Unrecognised filename: {pdf_path.name}")
            continue

        _, chapter_num = parsed
        chapter_name = get_chapter_name(book_code, chapter_num, pdf_path)

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

        doc_id = get_or_create_rag_document(grade, subject, chapter_name)
        stored = upload_chunks_for_doc(doc_id, chunks)
        print(f"      ✅ stored {stored}/{len(chunks)} chunks")
        uploaded += 1

    return uploaded


def run_upload(
    grades: list[int],
    subject_filter: list[str] | None,
    dry_run: bool,
    force: bool,
) -> None:
    total = 0
    summary: dict[str, int] = {}

    grade_codes = {
        11: ("Grade_11", "Grade 11", GRADE_11_BOOK_CODES),
        12: ("Grade_12", "Grade 12", GRADE_12_BOOK_CODES),
    }

    for grade_int in grades:
        folder_name, grade_label, book_codes = grade_codes[grade_int]
        grade_dir = PDF_ROOT / folder_name

        if not grade_dir.exists():
            print(f"\n[warn] {grade_dir} not found — run download_ncert_grade11_12.py first")
            continue

        print(f"\n{'='*70}")
        print(f"  {grade_label} → {grade_dir}")
        print(f"{'='*70}")

        for book_code in book_codes:
            folder_name_sub = BOOK_TO_FOLDER.get(book_code, "")
            subject = FOLDER_TO_SUBJECT.get(folder_name_sub, folder_name_sub)

            # Apply subject filter
            if subject_filter:
                if not any(sf.lower() in subject.lower() for sf in subject_filter):
                    continue

            n = process_book(
                grade_dir=grade_dir,
                book_code=book_code,
                grade=grade_label,
                subject=subject,
                dry_run=dry_run,
                force=force,
            )
            total += n
            summary[f"{grade_label} / {subject} / {book_code}"] = n

    print(f"\n\n{'='*70}")
    print(f"  UPLOAD COMPLETE — {total} chapters uploaded to RAG")
    print(f"{'='*70}")
    for key, n in summary.items():
        if n:
            print(f"  {key}: {n} chapters")
    print()
    print("  Next step:")
    print("    Admin panel → Cache & Question Bank → Generate Lessons for Grade 11 & 12")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload NCERT Grade 11 & 12 PDFs to RAG (Supabase)"
    )
    parser.add_argument("--grade", type=int, choices=[11, 12])
    parser.add_argument("--subjects", nargs="+", metavar="SUBJECT")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Re-upload even if chapter already exists in RAG")
    args = parser.parse_args()

    grades = [args.grade] if args.grade else [11, 12]
    print()
    print("  NCERT Grade 11 & 12 RAG Upload")
    print(f"  PDF root: {PDF_ROOT}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    if args.subjects:
        print(f"  Subjects: {args.subjects}")
    print()

    run_upload(
        grades=grades,
        subject_filter=args.subjects,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
