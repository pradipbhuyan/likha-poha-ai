#!/usr/bin/env python3
"""
Seed syllabus_chapter_overrides for Grade 11 & 12 from CHAPTER_OVERRIDES.
================================================================
When the Grade 11/12 Supabase is unavailable (key rotation, downtime),
this script saves the chapter names into the PRIMARY Supabase's
syllabus_chapter_overrides table so the student dropdown always shows
the correct chapter names regardless of secondary DB status.

Run once after the Grade 11/12 content was first uploaded, or after
any change to the Grade 11/12 chapter list.

Usage:
    cd backend
    python3 scripts/seed_grade1112_syllabus_overrides.py --dry-run
    python3 scripts/seed_grade1112_syllabus_overrides.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client
from app.services.ssl_service import enable_system_truststore

enable_system_truststore()

# ── Chapter data from upload_ncert_grade11_12_rag.py ──────────────────────────
# Copied here so this script has no import dependency on the upload script.
# Maps: book_code → {chapter_num: chapter_name}

BOOK_TO_GRADE = {
    "keph1": "Grade 11", "keph2": "Grade 11",
    "kech1": "Grade 11", "kech2": "Grade 11",
    "kemh1": "Grade 11", "kemh2": "Grade 11",
    "kebo1": "Grade 11",
    "keeh1": "Grade 11", "kesp1": "Grade 11",
    "khah1": "Grade 11", "khvt1": "Grade 11",
    "keec1": "Grade 11", "kest1": "Grade 11",
    "kebs1": "Grade 11", "kebs2": "Grade 11",
    "keac1": "Grade 11", "keac2": "Grade 11",
    "kehe1": "Grade 11", "kehe2": "Grade 11",
    "kegy1": "Grade 11", "kegy2": "Grade 11",
    "keps1": "Grade 11", "keps2": "Grade 11",
    "leph1": "Grade 12", "leph2": "Grade 12",
    "lech1": "Grade 12", "lech2": "Grade 12",
    "lemh1": "Grade 12", "lemh2": "Grade 12",
    "lebo1": "Grade 12",
    "lefl1": "Grade 12", "levs1": "Grade 12",
    "lhah1": "Grade 12", "lhvt1": "Grade 12",
    "leec1": "Grade 12", "lema1": "Grade 12",
    "lebs1": "Grade 12", "lebs2": "Grade 12",
    "leac1": "Grade 12", "leac2": "Grade 12",
    "lehe1": "Grade 12", "lehe2": "Grade 12",
    "legy1": "Grade 12", "legz1": "Grade 12",
    "leps1": "Grade 12", "leps2": "Grade 12",
}

BOOK_TO_SUBJECT = {
    "keph1": "Physics",   "keph2": "Physics",
    "leph1": "Physics",   "leph2": "Physics",
    "kech1": "Chemistry", "kech2": "Chemistry",
    "lech1": "Chemistry", "lech2": "Chemistry",
    "kemh1": "Mathematics", "kemh2": "Mathematics",
    "lemh1": "Mathematics", "lemh2": "Mathematics",
    "kebo1": "Biology",   "lebo1": "Biology",
    "keeh1": "English",   "kesp1": "English",
    "lefl1": "English",   "levs1": "English",
    "khah1": "Hindi",     "khvt1": "Hindi",
    "lhah1": "Hindi",     "lhvt1": "Hindi",
    "keec1": "Economics", "kest1": "Economics",
    "leec1": "Economics", "lema1": "Economics",
    "kebs1": "Business Studies", "kebs2": "Business Studies",
    "lebs1": "Business Studies", "lebs2": "Business Studies",
    "keac1": "Accountancy", "keac2": "Accountancy",
    "leac1": "Accountancy", "leac2": "Accountancy",
    "kehe1": "History",  "kehe2": "History",
    "lehe1": "History",  "lehe2": "History",
    "kegy1": "Geography","kegy2": "Geography",
    "legy1": "Geography","legz1": "Geography",
    "keps1": "Political Science", "keps2": "Political Science",
    "leps1": "Political Science", "leps2": "Political Science",
}

# Chapter names by book code (from CHAPTER_OVERRIDES in upload script)
CHAPTER_OVERRIDES: dict[str, dict[int, str]] = {
    "keph2": {1:"Mechanical Properties of Solids",2:"Mechanical Properties of Fluids",3:"Thermal Properties of Matter",4:"Thermodynamics",5:"Kinetic Theory",6:"Oscillations",7:"Waves"},
    "kech1": {1:"Some Basic Concepts of Chemistry",2:"Structure of Atom",3:"Classification of Elements and Periodicity in Properties",4:"Chemical Bonding and Molecular Structure",5:"Thermodynamics",6:"Equilibrium"},
    "kech2": {1:"Redox Reactions",2:"Hydrogen",3:"The s-Block Elements",4:"The p-Block Elements",5:"Organic Chemistry — Some Basic Principles and Techniques",6:"Hydrocarbons",7:"Environmental Chemistry"},
    "kebo1": {1:"The Living World",2:"Biological Classification",3:"Plant Kingdom",4:"Animal Kingdom",5:"Morphology of Flowering Plants",6:"Anatomy of Flowering Plants",7:"Structural Organisation in Animals",8:"Cell: The Unit of Life",9:"Biomolecules",10:"Cell Cycle and Cell Division",11:"Photosynthesis in Higher Plants",12:"Respiration in Plants",13:"Plant Growth and Development",14:"Breathing and Exchange of Gases",15:"Body Fluids and Circulation",16:"Excretory Products and their Elimination",17:"Locomotion and Movement",18:"Neural Control and Coordination",19:"Chemical Coordination and Integration"},
    "keeh1": {1:"The Portrait of a Lady",2:"We're Not Afraid to Die — If We Can All Be Together",3:"Discovering Tut: The Saga Continues",4:"Landscape of the Soul",5:"The Ailing Planet: The Green Movement's Role",6:"The Browning Version",7:"The Adventure",8:"Silk Road"},
    "kesp1": {1:"The Summer of the Beautiful White Horse",2:"The Address",3:"Ranga's Marriage",4:"Albert Einstein at School",5:"Mother's Day",6:"The Ghat of the Only World",7:"Birth",8:"The Tale of Melon City"},
    "keec1": {1:"Indian Economy on the Eve of Independence",2:"Indian Economy 1950-1990",3:"Liberalisation, Privatisation and Globalisation: An Appraisal",4:"Poverty",5:"Human Capital Formation in India",6:"Rural Development",7:"Employment: Growth, Informalisation and Other Issues",8:"Infrastructure",9:"Environment and Sustainable Development",10:"Comparative Development Experiences of India and Its Neighbours"},
    "kest1": {1:"Introduction",2:"Collection of Data",3:"Organisation of Data",4:"Presentation of Data",5:"Measures of Central Tendency",6:"Measures of Dispersion",7:"Correlation",8:"Index Numbers",9:"Use of Statistical Tools"},
    "kebs1": {1:"Nature and Purpose of Business",2:"Forms of Business Organisation",3:"Private, Public and Global Enterprises",4:"Business Services",5:"Emerging Modes of Business",6:"Social Responsibility of Business and Business Ethics"},
    "kebs2": {1:"Sources of Business Finance",2:"Small Business",3:"Internal Trade",4:"International Business"},
    "keac1": {1:"Introduction to Accounting",2:"Theory Base of Accounting",3:"Recording of Transactions I",4:"Recording of Transactions II",5:"Bank Reconciliation Statement",6:"Trial Balance and Rectification of Errors",7:"Depreciation, Provisions and Reserves",8:"Bills of Exchange"},
    "keac2": {1:"Financial Statements I",2:"Financial Statements II",3:"Accounts from Incomplete Records",4:"Computers in Accounting",5:"Accounting Software: Tally"},
    "kehe1": {1:"From the Beginning of Time",2:"Writing and City Life",3:"An Empire Across Three Continents",4:"The Central Islamic Lands",5:"Nomadic Empires",6:"The Three Orders",7:"Changing Cultural Traditions"},
    "kehe2": {1:"Confrontation of Cultures",2:"The Industrial Revolution",3:"Displacing Indigenous Peoples",4:"Paths to Modernisation"},
    "kegy1": {1:"Geography as a Discipline",2:"The Origin and Evolution of the Earth",3:"Interior of the Earth",4:"Distribution of Oceans and Continents",5:"Minerals and Rocks",6:"Geomorphic Processes",7:"Landforms and their Evolution",8:"Composition and Structure of Atmosphere",9:"Solar Radiation, Heat Balance and Temperature",10:"Atmospheric Circulation and Weather Systems",11:"Water in the Atmosphere",12:"World Climate and Climate Change",13:"Water (Oceans)",14:"Movements of Ocean Water",15:"Life on the Earth",16:"Biodiversity and Conservation"},
    "kegy2": {1:"India — Location",2:"Structure and Physiography",3:"Drainage System",4:"Climate",5:"Natural Vegetation",6:"Soils",7:"Natural Hazards and Disasters"},
    "keps1": {1:"Political Theory: An Introduction",2:"Freedom",3:"Equality",4:"Social Justice",5:"Rights",6:"Citizenship",7:"Nationalism",8:"Secularism"},
    "keps2": {1:"Constitution: Why and How?",2:"Rights in the Indian Constitution",3:"Election and Representation",4:"Executive",5:"Legislature",6:"Judiciary",7:"Federalism",8:"Local Governments",9:"Constitution as a Living Document",10:"The Philosophy of the Constitution"},
    # Grade 12
    "leph2": {1:"Wave Optics",2:"Ray Optics and Optical Instruments",3:"Dual Nature of Radiation and Matter",4:"Atoms",5:"Nuclei",6:"Semiconductor Electronics: Materials, Devices and Simple Circuits"},
    "lech1": {1:"The Solid State",2:"Solutions",3:"Electrochemistry",4:"Chemical Kinetics",5:"Surface Chemistry",6:"General Principles and Processes of Isolation of Elements",7:"The p-Block Elements"},
    "lech2": {1:"The d and f Block Elements",2:"Coordination Compounds",3:"Haloalkanes and Haloarenes",4:"Alcohols, Phenols and Ethers",5:"Aldehydes, Ketones and Carboxylic Acids",6:"Amines",7:"Biomolecules",8:"Polymers",9:"Chemistry in Everyday Life"},
    "lebo1": {1:"Reproduction in Organisms",2:"Sexual Reproduction in Flowering Plants",3:"Human Reproduction",4:"Reproductive Health",5:"Principles of Inheritance and Variation",6:"Molecular Basis of Inheritance",7:"Evolution",8:"Human Health and Disease",9:"Strategies for Enhancement in Food Production",10:"Microbes in Human Welfare",11:"Biotechnology: Principles and Processes",12:"Biotechnology and its Applications",13:"Organisms and Populations",14:"Ecosystem",15:"Biodiversity and Conservation",16:"Environmental Issues"},
    "lefl1": {1:"The Last Lesson",2:"Lost Spring",3:"Deep Water",4:"The Rattrap",5:"Indigo",6:"Poets and Pancakes",7:"The Interview",8:"Going Places"},
    "levs1": {1:"The Third Level",2:"The Tiger King",3:"Journey to the End of the Earth",4:"The Enemy",5:"Should Wizard Hit Mommy?",6:"On the Face of It",7:"Evans Tries an O-Level",8:"Memories of Childhood"},
    "leec1": {1:"Introduction",2:"National Income Accounting",3:"Money and Banking",4:"Determination of Income and Employment",5:"Government Budget and the Economy",6:"Open Economy Macroeconomics"},
    "lema1": {1:"Introduction to Macro Economics",2:"National Income Accounting",3:"Money and Banking",4:"Income Determination",5:"Government Budget and the Economy",6:"Open Economy Macroeconomics"},
    "lebs1": {1:"Nature and Significance of Management",2:"Principles of Management",3:"Business Environment",4:"Planning",5:"Organising",6:"Staffing"},
    "lebs2": {1:"Directing",2:"Controlling",3:"Financial Management",4:"Financial Markets",5:"Marketing Management",6:"Consumer Protection",7:"Entrepreneurship Development"},
    "leac1": {1:"Accounting for Partnership: Basic Concepts",2:"Change in Profit Sharing Ratio Among the Existing Partners",3:"Admission of a Partner",4:"Retirement and Death of a Partner",5:"Dissolution of a Partnership Firm"},
    "leac2": {1:"Accounting for Share Capital",2:"Issue and Redemption of Debentures",3:"Financial Statements of a Company",4:"Analysis of Financial Statements",5:"Accounting Ratios",6:"Cash Flow Statement"},
    "lehe1": {1:"Bricks, Beads and Bones",2:"Kings, Farmers and Towns",3:"Kinship, Caste and Class",4:"Thinkers, Beliefs and Buildings",5:"Through the Eyes of Travellers",6:"Bhakti-Sufi Traditions",7:"An Imperial Capital: Vijayanagara"},
    "lehe2": {1:"Peasants, Zamindars and the State",2:"Colonialism and the Countryside",3:"Rebels and the Raj",4:"Colonial Cities",5:"Mahatma Gandhi and the Nationalist Movement",6:"Partition: Understanding and Interpreting",7:"The Making of the Constitution"},
    "legy1": {1:"Human Geography: Nature and Scope",2:"The World Population: Distribution, Density and Growth",3:"Population Composition",4:"Human Development",5:"Primary Activities",6:"Secondary Activities",7:"Tertiary and Quaternary Activities",8:"Transport and Communication",9:"International Trade",10:"Human Settlements"},
    "legz1": {1:"Population: Distribution, Density, Growth and Composition",2:"Migration: Types, Causes and Consequences",3:"Human Development",4:"Human Settlements",5:"Land Resources and Agriculture",6:"Water Resources",7:"Mineral and Energy Resources",8:"Manufacturing Industries",9:"Planning and Sustainable Development in Indian Context",10:"Transport and Communication",11:"International Trade",12:"Geographical Perspective on Selected Issues and Problems"},
    "leps1": {1:"The Cold War Era",2:"The End of Bipolarity",3:"US Hegemony in World Politics",4:"Alternative Centres of Power",5:"Contemporary South Asia",6:"International Organisations",7:"Security in the Contemporary World"},
    "leps2": {1:"Challenges of Nation-Building",2:"Era of One-Party Dominance",3:"Politics of Planned Development",4:"India's External Relations",5:"Challenges to and Restoration of the Congress System",6:"The Crisis of Democratic Order",7:"Rise of Popular Movements",8:"Regional Aspirations"},
    # Grade 11 Physics Part 1 — TOC extraction works for this book
    "keph1": {1:"Units and Measurements",2:"Motion in a Straight Line",3:"Motion in a Plane",4:"Laws of Motion",5:"Work, Energy and Power",6:"System of Particles and Rotational Motion",7:"Gravitation"},
    # Grade 11 Mathematics
    "kemh1": {1:"Sets",2:"Relations and Functions",3:"Trigonometric Functions",4:"Complex Numbers and Quadratic Equations",5:"Linear Inequalities",6:"Permutations and Combinations",7:"Binomial Theorem"},
    "kemh2": {1:"Sequences and Series",2:"Straight Lines",3:"Conic Sections",4:"Introduction to Three Dimensional Geometry",5:"Limits and Derivatives",6:"Statistics",7:"Probability"},
    # Grade 12 Physics Part 1
    "leph1": {1:"Electric Charges and Fields",2:"Electrostatic Potential and Capacitance",3:"Current Electricity",4:"Moving Charges and Magnetism",5:"Magnetism and Matter",6:"Electromagnetic Induction",7:"Alternating Current",8:"Electromagnetic Waves"},
    # Grade 12 Mathematics
    "lemh1": {1:"Relations and Functions",2:"Inverse Trigonometric Functions",3:"Matrices",4:"Determinants",5:"Continuity and Differentiability",6:"Application of Derivatives"},
    "lemh2": {1:"Integrals",2:"Application of Integrals",3:"Differential Equations",4:"Vector Algebra",5:"Three Dimensional Geometry",6:"Linear Programming",7:"Probability"},
    # Grade 11 Hindi
    "khah1": {1:"हम तौ एक एक करि जाना — कबीर",2:"मेरे तो गिरधर गोपाल — मीरा",3:"पथिक — रामनरेश त्रिपाठी",4:"वे आँखें — सुमित्रानंदन पंत",5:"घर की याद — भवानीप्रसाद मिश्र",6:"नमक का दारोगा",7:"मियाँ नसीरुद्दीन",8:"अपू के साथ ढाई साल"},
    "khvt1": {1:"भारतीय गायिकाओं में बेजोड़: लता मंगेशकर",2:"राजस्थान की रजत बूँदें",3:"आलो-आँधारि"},
    "lhah1": {1:"आत्म-परिचय / एक गीत — हरिवंशराय बच्चन",2:"पतंग — आलोक धन्वा",3:"कविता के बहाने / बात सीधी थी पर — कुँवर नारायण",4:"भक्तिन",5:"बाजार दर्शन",6:"काले मेघा पानी दे"},
    "lhvt1": {1:"सिल्वर वेडिंग",2:"जूझ",3:"अतीत में दबे पाँव",4:"डायरी के पन्ने"},
}

# ── Build chapter lists per grade/subject ─────────────────────────────────────

def build_chapter_lists() -> dict[tuple[str,str], list[str]]:
    """Aggregate chapters from all books, grouped by (grade, subject)."""
    # Books in canonical order per subject
    BOOK_ORDER = [
        "keph1","keph2","kech1","kech2","kemh1","kemh2","kebo1",
        "keeh1","kesp1","khah1","khvt1","keec1","kest1","kebs1","kebs2",
        "keac1","keac2","kehe1","kehe2","kegy1","kegy2","keps1","keps2",
        "leph1","leph2","lech1","lech2","lemh1","lemh2","lebo1",
        "lefl1","levs1","lhah1","lhvt1","leec1","lema1","lebs1","lebs2",
        "leac1","leac2","lehe1","lehe2","legy1","legz1","leps1","leps2",
    ]
    result: dict[tuple[str,str], list[str]] = {}
    seen: dict[tuple[str,str], set[str]] = {}

    for book_code in BOOK_ORDER:
        grade = BOOK_TO_GRADE.get(book_code)
        subject = BOOK_TO_SUBJECT.get(book_code)
        chapters_map = CHAPTER_OVERRIDES.get(book_code, {})

        if not grade or not subject or not chapters_map:
            continue

        key = (grade, subject)
        result.setdefault(key, [])
        seen.setdefault(key, set())

        for ch_num in sorted(chapters_map.keys()):
            ch_name = chapters_map[ch_num]
            norm = ch_name.strip().lower()
            if norm not in seen[key]:
                result[key].append(ch_name)
                seen[key].add(norm)

    return result


def run(dry_run: bool) -> None:
    chapter_lists = build_chapter_lists()
    ADMIN_USER_ID = "4f443815-66b3-49a3-a746-04cd34eb7abf"

    print()
    print("  Seeding syllabus_chapter_overrides for Grade 11 & 12")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}")
    print(f"  Subjects to seed: {len(chapter_lists)}")
    print()

    saved = 0
    for (grade, subject), chapters in sorted(chapter_lists.items()):
        print(f"  {grade} — {subject}: {len(chapters)} chapters")
        for ch in chapters[:3]:
            print(f"    • {ch}")
        if len(chapters) > 3:
            print(f"    ... and {len(chapters)-3} more")

        if dry_run:
            continue

        try:
            admin_client.table("syllabus_chapter_overrides").upsert({
                "grade": grade,
                "mode": "CBSE",
                "subject": subject,
                "chapters": chapters,
                "updated_by": ADMIN_USER_ID,
            }, on_conflict="grade,mode,subject").execute()
            print(f"    ✅ Saved to syllabus_chapter_overrides")
            saved += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")

    print()
    if dry_run:
        print(f"  DRY RUN complete — {len(chapter_lists)} subjects would be saved")
    else:
        print(f"  Done — {saved}/{len(chapter_lists)} subjects saved to primary Supabase")
    print()
    print("  Grade 11/12 chapters will now appear in the Syllabus Review page")
    print("  even when the Grade 11/12 Supabase credentials are being rotated.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Grade 11/12 chapter overrides in primary Supabase"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be saved without writing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
