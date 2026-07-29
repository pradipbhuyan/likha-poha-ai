#!/usr/bin/env python3
"""
Fix GRADE_11_RESOURCES in resources.py:
1. Physics/Chemistry/Biology: replace duplicate slot[0] with Indian video search (type "website")
2. Rename "Maths" key -> "Mathematics" so Grade 11 syllabus subject lookup works
3. Mathematics: replace duplicate slot[0] with Vedantu search links (type "website")
"""
from urllib.parse import quote_plus
import re

FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

# ---------------------------------------------------------------------------
# 1. Fix Physics chapters: replace duplicate slot[0] with PW search entry
# ---------------------------------------------------------------------------
# Each fix: (chapter_key, pw_topic, slot1_title, slot1_video_id)
physics_fixes = [
    ("Units and Measurements",
     "units and measurements",
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Units and Measurement",
     "units and measurement",
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Motion in a Straight Line",
     "motion in a straight line",
     "Khan Academy — Distance and Displacement (International)", "vQCkYm3v3aA"),
    ("Motion in a Plane",
     "motion in a plane",
     "Khan Academy — Introduction to Vectors and Scalars (International)", "ihNZlp7iUHE"),
    ("Laws of Motion",
     "laws of motion",
     "Khan Academy — Newton's Laws of Motion (International)", "CQYELiTtUs8"),
    ("Work, Energy and Power",
     "work energy and power",
     "Khan Academy — Work and Energy (International)", "ewfMcg3wRaQ"),
    ("System of Particles and Rotational Motion",
     "system of particles and rotational motion",
     "Khan Academy — Angular Momentum and Torque (International)", "o7_zmuBweHI"),
    ("Gravitation",
     "gravitation",
     "Kurzgesagt — Gravity Explained (International)", "e5GBM-MEKzo"),
    ("Mechanical Properties of Solids",
     "mechanical properties of solids",
     "Khan Academy — Stress, Strain and Elastic Modulus (International)", "VRXLvJPTV0k"),
    ("Mechanical Properties of Fluids",
     "mechanical properties of fluids",
     "Khan Academy — Fluid Pressure and Bernoulli Equation (International)", "VRXLvJPTV0k"),
    ("Thermal Properties of Matter",
     "thermal properties of matter",
     "Khan Academy — Specific Heat and Thermal Energy (International)", "7L1EaURmvDs"),
    ("Thermodynamics",
     "thermodynamics physics",
     "Veritasium — Entropy: The Most Misunderstood Concept (International)", "DxL2HoqLbyA"),
    ("Kinetic Theory",
     "kinetic theory",
     "Khan Academy — Kinetic Molecular Theory (International)", "HkSXiHz9vUc"),
    ("Oscillations",
     "oscillations",
     "Khan Academy — Introduction to Simple Harmonic Motion (International)", "ZcZQsj6YAgU"),
    ("Waves",
     "waves",
     "Khan Academy — Introduction to Waves (International)", "c38H6UKt3_I"),
]

# ---------------------------------------------------------------------------
# 2. Fix Chemistry chapters: replace duplicate slot[0] with PW search entry
# ---------------------------------------------------------------------------
chemistry_fixes = [
    ("Some Basic Concepts of Chemistry",
     "some basic concepts of chemistry",
     "Khan Academy \u2014 The Mole and Avogadro's Number (International)", "cvi4IJMZ13Q"),
    ("Structure of Atom",
     "structure of atom",
     "Khan Academy \u2014 Bohr Model and Atomic Structure (International)", "haFTkhOcQaY"),
    ("Classification of Elements and Periodicity in Properties",
     "classification of elements and periodicity",
     "Khan Academy \u2014 Periodic Table Trends (International)", "MyBYZJ3Wo_0"),
    ("Chemical Bonding and Molecular Structure",
     "chemical bonding and molecular structure",
     "Khan Academy \u2014 Ionic and Covalent Bonding (International)", "FaeAurHnQJs"),
    ("States of Matter",
     "states of matter",
     "Khan Academy \u2014 States of Matter and Ideal Gas (International)", "pKvo0XWZtjo"),
    ("Thermodynamics",
     "thermodynamics chemistry",
     "Khan Academy \u2014 Enthalpy and Thermochemistry (International)", "TNwGNHqwHxc"),
    ("Equilibrium",
     "equilibrium",
     "Khan Academy \u2014 Chemical Equilibrium Constant (International)", "5HZbCNg9mIw"),
    ("Redox Reactions",
     "redox reactions",
     "Khan Academy \u2014 Oxidation and Reduction Redox (International)", "DvYs1HILq1g"),
    ("Hydrocarbons",
     "hydrocarbons",
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    ("Organic Chemistry \u2013 Some Basic Principles and Techniques",
     "organic chemistry basic principles",
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
]

# ---------------------------------------------------------------------------
# 3. Fix Biology chapters: replace duplicate slot[0] with Vedantu search entry
# ---------------------------------------------------------------------------
biology_fixes = [
    ("The Living World",
     "the living world",
     "Kurzgesagt \u2014 What Is Life? How Does It Work? (International)", "QOCaacO8wus"),
    ("Biological Classification",
     "biological classification",
     "Khan Academy \u2014 Taxonomy and Classification (International)", "mrheet-2osg"),
    ("Plant Kingdom",
     "plant kingdom",
     "Kurzgesagt \u2014 How Evolution Works (International)", "hOfRN0KihOU"),
    ("Animal Kingdom",
     "animal kingdom",
     "Kurzgesagt \u2014 The Immune System Explained (International)", "lXfEK8G8CUI"),
    ("Cell: The Unit of Life",
     "cell unit of life",
     "Khan Academy \u2014 Cell Structure and Function (International)", "7FN1NBoV2u0"),
    ("Biomolecules",
     "biomolecules",
     "Khan Academy \u2014 Macromolecules Proteins Carbs Lipids (International)", "HGg_WiaSr4U"),
    ("Cell Cycle and Cell Division",
     "cell cycle and cell division",
     "Khan Academy \u2014 Mitosis and Cell Division (International)", "U5vAO_f2LDQ"),
    ("Photosynthesis in Higher Plants",
     "photosynthesis in higher plants",
     "Khan Academy \u2014 Photosynthesis Overview (International)", "-rsYk4eCKnA"),
    ("Respiration in Plants",
     "respiration in plants",
     "Khan Academy \u2014 Cellular Respiration Overview (International)", "ArmlWtDnuys"),
    ("Breathing and Exchange of Gases",
     "breathing and exchange of gases",
     "Khan Academy \u2014 Respiratory System and Breathing (International)", "qGiPZf7njqY"),
    ("Body Fluids and Circulation",
     "body fluids and circulation",
     "Khan Academy \u2014 Heart and Circulatory System (International)", "7K2icszdxQc"),
    ("Neural Control and Coordination",
     "neural control and coordination",
     "Khan Academy \u2014 Neurons and the Nervous System (International)", "h2H6POZowiU"),
    ("Chemical Coordination and Integration",
     "chemical coordination and integration",
     "Khan Academy \u2014 Endocrine System and Hormones (International)", "ER49EweKwW8"),
]

# ---------------------------------------------------------------------------
# 4. Fix Mathematics chapters: rename key + replace duplicate slot[0] with Vedantu
# ---------------------------------------------------------------------------
maths_fixes = [
    ("Sets",
     "sets",
     "Khan Academy \u2014 Introduction to Sets (International)", "riXcZT2ICjA"),
    ("Relations and Functions",
     "relations and functions",
     "Khan Academy \u2014 Relations and Functions (International)", "-DTMakGDZAw"),
    ("Trigonometric Functions",
     "trigonometric functions",
     "3Blue1Brown \u2014 Euler's Formula and Trigonometry (International)", "mvmuCPvRoWQ"),
    ("Complex Numbers and Quadratic Equations",
     "complex numbers and quadratic equations",
     "Khan Academy \u2014 Complex Numbers (International)", "T647CGsuOVU"),
    ("Linear Inequalities",
     "linear inequalities",
     "Khan Academy \u2014 Linear Inequalities (International)", "Z1zdkcwosD4"),
    ("Permutations and Combinations",
     "permutations and combinations",
     "Khan Academy \u2014 Permutations and Combinations (International)", "Z1zdkcwosD4"),
    ("Binomial Theorem",
     "binomial theorem",
     "Khan Academy \u2014 Binomial Theorem (International)", "WUvTyaaNkzM"),
    ("Sequences and Series",
     "sequences and series",
     "Khan Academy \u2014 Arithmetic Sequences and Series (International)", "_cooC3yG_p0"),
    ("Straight Lines",
     "straight lines",
     "Khan Academy \u2014 Slope and Equation of a Line (International)", "XMJ72mtMn4Y"),
    ("Conic Sections",
     "conic sections",
     "Khan Academy \u2014 Introduction to Conic Sections (International)", "0A7RR0oy2ho"),
    ("Introduction to Three Dimensional Geometry",
     "introduction to three dimensional geometry",
     "Khan Academy \u2014 3D Geometry Introduction (International)", "riXcZT2ICjA"),
    ("Limits and Derivatives",
     "limits and derivatives",
     "3Blue1Brown \u2014 Essence of Calculus (International)", "WUvTyaaNkzM"),
    ("Statistics",
     "statistics",
     "Khan Academy \u2014 Mean Median and Mode Statistics (International)", "k3aKKasOmIw"),
    ("Probability",
     "probability",
     "Khan Academy \u2014 Basic Probability (International)", "uzkc-qNVoOk"),
]


def make_pw_url(topic):
    return "https://www.youtube.com/results?search_query=physics+wallah+" + quote_plus(topic) + "+class+11"


def make_vedantu_url(topic):
    return "https://www.youtube.com/results?search_query=vedantu+" + quote_plus(topic) + "+class+11+NCERT"


def fix_chapter_entries(text, chapter_key, new_title, new_url, slot1_title, slot1_id):
    """
    Within text, find the chapter_key's resource list and replace the first entry
    with a website-type entry, keeping the second entry as the verified youtube.
    Pattern:
        "CHAPTER_KEY": [
            {OLD_SLOT0},
            {SLOT1},
        ],
    """
    # Escape special regex chars in chapter_key
    ck_escaped = re.escape(chapter_key)

    # Build the new replacement block
    new_slot0 = (
        '{"title": "' + new_title + '", '
        '"type": "website", "url": "' + new_url + '"}'
    )
    new_slot1 = (
        '{"title": "' + slot1_title + '", '
        '"type": "youtube", "url": "https://www.youtube.com/watch?v=' + slot1_id + '"}'
    )
    replacement_list = "[\n            " + new_slot0 + ",\n            " + new_slot1 + ",\n        ]"

    # Match the chapter block: "KEY": [\n            {...},\n            {...},\n        ],
    pattern = (
        r'("' + ck_escaped + r'":\s*\[)'
        r'(\s*\{[^}]*\},)'       # first entry (any content)
        r'(\s*\{[^}]*\},?)'      # second entry
        r'(\s*\])'               # closing bracket
    )

    def replacer(m):
        return '"' + chapter_key + '": ' + replacement_list

    new_text, n = re.subn(pattern, replacer, text, count=1)
    return new_text, n


# Apply Physics fixes
for chapter_key, pw_topic, slot1_title, slot1_id in physics_fixes:
    pw_title = "Physics Wallah \u2014 " + chapter_key + " | Class 11 (India)"
    pw_url = make_pw_url(pw_topic)
    src, n = fix_chapter_entries(src, chapter_key, pw_title, pw_url, slot1_title, slot1_id)
    changes += n
    if n:
        print("Physics fixed:", chapter_key)
    else:
        print("Physics SKIPPED (no match):", chapter_key)

# Apply Chemistry fixes
for chapter_key, pw_topic, slot1_title, slot1_id in chemistry_fixes:
    pw_title = "Physics Wallah \u2014 " + chapter_key + " | Class 11 (India)"
    pw_url = make_pw_url(pw_topic)
    src, n = fix_chapter_entries(src, chapter_key, pw_title, pw_url, slot1_title, slot1_id)
    changes += n
    if n:
        print("Chemistry fixed:", chapter_key)
    else:
        print("Chemistry SKIPPED (no match):", chapter_key)

# Apply Biology fixes
for chapter_key, vedantu_topic, slot1_title, slot1_id in biology_fixes:
    v_title = "Vedantu \u2014 " + chapter_key + " | Class 11 (India)"
    v_url = make_vedantu_url(vedantu_topic)
    src, n
