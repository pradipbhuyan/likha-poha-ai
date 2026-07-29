#!/usr/bin/env python3
"""Replace Grade 11 Mathematics Vedantu slot[0] with CrashCourse Statistics / 3B1B."""
import re, sys
sys.path.insert(0, 'backend')

FILE = "backend/app/data/resources.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()

# Grade 11 Math: (chapter, cc_title, cc_id, ka_title, ka_id)
# slot[0] = CrashCourse Statistics or 3Blue1Brown
# slot[1] = Khan Academy (keep as-is, just use the same IDs)
G11_MATH = [
    ("Sets",
     "CrashCourse Statistics \u2014 What is Statistics (International)", "XZo4xyJXCak",
     "Khan Academy \u2014 Introduction to Sets (International)", "riXcZT2ICjA"),
    ("Relations and Functions",
     "CrashCourse Statistics \u2014 Data Visualization (International)", "VHYOuWu9jQI",
     "Khan Academy \u2014 Relations and Functions (International)", "-DTMakGDZAw"),
    ("Trigonometric Functions",
     "CrashCourse Statistics \u2014 Normal Distribution (International)", "Iu17mY1VfZU",
     "3Blue1Brown \u2014 Eulers Formula and Trigonometry (International)", "mvmuCPvRoWQ"),
    ("Complex Numbers and Quadratic Equations",
     "CrashCourse Statistics \u2014 Z-Scores (International)", "6hJGa4Zp62M",
     "Khan Academy \u2014 Complex Numbers (International)", "T647CGsuOVU"),
    ("Linear Inequalities",
     "CrashCourse Statistics \u2014 Measures of Spread (International)", "LuBD49SFpWs",
     "Khan Academy \u2014 Linear Inequalities (International)", "Z1zdkcwosD4"),
    ("Permutations and Combinations",
     "CrashCourse Statistics \u2014 Counting (International)", "MUCvUgGfzdo",
     "Khan Academy \u2014 Permutations and Combinations (International)", "Z1zdkcwosD4"),
    ("Binomial Theorem",
     "CrashCourse Statistics \u2014 Binomial Distribution (International)", "wkAjnGmRPVo",
     "Khan Academy \u2014 Binomial Theorem (International)", "WUvTyaaNkzM"),
    ("Sequences and Series",
     "CrashCourse Statistics \u2014 Visualizing Distributions (International)", "5rUVYWfZOb8",
     "Khan Academy \u2014 Arithmetic Sequences and Series (International)", "_cooC3yG_p0"),
    ("Straight Lines",
     "CrashCourse Statistics \u2014 Correlation and Causation (International)", "gq3FPpm2yvA",
     "Khan Academy \u2014 Slope and Equation of a Line (International)", "XMJ72mtMn4Y"),
    ("Conic Sections",
     "CrashCourse Physics \u2014 Lenses (International)", "-w-VTw0tQlE",
     "Khan Academy \u2014 Introduction to Conic Sections (International)", "0A7RR0oy2ho"),
    ("Introduction to Three Dimensional Geometry",
     "CrashCourse Physics \u2014 Geometric Optics (International)", "g-wjP1otQWI",
     "Khan Academy \u2014 3D Geometry Introduction (International)", "riXcZT2ICjA"),
    ("Limits and Derivatives",
     "3Blue1Brown \u2014 Essence of Calculus (International)", "WUvTyaaNkzM",
     "Khan Academy \u2014 Limits Introduction (International)", "riXcZT2ICjA"),
    ("Statistics",
     "CrashCourse Statistics \u2014 Mean Median and Mode (International)", "Mb9BuEkbaHQ",
     "Khan Academy \u2014 Mean Median and Mode Statistics (International)", "k3aKKasOmIw"),
    ("Probability",
     "CrashCourse Statistics \u2014 Basic Probability (International)", "JnoBjHz2dtw",
     "Khan Academy \u2014 Basic Probability (International)", "uzkc-qNVoOk"),
]

g11s = src.find("GRADE_11_RESOURCES: dict")
g11e = src.find("\n# \u2500\u2500 Grade-aware resource lookup", g11s)
block = src[g11s:g11e]

changed = 0
for chap, s0t, s0id, s1t, s1id in G11_MATH:
    ck = re.escape(chap)
    pat = r'("' + ck + r'":\s*\[)(\s*\{[^}]*\},)(\s*\{[^}]*\},?)(\s*\])'
    s0 = '{"title": "' + s0t + '", "type": "youtube", "url": "https://www.youtube.com/watch?v=' + s0id + '"}'
    s1 = '{"title": "' + s1t + '", "type": "youtube", "url": "https://www.youtube.com/watch?v=' + s1id + '"}'
    repl = '"' + chap + '": [\n            ' + s0 + ',\n            ' + s1 + ',\n        ]'
    new_block, n = re.subn(pat, repl, block, count=1)
    if n:
        block = new_block
        changed += 1
        print(f"  fixed: {chap}")
    else:
        print(f"  SKIP: {chap}")

src = src[:g11s] + block + src[g11e:]
with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nGrade 11 Math: {changed}/14 chapters updated with CrashCourse/3B1B")

# Verify
import importlib, app.data.resources as r; importlib.reload(r)
from app.data.resources import GRADE_11_RESOURCES
m = GRADE_11_RESOURCES["Mathematics"]
vedantu_remaining = [(k, v[0]["type"]) for k, v in m.items() if "vedantu" in v[0].get("url", "").lower()]
print(f"Vedantu remaining in Grade 11 Math: {len(vedantu_remaining)}")
for k, t in vedantu_remaining:
    print(f"  {k}: {t}")
