#!/usr/bin/env python3
"""
Replace Physics Wallah (type:website) slot[0] entries with CrashCourse
embeddable YouTube videos (type:youtube) for Physics and Chemistry.

CrashCourse Physics playlist: PL8dPuuaLjXtN0ge7yDk_UA0ldZJdhwkoV
CrashCourse Chemistry playlist: PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr

Physics IDs (ordered):
 0 OoO5d5P0Jn4  Preview
 1 ZM8ECpBuQYE  #1  Motion in a Straight Line
 2 ObHJJYvu3RE  #2  Derivatives
 3 jLJLXka2wEM  #3  Integrals
 4 w3BhzYI6zXU  #4  Vectors and 2D Motion
 5 kKKM8Y-u7ds  #5  Newton's Laws
 6 fo_pmp5rtzo  #6  Friction
 7 bpFK2VCRHUs  #7  Uniform Circular Motion
 8 7gf6YpdvtE0  #8  Gravity
 9 w4QFJb9a8vo  #9  Work, Energy, Power
11 fmXFWi-WfyU  #11 Rotational Motion
13 9cbF9A6eQNA  #13 Statics and Torque
14 b5SqYuWT4-4  #14 Fluids at Rest
15 fJefjG3xhW0  #15 Fluids in Motion
16 jxstE6A_CYQ  #16 Temperature, Kinetic Theory, Gas Law
17 TfYCnOvNnFU  #17 Thermodynamics
19 XDsk6tZX55g  #19 Entropy / Oscillations
33 5fqwJyt4Lus  #33 Sound / Waves

Chemistry IDs (ordered):
 2 hQpQ0hxVNTg  #2  Unit Conversion & Significant Figures
 5 rcKilE9CdaA  #5  Atomic Theory
 6 UL1jmJaUkaQ  #6  Periodic Table
10 lQ6FBA1HM3s  #10 Chemical Bonding
 3 QiiyvzZBKT8  #3  Matter / States of Matter
16 TLRZAFU_9Kg  #16 Thermochemistry
18 SV7U4yAXL5I  #18 Equilibrium
25 cPDptc0wUYI  #25 Reduction/Oxidation
40 UloIw7dhnlQ  #40 Hydrocarbons (org)
41 CEH3O6l1pbw  #41 Organic Chemistry Basics
"""
import re

FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, encoding="utf-8") as f:
    src = f.read()

# (chapter_key, cc_title, cc_video_id, slot1_title, slot1_id)
# slot1 stays as the existing Khan Academy / Kurzgesagt / Veritasium youtube entry
FIXES = [
    # ── Physics ──────────────────────────────────────────────────────────────
    ("Units and Measurements",
     "CrashCourse — Unit Conversion & Significant Figures (International)",
     "hQpQ0hxVNTg",
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Units and Measurement",
     "CrashCourse — Unit Conversion & Significant Figures (International)",
     "hQpQ0hxVNTg",
     "Khan Academy — Distance and Displacement Intro (International)", "vQCkYm3v3aA"),
    ("Motion in a Straight Line",
     "CrashCourse Physics — Motion in a Straight Line (International)",
     "ZM8ECpBuQYE",
     "Khan Academy — Distance and Displacement (International)", "vQCkYm3v3aA"),
    ("Motion in a Plane",
     "CrashCourse Physics — Vectors and 2D Motion (International)",
     "w3BhzYI6zXU",
     "Khan Academy — Introduction to Vectors and Scalars (International)", "ihNZlp7iUHE"),
    ("Laws of Motion",
     "CrashCourse Physics — Newton's Laws (International)",
     "kKKM8Y-u7ds",
     "Khan Academy — Newton's Laws of Motion (International)", "CQYELiTtUs8"),
    ("Work, Energy and Power",
     "CrashCourse Physics — Work, Energy and Power (International)",
     "w4QFJb9a8vo",
     "Khan Academy — Work and Energy (International)", "ewfMcg3wRaQ"),
    ("System of Particles and Rotational Motion",
     "CrashCourse Physics — Rotational Motion (International)",
     "fmXFWi-WfyU",
     "Khan Academy — Angular Momentum and Torque (International)", "o7_zmuBweHI"),
    ("Gravitation",
     "CrashCourse Physics — Gravity (International)",
     "7gf6YpdvtE0",
     "Kurzgesagt — Gravity Explained (International)", "e5GBM-MEKzo"),
    ("Mechanical Properties of Solids",
     "CrashCourse Physics — Statics and Torque (International)",
     "9cbF9A6eQNA",
     "Khan Academy — Stress Strain and Elastic Modulus (International)", "VRXLvJPTV0k"),
    ("Mechanical Properties of Fluids",
     "CrashCourse Physics — Fluids at Rest (International)",
     "b5SqYuWT4-4",
     "Khan Academy — Fluid Pressure and Bernoulli Equation (International)", "VRXLvJPTV0k"),
    ("Thermal Properties of Matter",
     "CrashCourse Physics — Temperature and Kinetic Theory (International)",
     "jxstE6A_CYQ",
     "Khan Academy — Specific Heat and Thermal Energy (International)", "7L1EaURmvDs"),
    ("Thermodynamics",
     "CrashCourse Physics — Thermodynamics (International)",
     "TfYCnOvNnFU",
     "Veritasium — Entropy The Most Misunderstood Concept (International)", "DxL2HoqLbyA"),
    ("Kinetic Theory",
     "CrashCourse Physics — Temperature Kinetic Theory and Gas Law (International)",
     "jxstE6A_CYQ",
     "Khan Academy — Kinetic Molecular Theory (International)", "HkSXiHz9vUc"),
    ("Oscillations",
     "CrashCourse Physics — Uniform Circular Motion and SHM (International)",
     "bpFK2VCRHUs",
     "Khan Academy — Introduction to Simple Harmonic Motion (International)", "ZcZQsj6YAgU"),
    ("Waves",
     "CrashCourse Physics — Traveling Waves (International)",
     "5fqwJyt4Lus",
     "Khan Academy — Introduction to Waves (International)", "c38H6UKt3_I"),
    # ── Chemistry ────────────────────────────────────────────────────────────
    ("Some Basic Concepts of Chemistry",
     "CrashCourse Chemistry — Unit Conversion and the Mole (International)",
     "hQpQ0hxVNTg",
     "Khan Academy — The Mole and Avogadros Number (International)", "cvi4IJMZ13Q"),
    ("Structure of Atom",
     "CrashCourse Chemistry — Atomic Theory (International)",
     "rcKilE9CdaA",
     "Khan Academy — Bohr Model and Atomic Structure (International)", "haFTkhOcQaY"),
    ("Classification of Elements and Periodicity in Properties",
     "CrashCourse Chemistry — Periodic Table (International)",
     "UL1jmJaUkaQ",
     "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0"),
    ("Chemical Bonding and Molecular Structure",
     "CrashCourse Chemistry — Chemical Bonding (International)",
     "lQ6FBA1HM3s",
     "Khan Academy — Ionic and Covalent Bonding (International)", "FaeAurHnQJs"),
    ("States of Matter",
     "CrashCourse Chemistry — Matter Changing States (International)",
     "QiiyvzZBKT8",
     "Khan Academy — States of Matter and Ideal Gas (International)", "pKvo0XWZtjo"),
    ("Equilibrium",
     "CrashCourse Chemistry — Equilibrium (International)",
     "SV7U4yAXL5I",
     "Khan Academy — Chemical Equilibrium Constant (International)", "5HZbCNg9mIw"),
    ("Redox Reactions",
     "CrashCourse Chemistry — Reduction and Oxidation (International)",
     "cPDptc0wUYI",
     "Khan Academy — Oxidation and Reduction Redox (International)", "DvYs1HILq1g"),
    ("Hydrocarbons",
     "CrashCourse Chemistry — Hydrocarbons (International)",
     "UloIw7dhnlQ",
     "Khan Academy — Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
]

changed = 0
skipped = 0

# Work within GRADE_11_RESOURCES block only
g11s = src.find("GRADE_11_RESOURCES: dict")
g11e = src.find("GRADE_RESOURCES_MAP", g11s)
block = src[g11s:g11e]

for chapter_key, cc_title, cc_id, s1_title, s1_id in FIXES:
    ck = re.escape(chapter_key)
    pattern = (
        r'("' + ck + r'":\s*\[)'
        r'(\s*\{[^}]*\},)'
        r'(\s*\{[^}]*\},?)'
        r'(\s*\])'
    )
    new_s0 = ('{"title": "' + cc_title + '", '
              '"type": "youtube", "url": "https://www.youtube.com/watch?v=' + cc_id + '"}')
    new_s1 = ('{"title": "' + s1_title + '", '
              '"type": "youtube", "url": "https://www.youtube.com/watch?v=' + s1_id + '"}')
    replacement = ('"' + chapter_key + '": [\n'
                   '            ' + new_s0 + ',\n'
                   '            ' + new_s1 + ',\n'
                   '        ]')
    new_block, n = re.subn(pattern, replacement, block, count=1)
    if n:
        block = new_block
        changed += 1
        print(f"  fixed: {chapter_key}")
    else:
        skipped += 1
        print(f"  skipped: {chapter_key}")

# Also fix Chemistry Thermodynamics (special case - same key as Physics)
# It should be the SECOND occurrence of "Thermodynamics" in the block
thermo_cc = ('{"title": "CrashCourse Chemistry — Thermochemistry (International)", '
             '"type": "youtube", "url": "https://www.youtube.com/watch?v=TLRZAFU_9Kg"}')
thermo_s1 = ('{"title": "Khan Academy — Enthalpy and Thermochemistry (International)", '
             '"type": "youtube", "url": "https://www.youtube.com/watch?v=TNwGNHqwHxc"}')

# Find second Thermodynamics occurrence and replace its slot[0]
thermo_pattern = (r'("Thermodynamics":\s*\[)'
                  r'(\s*\{[^}]*\},)'
                  r'(\s*\{[^}]*\},?)'
                  r'(\s*\])')
matches = list(re.finditer(thermo_pattern, block))
if len(matches) >= 2:
    m = matches[1]  # second Thermodynamics = Chemistry
    new_entry = ('"Thermodynamics": [\n'
                 '            ' + thermo_cc + ',\n'
                 '            ' + thermo_s1 + ',\n'
                 '        ]')
    block = block[:m.start()] + new_entry + block[m.end():]
    changed += 1
    print(f"  fixed: Chemistry Thermodynamics (2nd occurrence)")
else:
    print(f"  skipped: Chemistry Thermodynamics (found {len(matches)} occurrences)")

src = src[:g11s] + block + src[g11e:]
with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nDone: {changed} fixed, {skipped} skipped")
