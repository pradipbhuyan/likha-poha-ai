#!/usr/bin/env python3
"""
Replace Biology Vedantu (type:website) slot[0] entries with CrashCourse Biology
embeddable YouTube videos (type:youtube).

CrashCourse Biology playlist: PL8dPuuaLjXtPW_ofbxdHNciuLoTRLPMgB (48 videos)
Index mapping (0=Preview, 1=#1, 2=#2, ...):
  1  tZE_fQFK8EY  #1  The Science of Biology
  4  cjR5zPrVjTc  #4  Biological Molecules
  5  aO3Yp45zmw8  #5  The Cell
  6  yGYnwMSflBU  #6  Eukaryopolis (Animal Cells)
  8  Y1mPWVzaGQY  #8  ATP & Respiration
  9  HsAUGbUgx6Y  #9  Photosynthesis
 10  IALw687nswo  #10 Cell Division
 18  TmNHk7kIxr8  #18 Natural Selection / Classification
 19  y7raEBOvLwU  #19 Taxonomy
 24  9Ia8zH-qMZw  #24 Plant Cells
 25  p15KSbNxb28  #25 Vascular Plants
 29  skPOXcVvS5c  #29 Simple Animals
 30  pj1oFx42d48  #30 Complex Animals
 31  YnJPbphsoMY  #31 Circulatory & Respiratory Systems
 35  j6YaOqKORYY  #35 Nervous System
 36  6ulXau2HyHg  #36 Hormones / Endocrine
"""
import re

FILE = "/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py"

with open(FILE, encoding="utf-8") as f:
    src = f.read()

# (chapter_key, cc_title, cc_video_id, slot1_title, slot1_id)
FIXES = [
    ("The Living World",
     "CrashCourse Biology — The Science of Biology (International)",
     "tZE_fQFK8EY",
     "Kurzgesagt — What Is Life How Does It Work (International)", "QOCaacO8wus"),
    ("Biological Classification",
     "CrashCourse Biology — Taxonomy: Life's Filing System (International)",
     "y7raEBOvLwU",
     "Khan Academy — Taxonomy and Classification (International)", "mrheet-2osg"),
    ("Plant Kingdom",
     "CrashCourse Biology — Vascular Plants (International)",
     "p15KSbNxb28",
     "Kurzgesagt — How Evolution Works (International)", "hOfRN0KihOU"),
    ("Animal Kingdom",
     "CrashCourse Biology — Complex Animals (International)",
     "pj1oFx42d48",
     "Kurzgesagt — The Immune System Explained (International)", "lXfEK8G8CUI"),
    ("Cell: The Unit of Life",
     "CrashCourse Biology — The Cell (International)",
     "aO3Yp45zmw8",
     "Khan Academy — Cell Structure and Function (International)", "7FN1NBoV2u0"),
    ("Biomolecules",
     "CrashCourse Biology — Biological Molecules (International)",
     "cjR5zPrVjTc",
     "Khan Academy — Macromolecules Proteins Carbs Lipids (International)", "HGg_WiaSr4U"),
    ("Cell Cycle and Cell Division",
     "CrashCourse Biology — Cell Division (International)",
     "IALw687nswo",
     "Khan Academy — Mitosis and Cell Division (International)", "U5vAO_f2LDQ"),
    ("Photosynthesis in Higher Plants",
     "CrashCourse Biology — Photosynthesis (International)",
     "HsAUGbUgx6Y",
     "Khan Academy — Photosynthesis Overview (International)", "-rsYk4eCKnA"),
    ("Respiration in Plants",
     "CrashCourse Biology — ATP and Respiration (International)",
     "Y1mPWVzaGQY",
     "Khan Academy — Cellular Respiration Overview (International)", "ArmlWtDnuys"),
    ("Breathing and Exchange of Gases",
     "CrashCourse Biology —
