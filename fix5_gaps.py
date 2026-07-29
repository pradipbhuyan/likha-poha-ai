#!/usr/bin/env python3
"""Add missing Chemistry (5) and Biology (9) chapters to GRADE_11_RESOURCES."""
import re

FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, encoding="utf-8") as f:
    src = f.read()

g11s = src.find("GRADE_11_RESOURCES: dict")
g11e = src.find("\n# ── Grade-aware resource lookup", g11s)
block = src[g11s:g11e]


def make_entry(key, s0_title, s0_id, s1_title, s1_id):
    s0 = '{"title": "' + s0_title + '", "type": "youtube", "url": "https://www.youtube.com/watch?v=' + s0_id + '"}'
    s1 = '{"title": "' + s1_title + '", "type": "youtube", "url": "https://www.youtube.com/watch?v=' + s1_id + '"}'
    return ('        "' + key + '": [\n'
            '            ' + s0 + ',\n'
            '            ' + s1 + ',\n'
            '        ],\n')


# ── Chemistry gaps ────────────────────────────────────────────────────────────
# CC Chemistry playlist IDs:
#  7 AN4KifV12DA  Electron Configuration
#  8 ANi709MYnWg  The Nucleus
# 14 GIPrsWuSkQc  Intermolecular Forces (H-bonding)
# 26 BqQJPCdmIp8  Oxidation States / element groups
# 46 aLuSi_6Ol8M  Big Questions (last episode)

chem_new = ""
# Hydrogen - H-bonding and intermolecular forces key topic
chem_new += make_entry(
    "Hydrogen",
    "CrashCourse Chemistry — Intermolecular Forces (International)", "GIPrsWuSkQc",
    "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0")
# The s-Block Elements
chem_new += make_entry(
    "The s-Block Elements",
    "CrashCourse Chemistry — Electron Configuration (International)", "AN4KifV12DA",
    "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0")
# The p-Block Elements
chem_new += make_entry(
    "The p-Block Elements",
    "CrashCourse Chemistry — The Nucleus (International)", "ANi709MYnWg",
    "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0")
# Environmental Chemistry
chem_new += make_entry(
    "Environmental Chemistry",
    "CrashCourse Chemistry — Big Questions in Chemistry (International)", "aLuSi_6Ol8M",
    "Khan Academy — Periodic Table Trends (International)", "MyBYZJ3Wo_0")
# Fix hyphen-key alias for Organic Chemistry
chem_new += make_entry(
    "Organic Chemistry - Some Basic Principles and Techniques",
    "CrashCourse Chemistry — Organic Chemistry Basics (International)", "CEH3O6l1pbw",
    "Khan Academy — Introduction to Organic Chemistry (International)", "nDV5yWfHKko")

# Insert before Chemistry closing: find '    },\n    "Biology":'
chem_anchor = '    },\n    "Biology": {'
idx = block.find(chem_anchor)
if idx >= 0:
    block = block[:idx] + chem_new + block[idx:]
    print("Chemistry: inserted", chem_new.count('"type":'), "new entries")
else:
    print("ERROR: Chemistry anchor not found")

# ── Biology gaps ──────────────────────────────────────────────────────────────
# CC Biology playlist IDs (PL8dPuuaLjXtPW_ofbxdHNciuLoTRLPMgB):
#  2 xOLcZMw0hd4  The Chemistry of Life
#  3 rgZhDoPgzK8  Water - Liquid Awesome
#  6 yGYnwMSflBU  Eukaryopolis (cell structure)
#  7 KfHYN6tZnpU  Membranes & Transport
# 11 2TSIUt-lHyo  Meiosis
# 17 YM6Ekb5De2o  More Transcription
# 22 V66WBvI7Ufw  Taxonomy
# 24 9Ia8zH-qMZw  Plant Cells
# 26 62cN8Z5Velo  Non-Vascular Plants
# 28 -ZRsLhaukn8  Simple Animals / Organisation
# 32 9zwq8N4Ufd8  The Digestive System
# 33 4YNDB_zSzfE  The Musculoskeletal System
# 34 j6YaOqKORYY  The Immune System (reuse)

bio_new = ""
# Morphology of Flowering Plants
bio_new += make_entry(
    "Morphology of Flowering Plants",
    "CrashCourse Biology — Plant Cells (International)", "9Ia8zH-qMZw",
    "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA")
# Anatomy of Flowering Plants
bio_new += make_entry(
    "Anatomy of Flowering Plants",
    "CrashCourse Biology — Non-Vascular Plants (International)", "62cN8Z5Velo",
    "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA")
# Structural Organisation in Animals
bio_new += make_entry(
    "Structural Organisation in Animals",
    "CrashCourse Biology — Eukaryopolis (International)", "yGYnwMSflBU",
    "Khan Academy — Cell Structure and Function (International)", "7FN1NBoV2u0")
# Transport in Plants
bio_new += make_entry(
    "Transport in Plants",
    "CrashCourse Biology — Membranes and Transport (International)", "KfHYN6tZnpU",
    "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA")
# Mineral Nutrition
bio_new += make_entry(
    "Mineral Nutrition",
    "CrashCourse Biology — Water Liquid Awesome (International)", "rgZhDoPgzK8",
    "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA")
# Plant Growth and Development
bio_new += make_entry(
    "Plant Growth and Development",
    "CrashCourse Biology — The Chemistry of Life (International)", "xOLcZMw0hd4",
    "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA")
# Digestion and Absorption
bio_new += make_entry(
    "Digestion and Absorption",
    "CrashCourse Biology — The Digestive System (International)", "9zwq8N4Ufd8",
    "Khan Academy — Cellular Respiration Overview (International)", "ArmlWtDnuys")
