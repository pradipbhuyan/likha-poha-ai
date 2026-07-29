#!/usr/bin/env python3
"""Fix 2: Replace duplicate slot[0] entries with Indian video search links.

For Physics/Chemistry: slot[0] -> Physics Wallah search (type "website")
For Biology/Mathematics: slot[0] -> Vedantu search (type "website")
slot[1] stays as the verified international youtube embed.
"""
import re
from urllib.parse import quote_plus

FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, encoding="utf-8") as f:
    src = f.read()

def pw(topic):
    return ("https://www.youtube.com/results?search_query=physics+wallah+"
            + quote_plus(topic) + "+class+11")

def ved(topic):
    return ("https://www.youtube.com/results?search_query=vedantu+"
            + quote_plus(topic) + "+class+11+NCERT")

# (chapter_key, slot0_title, slot0_url, slot1_title, slot1_id)
FIXES = [
    # ── Physics ──────────────────────────────────────────────────────────────
    ("Units and Measurements",
     "Physics Wallah — Units and Measurements | Class 11 (India)", pw("units and measurements"),
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Units and Measurement",
     "Physics Wallah — Units and Measurement | Class 11 (India)", pw("units and measurement"),
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Motion in a Straight Line",
     "Physics Wallah — Motion in a Straight Line | Class 11 (India)", pw("motion in a straight line"),
     "Khan Academy — Distance and Displacement (International)", "vQCkYm3v3aA"),
    ("Motion in a Plane",
     "Physics Wallah — Motion in a Plane | Class 11 (India)", pw("motion in a plane"),
     "Khan Academy — Introduction to Vectors and Scalars (International)", "ihNZlp7iUHE"),
    ("Laws of Motion",
     "Physics Wallah — Laws of Motion | Class 11 (India)", pw("laws of motion"),
     "Khan Academy — Newton's Laws of Motion (International)", "CQYELiTtUs8"),
    ("Work, Energy and Power",
     "Physics Wallah — Work Energy and Power | Class 11 (India)", pw("work energy and power"),
     "Khan Academy — Work and Energy (International)", "ewfMcg3wRaQ"),
    ("System of Particles and Rotational Motion",
     "Physics Wallah — System of Particles and Rotational Motion | Class 11 (India)",
     pw("system of particles and rotational motion"),
     "Khan Academy — Angular Momentum and Torque (International)", "o7_zmuBweHI"),
    ("Gravitation",
     "Physics Wallah — Gravitation | Class 11 (India)", pw("gravitation"),
     "Kurzgesagt — Gravity Explained (International)", "e5GBM-MEKzo"),
    ("Mechanical Properties of Solids",
     "Physics Wallah — Mechanical Properties of Solids | Class 11 (India)",
     pw("mechanical properties of solids"),
     "Khan Academy — Stress Strain and Elastic Modulus (International)", "VRXLvJPTV0k"),
    ("Mechanical Properties of Fluids",
     "Physics Wallah — Mechanical Properties of Fluids | Class 11 (India)",
     pw("mechanical properties of fluids"),
     "Khan Academy — Fluid Pressure and Bernoulli Equation (International)", "VRXLvJPTV0k"),
    ("Thermal Properties of Matter",
     "Physics Wallah — Thermal Properties of Matter | Class 11 (India)",
     pw("thermal properties of matter"),
     "Khan Academy — Specific Heat and Thermal Energy (International)", "7L1EaURmvDs"),
    ("Thermodynamics",
     "Physics Wallah — Thermodynamics | Class 11 (India)", pw("thermodynamics"),
     "Veritasium — Entropy The Most Misunderstood Concept (International)", "DxL2HoqLbyA"),
    ("Kinetic Theory",
     "Physics Wallah — Kinetic Theory | Class 11 (India)", pw("kinetic theory"),
     "Khan Academy — Kinetic Molecular Theory (International)", "HkSXiHz9vUc"),
    ("Oscillations",
     "Physics Wallah — Oscillations | Class 11 (India)", pw("oscillations"),
     "Khan Academy — Introduction to Simple Harmonic Motion (International)", "ZcZQsj6YAgU"),
    ("Waves",
     "Physics Wallah — Waves | Class 11 (India)", pw("waves"),
     "Khan Academy — Introduction to Waves (International)", "c38H6UKt3_I"),
    # ── Chemistry ────────────────────────────────────────────────────────────
    ("Some Basic Concepts of Chemistry",
     "Physics Wallah — Some Basic Concepts of Chemistry | Class 11 (India)",
     pw("some basic concepts of chemistry"),
     "Khan Academy — The Mole and Avogadros Number (International)", "cvi4IJMZ13Q"),
    ("Structure of Atom",
     "Physics Wallah — Structure of Atom | Class 11 (India)", pw("structure of atom"),
     "Khan Academy — Bohr Model and Atomic Structure (International)", "haFTkhOcQaY"),
    ("Classification of Elements and Periodicity in Properties",
     "Physics Wallah — Classification of Elements and Periodicity | Class 11 (India)",
     pw("classification of elements and periodicity"),
     "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0"),
    ("Chemical Bonding and Molecular Structure",
     "Physics Wallah — Chemical Bonding and Molecular Structure | Class 11 (India)",
     pw("chemical bonding and molecular structure"),
     "Khan Academy — Ionic and Covalent Bonding (International)", "FaeAurHnQJs"),
    ("States of Matter",
     "Physics Wallah — States of Matter | Class 11 (India)", pw("states of matter"),
     "Khan Academy — States of Matter and Ideal Gas (International)", "pKvo0XWZtjo"),
    ("Equilibrium",
     "Physics Wallah — Equilibrium | Class 11 (India)", pw("equilibrium"),
     "Khan Academy — Chemical Equilibrium Constant (International)", "5HZbCNg9mIw"),
    ("Redox Reactions",
     "Physics Wallah — Redox Reactions | Class 11 (India)", pw("redox reactions"),
     "Khan Academy — Oxidation and Reduction Redox (International)", "DvYs1HILq1g"),
    ("Hydrocarbons",
     "Physics Wallah — Hydrocarbons | Class 11 (India)", pw("hydrocarbons"),
     "Khan Academy — Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    # ── Biology ───────────────────────────────────────────────────────────────
    ("The Living World",
     "Vedantu — The Living World | Class 11 (India)", ved("the living world"),
     "Kurzgesagt — What Is Life How Does It Work (International)", "QOCaacO8wus"),
    ("Biological Classification",
     "Vedantu — Biological Classification | Class 11 (India)", ved("biological classification"),
     "Khan Academy — Taxonomy and Classification (International)", "mrheet-2osg"),
    ("Plant Kingdom",
     "Vedantu — Plant Kingdom | Class 11 (India)", ved("plant kingdom"),
     "Kurzgesagt — How Evolution Works (International)", "hOfRN0KihOU"),
    ("Animal Kingdom",
     "Vedantu — Animal Kingdom | Class 11 (India)", ved("animal kingdom"),
     "Kurzgesagt — The Immune System Explained (International)", "lXfEK8G8CUI"),
    ("Cell: The Unit of Life",
     "Vedantu — Cell The Unit of Life | Class 11 (India)", ved("cell unit of life"),
     "Khan Academy — Cell Structure and Function (International)", "7FN1NBoV2u0"),
    ("Biomolecules",
     "Vedantu — Biomolecules | Class 11 (India)", ved("biomolecules"),
     "Khan Academy — Macromolecules Proteins Carbs Lipids (International)", "HGg_WiaSr4U"),
    ("Cell Cycle and Cell Division",
     "Vedantu — Cell Cycle and Cell Division | Class 11 (India)", ved("cell cycle and cell division"),
     "Khan Academy — Mitosis and Cell Division (International)", "U5vAO_f2LDQ"),
    ("Photosynthesis in Higher Plants",
     "Vedantu — Photosynthesis in Higher Plants | Class 11 (India)",
     ved("photosynthesis in higher plants"),
     "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA"),
    ("Respiration in Plants",
     "Vedantu — Respiration in Plants | Class 11 (India)", ved("respiration in plants"),
     "Khan Academy — Cellular Respiration Overview (International)", "ArmlWtDnuys"),
    ("Breathing and Exchange of Gases",
     "Vedantu — Breathing and Exchange of Gases | Class 11 (India)",
     ved("breathing and exchange of gases"),
     "Khan Academy — Respiratory System and Breathing (International)", "qGiPZf7njqY"),
    ("Body Fluids and Circulation",
     "Vedantu — Body Fluids and Circulation | Class 11 (India)", ved("body fluids and circulation"),
     "Khan Academy — Heart and Circulatory System (International)", "7K2icszdxQc"),
    ("Neural Control and Coordination",
     "Vedantu — Neural Control and Coordination | Class 11 (India)",
     ved("neural control and coordination"),
     "Khan Academy — Neurons and the Nervous System (International)", "h2H6POZowiU"),
    ("Chemical Coordination and Integration",
     "Vedantu — Chemical Coordination and Integration | Class 11 (India)",
     ved("chemical coordination and integration"),
     "Khan Academy — Endocrine System and Hormones (International)", "ER49EweKwW8"),
    # ── Mathematics ───────────────────────────────────────────────────────────
    ("Sets",
     "Vedantu — Sets | Class 11 (India)", ved("sets"),
     "Khan Academy — Introduction to Sets (International)", "riXcZT2ICjA"),
    ("Relations and Functions",
     "Vedantu — Relations and Functions | Class 11 (India)", ved("relations and functions"),
     "Khan Academy — Relations and Functions (International)", "-DTMakGDZAw"),
    ("Trigonometric Functions",
     "Vedantu — Trigonometric Functions | Class 11 (India)", ved("trigonometric functions"),
     "3Blue1Brown — Eulers Formula and Trigonometry (International)", "mvmuCPvRoWQ"),
    ("Complex Numbers and Quadratic Equations",
     "Vedantu — Complex Numbers and Quadratic Equations | Class 11 (India)",
     ved("complex numbers and quadratic equations"),
     "Khan Academy — Complex Numbers (International)", "T647CGsuOVU"),
    ("Linear Inequalities",
     "Vedantu — Linear Inequalities | Class 11 (India)", ved("linear inequalities"),
     "Khan Academy — Linear Inequalities (International)", "Z1zdkcwosD4"),
    ("Permutations and Combinations",
     "Vedantu — Permutations and Combinations | Class 11 (India)",
     ved("permutations and combinations"),
     "Khan Academy — Permutations and Combinations (International)", "Z1zdkcwosD4"),
    ("Binomial Theorem",
     "Vedantu — Binomial Theorem | Class 11 (India)", ved("binomial theorem"),
     "Khan Academy — Binomial Theorem (International)", "WUvTyaaNkzM"),
    ("Sequences and Series",
     "Vedantu — Sequences and Series | Class 11 (India)", ved("sequences and series"),
     "Khan Academy — Arithmetic Sequences and Series (International)", "_cooC3yG_p0"),
    ("Straight Lines",
     "Vedantu — Straight Lines | Class 11 (India)", ved("straight lines"),
     "Khan Academy — Slope and Equation of a Line (International)", "XMJ72mtMn4Y"),
    ("Conic Sections",
     "Vedantu — Conic Sections | Class 11 (India)", ved("conic sections"),
     "Khan Academy — Introduction to Conic Sections (International)", "0A7RR0oy2ho"),
    ("Introduction to Three Dimensional Geometry",
     "Vedantu — Introduction to Three Dimensional Geometry | Class 11 (India)",
     ved("introduction to three dimensional geometry"),
     "Khan Academy — 3D Geometry Introduction (International)", "riXcZT2ICjA"),
    ("Limits and Derivatives",
     "Vedantu — Limits and Derivatives | Class 11 (India)", ved("limits and derivatives"),
     "3Blue1Brown — Essence of Calculus (International)", "WUvTyaaNkzM"),
    ("Statistics",
     "Vedantu — Statistics | Class 11 (India)", ved("statistics"),
     "Khan Academy — Mean Median and Mode Statistics (International)", "k3aKKasOmIw"),
    ("Probability",
     "Vedantu — Probability | Class 11 (India)", ved("probability"),
     "Khan Academy — Basic Probability (International)", "uzkc-qNVoOk"),
]

changed = 0
skipped = 0

for chapter_key, s0_title, s0_url, s1_title, s1_id in FIXES:
    ck = re.escape(chapter_key)
    # Match: "KEY": [\n            {any dict},\n            {any dict},?\n        ]
    pattern = (
        r'("' + ck + r'":\s*\[)'
        r'(\s*\{[^}]*\},)'
        r'(\s*\{[^}]*\},?)'
        r'(\s*\])'
    )
    new_s0 = ('{"title": "' + s0_title + '", '
              '"type": "website", "url": "' + s0_url + '"}')
    new_s1 = ('{"title": "' + s1_title + '", '
              '"type": "youtube", "url": "https://www.youtube.com/watch?v=' + s1_id + '"}')
    replacement = ('"' + chapter_key + '": [\n'
                   '            ' + new_s0 + ',\n'
                   '            ' + new_s1 + ',\n'
                   '        ]')

    new_src, n = re.subn(pattern, replacement, src, count=1)
    if n:
        src = new_src
        changed += 1
        print(f"  fixed: {chapter_key}")
    else:
        skipped += 1
        print(f"  skipped (no match): {chapter_key}")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nDone: {changed} fixed, {skipped} skipped")
