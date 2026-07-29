#!/usr/bin/env python3
"""Add GRADE_12_RESOURCES to resources.py and register in GRADE_RESOURCES_MAP.
Physics 14ch, Chemistry 16ch, Biology 16ch, Mathematics 13ch — all CrashCourse + KA/3B1B.
"""
import re, sys
sys.path.insert(0, 'backend')

FILE = "backend/app/data/resources.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()

# ── Video ID references ───────────────────────────────────────────────────────
# CC Physics (PL8dPuuaLjXtN0ge7yDk_UA0ldZJdhwkoV) indices 20-46:
CP = {20:'6BHbJ_gBOk0',21:'WOEvvHbc240',22:'tuSC0ObB-qY',23:'4i1MUWJoI0U',24:'p1woKh2mdVQ',
      25:'TFlVWf8JX4A',26:'mdulzEfQXDE',27:'ZrMltpK6iAw',28:'HXOok3mfMLM',29:'g-wjP1otQWI',
      30:'-w-VTw0tQlE',32:'s94suB5uLWw',37:'K40lNL3KsJ4',38:'Oh4m8Ees-3Q',
      43:'7kb1VT0J3DE',44:'qO_W70VegbQ',45:'lUhJL7o6_cA',46:'VYxYuaDvdM0'}
# CC Chemistry (PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr):
CC = {2:'hQpQ0hxVNTg',5:'rcKilE9CdaA',7:'AN4KifV12DA',8:'ANi709MYnWg',
      14:'GIPrsWuSkQc',15:'JbqtqCunYzA',16:'TLRZAFU_9Kg',17:'GqtUWyDR1fg',
      24:'a8LF7JEb0IA',25:'cPDptc0wUYI',27:'9h2f1Bjr0p4',28:'g5wNg_dKsYY',
      30:'LS67vS10O5Y',31:'8Fdt5WnYn1k',32:'7qOFtL3VEBc',40:'UloIw7dhnlQ',
      41:'CEH3O6l1pbw',42:'kXFEex-dABU',43:'hlXc_eEtBHA',44:'U7wavimfNFE',
      45:'rHxxLYzJ8Sw',46:'aLuSi_6Ol8M'}
# CC Biology (PL8dPuuaLjXtPW_ofbxdHNciuLoTRLPMgB):
CB = {1:'tZE_fQFK8EY',2:'xOLcZMw0hd4',4:'cjR5zPrVjTc',7:'KfHYN6tZnpU',
      9:'HsAUGbUgx6Y',10:'IALw687nswo',11:'2TSIUt-lHyo',12:'fBOrzQP423A',
      13:'i-VeKZeyHZs',14:'4joZpdXeS4A',16:'4mxJbgdiyIY',17:'YM6Ekb5De2o',
      18:'Aa1dGBKgGVc',20:'y7raEBOvLwU',27:'HeO3yagexTw',28:'-ZRsLhaukn8',
      29:'skPOXcVvS5c',31:'YnJPbphsoMY',32:'9zwq8N4Ufd8',33:'4YNDB_zSzfE',
      35:'j6YaOqKORYY',36:'6ulXau2HyHg',39:'xSbMX0MFJCY',40:'o-WFU5ovaTc',
      43:'kjZAHBMMKoU',44:'gAWYROgu4JU',47:'SyHM1gFyP8Y'}
# CC Statistics (PL0o_zxa4K1BVsziIRdfv4Hl4UIqDZhXWV):
CS = {0:'XZo4xyJXCak',3:'Mb9BuEkbaHQ',4:'LuBD49SFpWs',6:'gq3FPpm2yvA',
      7:'6hJGa4Zp62M',9:'JnoBjHz2dtw',10:'MUCvUgGfzdo',11:'wkAjnGmRPVo',
      14:'FP6qS5d3Ly4',20:'6G6i8vSa8Zs',32:'Sqkhzdn1eOU',40:'SkidyDQuupA'}

def row(s0t, s0id, s1t, s1id, indent='        '):
    s0 = ('{"title": "' + s0t + '", "type": "youtube", '
          '"url": "https://www.youtube.com/watch?v=' + s0id + '"}')
    s1 = ('{"title": "' + s1t + '", "type": "youtube", '
          '"url": "https://www.youtube.com/watch?v=' + s1id + '"}')
    return ('[\n' + indent + '    ' + s0 + ',\n' +
            indent + '    ' + s1 + ',\n' + indent + ']')

# ── Build GRADE_12_RESOURCES Python source ────────────────────────────────────
lines = [
    '',
    '# \u2500\u2500 Grade 12 resources \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500',
    'GRADE_12_RESOURCES: dict[str, dict[str, list]] = {',
]

# ── Physics ───────────────────────────────────────────────────────────────────
lines.append('    "Physics": {')
PHY12 = [
    ("Electric Charges and Fields",
     "CrashCourse Physics \u2014 Electric Charge (International)", CP[20],
     "Khan Academy \u2014 Electric Charge and Electric Force (International)", "YG4_4n46Scc"),
    ("Electrostatic Potential and Capacitance",
     "CrashCourse Physics \u2014 Electric Potential (International)", CP[22],
     "Khan Academy \u2014 Electric Potential Energy (International)", "zqGvUbvVQXg"),
    ("Current Electricity",
     "CrashCourse Physics \u2014 Electric Current (International)", CP[23],
     "Khan Academy \u2014 Introduction to Electric Current (International)", "YSX9-vkMhLY"),
    ("Moving Charges and Magnetism",
     "CrashCourse Physics \u2014 Magnetism (International)", CP[25],
     "Khan Academy \u2014 Magnetic Force on Moving Charge (International)", "uFqEXHECvO0"),
    ("Magnetism and Matter",
     "CrashCourse Physics \u2014 Magnetism (International)", CP[25],
     "Khan Academy \u2014 Magnetic Force on Current Carrying Wire (International)", "qYkqXq9CZNY"),
    ("Electromagnetic Induction",
     "CrashCourse Physics \u2014 Electromagnetic Induction (International)", CP[26],
     "Khan Academy \u2014 Introduction to Electromagnetic Induction (International)", "LqFLmqMFKGM"),
    ("Alternating Current",
     "CrashCourse Physics \u2014 AC Circuits (International)", CP[27],
     "Khan Academy \u2014 AC Circuits and Alternating Current (International)", "uoFB4kJsIko"),
    ("Electromagnetic Waves",
     "CrashCourse Physics \u2014 Electromagnetic Waves (International)", CP[28],
     "Khan Academy \u2014 Introduction to Electromagnetic Waves (International)", "FMVD-D65-l8"),
    ("Ray Optics and Optical Instruments",
     "CrashCourse Physics \u2014 Geometric Optics (International)", CP[29],
     "Khan Academy \u2014 Reflection and Refraction of Light (International)", "DveX84Rszjo"),
    ("Wave Optics",
     "CrashCourse Physics \u2014 Wave Optics (International)", CP[32],
     "Khan Academy \u2014 Young Double Slit Experiment (International)", "Iuv6hY6zsd0"),
    ("Dual Nature of Radiation and Matter",
     "CrashCourse Physics \u2014 Quantum Mechanics (International)", CP[43],
     "Khan Academy \u2014 Photoelectric Effect (International)", "v-1zjsqaAoE"),
    ("Atoms",
     "CrashCourse Physics \u2014 Nuclear Physics (International)", CP[37],
     "Khan Academy \u2014 Bohr Model of Hydrogen (International)", "GD1NJ7HFO6s"),
    ("Nuclei",
     "CrashCourse Physics \u2014 Radioactivity (International)", CP[45],
     "Khan Academy \u2014 Nuclear Binding Energy (International)", "LLBZ3Ec_Sro"),
    ("Semiconductor Electronics: Materials, Devices and Simple Circuits",
     "CrashCourse Physics \u2014 Quantum Mechanics (International)", CP[44],
     "Khan Academy \u2014 Semiconductors Introduction (International)", "DvkE48qW6iY"),
]
for ch, s0t, s0id, s1t, s1id in PHY12:
    lines.append('        "' + ch + '": ' + row(s0t, s0id, s1t, s1id) + ',')
lines.append('    },')

# ── Chemistry ─────────────────────────────────────────────────────────────────
lines.append('    "Chemistry": {')
CHEM12 = [
    ("The Solid State",
     "CrashCourse Chemistry \u2014 Solids (International)", CC[30],
     "Khan Academy \u2014 Solids Liquids and Gases (International)", "pKvo0XWZtjo"),
    ("Solutions",
     "CrashCourse Chemistry \u2014 Solutions (International)", CC[15],
     "Khan Academy \u2014 Solutions and Mixtures (International)", "3ROWXs3jtBU"),
    ("Electrochemistry",
     "CrashCourse Chemistry \u2014 Electrochemistry (International)", CC[24],
     "Khan Academy \u2014 Introduction to Electrochemistry (International)", "lQ6FBA1HM3s"),
    ("Chemical Kinetics",
     "CrashCourse Chemistry \u2014 Reaction Rates (International)", CC[17],
     "Khan Academy \u2014 Introduction to Chemical Kinetics (International)", "5HZbCNg9mIw"),
    ("Surface Chemistry",
     "CrashCourse Chemistry \u2014 Intermolecular Forces (International)", CC[14],
     "Khan Academy \u2014 Intermolecular Forces (International)", "pKvo0XWZtjo"),
    ("General Principles and Processes of Isolation of Elements",
     "CrashCourse Chemistry \u2014 Oxidation States (International)", CC[25],
     "Khan Academy \u2014 Oxidation and Reduction (International)", "DvYs1HILq1g"),
    ("The p-Block Elements",
     "CrashCourse Chemistry \u2014 The Nucleus (International)", CC[8],
     "Khan Academy \u2014 Periodic Table Trends (International)", "MyBYZJ3Wo_0"),
    ("The d and f Block Elements",
     "CrashCourse Chemistry \u2014 Electron Configuration (International)", CC[7],
     "Khan Academy \u2014 Electron Configuration (International)", "haFTkhOcQaY"),
    ("Coordination Compounds",
     "CrashCourse Chemistry \u2014 Calorimetry (International)", CC[31],
     "Khan Academy \u2014 Chemical Bonding and Molecular Structure (International)", "FaeAurHnQJs"),
    ("Haloalkanes and Haloarenes",
     "CrashCourse Chemistry \u2014 Organic Chemistry Basics (International)", CC[41],
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    ("Alcohols, Phenols and Ethers",
     "CrashCourse Chemistry \u2014 Alcohols (International)", CC[42],
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    ("Aldehydes, Ketones and Carboxylic Acids",
     "CrashCourse Chemistry \u2014 Aldehydes and Ketones (International)", CC[43],
     "Khan Academy \u2014 Carbonyl Groups (International)", "nDV5yWfHKko"),
    ("Amines",
     "CrashCourse Chemistry \u2014 Amines (International)", CC[44],
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    ("Biomolecules",
     "CrashCourse Chemistry \u2014 Biomolecules (International)", CC[45],
     "Khan Academy \u2014 Macromolecules Proteins Carbs Lipids (International)", "HGg_WiaSr4U"),
    ("Polymers",
     "CrashCourse Chemistry \u2014 Big Questions in Chemistry (International)", CC[46],
     "Khan Academy \u2014 Introduction to Organic Chemistry (International)", "nDV5yWfHKko"),
    ("Chemistry in Everyday Life",
     "CrashCourse Chemistry \u2014 Big Questions in Chemistry (International)", CC[46],
     "Khan Academy \u2014 Acids and Bases (International)", "5HZbCNg9mIw"),
]
for ch, s0t, s0id, s1t, s1id in CHEM12:
    lines.append('        "' + ch + '": ' + row(s0t, s0id, s1t, s1id) + ',')
lines.append('    },')

# ── Biology ───────────────────────────────────────────────────────────────────
lines.append('    "Biology": {')
BIO12 = [
    ("Reproduction in Organisms",
     "CrashCourse Biology \u2014 Meiosis (International)", CB[11],
     "Khan Academy \u2014 Meiosis and Sexual Reproduction (International)", "U5vAO_f2LDQ"),
    ("Sexual Reproduction in Flowering Plants",
     "CrashCourse Biology \u2014 Meiosis (International)", CB[11],
     "Khan Academy \u2014 Photosynthesis Overview (International)", "-rsYk4eCKnA"),
    ("Human Reproduction",
     "CrashCourse Biology \u2014 Reproductive System (International)", CB[43],
     "Khan Academy \u2014 Human Reproductive Biology (International)", "U5vAO_f2LDQ"),
    ("Reproductive Health",
     "CrashCourse Biology \u2014 Reproductive System (International)", CB[43],
     "Khan Academy \u2014 Mitosis and Cell Division (International)", "U5vAO_f2LDQ"),
    ("Principles of Inheritance and Variation",
     "CrashCourse Biology \u2014 Variation in Populations (International)", CB[13],
     "Khan Academy \u2014 Mitosis and Cell Division (International)", "U5vAO_f2LDQ"),
    ("Molecular Basis of Inheritance",
     "CrashCourse Biology \u2014 DNA Structure and Replication (International)", CB[14],
     "Khan Academy \u2014 DNA Structure and Replication (International)", "4joZpdXeS4A"),
    ("Evolution",
     "CrashCourse Biology \u2014 Natural Selection (International)", CB[12],
     "Kurzgesagt \u2014 How Evolution Works (International)", "hOfRN0KihOU"),
    ("Human Health and Disease",
     "CrashCourse Biology \u2014 The Immune System (International)", CB[35],
     "Kurzgesagt \u2014 The Immune System Explained (International)", "lXfEK8G8CUI"),
    ("Strategies for Enhancement in Food Production",
     "CrashCourse Biology \u2014 The Chemistry of Life (International)", CB[2],
     "Khan Academy \u2014 Photosynthesis Overview (International)", "-rsYk4eCKnA"),
    ("Microbes in Human Welfare",
     "CrashCourse Biology \u2014 The Science of Biology (International)", CB[1],
     "Khan Academy \u2014 Cellular Respiration Overview (International)", "ArmlWtDnuys"),
    ("Biotechnology: Principles and Processes",
     "CrashCourse Biology \u2014 Transcription and Translation (International)", CB[16],
     "Khan Academy \u2014 DNA Replication (International)", "4joZpdXeS4A"),
    ("Biotechnology and its Applications",
     "CrashCourse Biology \u2014 More Transcription (International)", CB[17],
     "Khan Academy \u2014 DNA Structure and Replication (International)", "4joZpdXeS4A"),
    ("Organisms and Populations",
     "CrashCourse Biology \u2014 Population Ecology (International)", CB[39],
     "Khan Academy \u2014 Ecology Introduction (International)", "-rsYk4eCKnA"),
    ("Ecosystem",
     "CrashCourse Biology \u2014 Community Ecology (International)", CB[40],
     "Kurzgesagt \u2014 What Is Life How Does It Work (International)", "QOCaacO8wus"),
    ("Biodiversity and Conservation",
     "CrashCourse Biology \u2014 Species and Biodiversity (International)", CB[47],
     "Kurzgesagt \u2014 How Evolution Works (International)", "hOfRN0KihOU"),
    ("Environmental Issues",
     "CrashCourse Biology \u2014 Ecology and the Environment (International)", CB[47],
     "Kurzgesagt \u2014 Overpopulation and the Environment (International)", "QOCaacO8wus"),
]
for ch, s0t, s0id, s1t, s1id in BIO12:
    lines.append('        "' + ch + '": ' + row(s0t, s0id, s1t, s1id) + ',')
lines.append('    },')

# ── Mathematics ───────────────────────────────────────────────────────────────
lines.append('    "Mathematics": {')
MATH12 = [
    ("Relations and Functions",
     "CrashCourse Statistics \u2014 Data Visualization (International)", CS[0],
     "Khan Academy \u2014 Relations and Functions (International)", "-DTMakGDZAw"),
    ("Inverse Trigonometric Functions",
     "CrashCourse Physics \u2014 Wave Optics (International)", CP[32],
     "Khan Academy \u2014 Inverse Trigonometric Functions (International)", "YXWKpgmLgHk"),
    ("Matrices",
     "3Blue1Brown \u2014 Essence of Linear Algebra (International)", "fNk_zzaMoSs",
     "Khan Academy \u2014 Introduction to Matrices (International)", "kqWCgIVDRBo"),
    ("Determinants",
     "3Blue1Brown \u2014 Determinant of a Matrix (International)", "Ip3X9LOh2iI",
     "Khan Academy \u2014 Determinants (International)", "OI07C1HsOuc"),
    ("Continuity and Differentiability",
     "3Blue1Brown \u2014 Essence of Calculus (International)", "WUvTyaaNkzM",
     "Khan Academy \u2014 Continuity and Differentiability (International)", "riXcZT2ICjA"),
    ("Application of Derivatives",
     "3Blue1Brown \u2014 Derivatives Visualized (International)", "S0_qX4VJhMQ",
     "Khan Academy \u2014 Application of Derivatives (International)", "XMJ72mtMn4Y"),
    ("Integrals",
     "3Blue1Brown \u2014 Integration and the Fundamental Theorem (International)", "rfG8ce4nNh0",
     "Khan Academy \u2014 Introduction to Integrals (International)", "riXcZT2ICjA"),
    ("Application of Integrals",
     "3Blue1Brown \u2014 Essence of Calculus (International)", "WUvTyaaNkzM",
     "Khan Academy \u2014 Application of Integrals (International)", "riXcZT2ICjA"),
    ("Differential Equations",
     "3Blue1Brown \u2014 Differential Equations Introduction (International)", "p_di4Zn4wz4",
     "Khan Academy \u2014 Introduction to Differential Equations (International)", "riXcZT2ICjA"),
    ("Vector Algebra",
     "3Blue1Brown \u2014 Vectors What Even Are They (International)", "fNk_zzaMoSs",
     "Khan Academy \u2014 Vector Basics (International)", "ihNZlp7iUHE"),
    ("Three Dimensional Geometry",
     "CrashCourse Physics \u2014 Geometric Optics (International)", CP[29],
     "Khan Academy \u2014 3D Geometry Introduction (International)", "riXcZT2ICjA"),
    ("Linear Programming",
     "CrashCourse Statistics \u2014 Linear Regression (International)", CS[20],
     "Khan Academy \u2014 Linear Programming (International)", "Z1zdkcwosD4"),
    ("Probability",
     "CrashCourse Statistics \u2014 Basic Probability (International)", CS[9],
     "Khan Academy \u2014 Basic Probability (International)", "uzkc-qNVoOk"),
]
for ch, s0t, s0id, s1t, s1id in MATH12:
    lines.append('        "' + ch + '": ' + row(s0t, s0id, s1t, s1id) + ',')
lines.append('    },')

lines.append('}')
lines.append('')

G12_SRC = '\n'.join(lines)

# ── Insert before GRADE_RESOURCES_MAP ────────────────────────────────────────
marker = '\n# \u2500\u2500 Grade-aware resource lookup'
idx = src.find(marker)
if idx >= 0:
    src = src[:idx] + '\n' + G12_SRC + src[idx:]
    print("Inserted GRADE_12_RESOURCES before GRADE_RESOURCES_MAP")
else:
    print("ERROR: GRADE_RESOURCES_MAP marker not found")

# ── Add Grade 12 to GRADE_RESOURCES_MAP ──────────────────────────────────────
old_map = ('GRADE_RESOURCES_MAP = {\n'
           '    "Grade 8": GRADE_8_RESOURCES,\n'
           '    "Grade 10": GRADE_10_RESOURCES,\n'
           '    "Grade 11": GRADE_11_RESOURCES,\n'
           '}')
new_map = ('GRADE_RESOURCES_MAP = {\n'
           '    "Grade 8": GRADE_8_RESOURCES,\n'
           '    "Grade 10": GRADE_10_RESOURCES,\n'
           '    "Grade 11": GRADE_11_RESOURCES,\n'
           '    "Grade 12": GRADE_12_RESOURCES,\n'
           '}')
if old_map in src:
    src = src.replace(old_map, new_map, 1)
    print("Added Grade 12 to GRADE_RESOURCES_MAP")
else:
    print("WARNING: GRADE_RESOURCES_MAP not updated (pattern not found)")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
print("File saved.")

# ── Verify ────────────────────────────────────────────────────────────────────
import importlib, app.data.resources as rmod; importlib.reload(rmod)
from app.data.resources import GRADE_12_RESOURCES, GRADE_RESOURCES_MAP
print(f"Grade 12 in map: {'Grade 12' in GRADE_RESOURCES_MAP}")
for subj in ["Physics", "Chemistry", "Biology", "Mathematics"]:
    n = len(GRADE_12_RESOURCES.get(subj, {}))
    print(f"  {subj}: {n} chapters")
