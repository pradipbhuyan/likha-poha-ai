#!/usr/bin/env python3
"""
Prepare GPT-5.5 Chapter-Authoring Prompts + Source PDFs (local bundle)
=========================================================================
See docs/GPT55_CHAPTER_AUTHORING_PROMPT.md for the full prompt design and
workflow this script prepares the inputs for.

For a given grade/subject, this script:
  1. Extracts the full text of each chapter's source NCERT PDF.
  2. Fills in the GPT-5.5 chapter-authoring prompt template with that text.
  3. Writes one ready-to-paste .txt prompt file per chapter, AND copies the
     original source PDF alongside it, into a single local output folder
     (default: ~/Downloads/GPT55_Prompts_<Grade>_<Subject>/).

Nothing here calls any LLM — this only prepares the exact inputs the user
will manually paste into a GPT-5.5 chat session (per Condition 3/4: no
free-tier LLM, and the actual generation step stays a manual, human-
initiated action).

Usage:
    cd backend
    python3 scripts/prepare_gpt55_prompts.py --grade "Grade 9" --subject Science
    python3 scripts/prepare_gpt55_prompts.py --grade "Grade 9" --subject Science --output-dir ~/Desktop/GPT55_Prompts
"""

from __future__ import annotations

import argparse
import re
import sys
import shutil
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── Book code -> (subject, PDF folder) map for locally available RAG DB PDFs ──
# Grade 9 Science lives in "RAG DB/Science/" with book code "iesc1",
# chapters iesc101.pdf .. iesc113.pdf (13 chapters), matching CBSE_9["Science"]
# order in backend/app/data/syllabus.py exactly.
BOOK_SOURCES = {
    ("Grade 9", "Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Science",
        "book_code": "iesc1",
        "num_chapters": 13,
        "subject_class": "science_or_maths",
    },
    # Grade 10 Maths lives in "RAG DB/Grade_10/Maths/" with book code
    # "jemh1", chapters jemh101.pdf .. jemh114.pdf (14 chapters) — this is
    # the NCERT Grade 10 Maths book, already RAG-uploaded (rag_documents
    # ids 260-273 confirmed as "Chapter 1: Real Numbers" .. "Chapter 14:
    # Probability"). Grade 10's syllabus.py currently only has a
    # placeholder ("Uploaded Book Content") entry, so get_chapter_list()
    # falls back to CHAPTER_NAME_OVERRIDES below instead of syllabus.py
    # for this grade/subject.
    ("Grade 10", "Maths"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Grade_10" / "Maths",
        "book_code": "jemh1",
        "num_chapters": 14,
        "subject_class": "science_or_maths",
    },
    # Grade 10 Science lives in "RAG DB/Grade_10/Science/" with book code
    # "jesc1", chapters jesc101.pdf .. jesc113.pdf (13 chapters) — matches
    # rag_documents ids 274-286 ("Chapter 1: Chemical Reactions and
    # Equations" .. "Chapter 13: Our Environment"). Same syllabus.py
    # placeholder situation as Maths above — see CHAPTER_NAME_OVERRIDES.
    ("Grade 10", "Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Grade_10" / "Science",
        "book_code": "jesc1",
        "num_chapters": 13,
        "subject_class": "science_or_maths",
    },
    # Grade 9 Maths lives in "RAG DB/Maths/" with book code "iemh1",
    # chapters iemh101.pdf .. iemh108.pdf (8 chapters), matching CBSE_9["Maths"]
    # order in backend/app/data/syllabus.py exactly.
    ("Grade 9", "Maths"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Maths",
        "book_code": "iemh1",
        "num_chapters": 8,
        "subject_class": "science_or_maths",
    },
    # Grade 9 Social Science lives in "RAG DB/Social Science/" with book
    # code "iest1", chapters iest101.pdf .. iest109.pdf (9 chapters),
    # matching CBSE_9["Social Science"] order in backend/app/data/syllabus.py
    # exactly (Understanding Society: India and Beyond — NCF-SE 2023,
    # first edition June 2026: Geography, History, Political Science,
    # Economics). subject_class = "humanities_or_language" enforces
    # strict PDF-only grounding — no external facts, no invented examples.
    ("Grade 9", "Social Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Social Science",
        "book_code": "iest1",
        "num_chapters": 9,
        "subject_class": "humanities_or_language",
    },
    # Grade 9 English lives in "RAG DB/English/" with book code "iebe1",
    # chapters iebe101.pdf .. iebe108.pdf (8 chapters), matching the first
    # 8 entries of CBSE_9["English"] in backend/app/data/syllabus.py
    # exactly (Kaveri — NCF-SE 2023, first edition January 2026). The
    # trailing "Grammar"/"Writing Skills"/"Reading Comprehension" syllabus
    # entries have no dedicated chapter PDF, so num_chapters=8 stops the
    # loop before them. subject_class = "humanities_or_language" enforces
    # strict PDF-only grounding — every fact/quote must trace back to the
    # actual prose/poem text, no invented literary analysis.
    ("Grade 9", "English"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "English",
        "book_code": "iebe1",
        "num_chapters": 8,
        "subject_class": "humanities_or_language",
    },
    # Grade 9 Hindi lives in "RAG DB/Hindi/" with book code "ihga1",
    # chapters ihga101.pdf .. ihga112.pdf (12 chapters), matching
    # CBSE_9["Hindi"] order in backend/app/data/syllabus.py exactly
    # (गंगा / Ganga — NCF-SE 2023). subject_class =
    # "humanities_or_language" enforces strict PDF-only grounding — every
    # fact/quote must trace back to the actual prose/poem text.
    # content_language="hi" makes the 7 lesson section headings (## What
    # you will learn, etc.) render in Hindi instead of English — see
    # HEADING_SETS below. Fixes user report: "why Hindi chapters are
    # written in English?" — the lesson BODY text was already correctly
    # grounded in Hindi (from the Hindi PDF), but the structural headings
    # were hardcoded English in the prompt template regardless of subject.
    ("Grade 9", "Hindi"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Hindi",
        "book_code": "ihga1",
        "num_chapters": 12,
        "subject_class": "humanities_or_language",
        "content_language": "hi",
    },
    # ── Grade 5 and Grade 6 books (added 2026-07-29) ─────────────────────
    # PDFs supplied locally under ~/Downloads/Class <N> - <Subject>/ with
    # each subject's own book code + 2-digit chapter numbering, matching
    # rag_documents ids 495-600 / 900-901 / 1016 exactly (already-uploaded
    # RAG content) — verified chapter names and counts directly against
    # rag_documents before adding these entries (see
    # docs/GPT55_LESSON_UPDATE_STATUS.md for the verification query).
    # None of Grade 5/6's syllabus.py entries have real chapter lists yet
    # (same placeholder situation as Grade 10), so every one of these
    # needs a CHAPTER_NAME_OVERRIDES entry below.
    ("Grade 5", "English"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 5 - English",
        "book_code": "eesa1",
        "num_chapters": 10,
        "subject_class": "humanities_or_language",
    },
    ("Grade 5", "Hindi"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 5 - Hindi",
        "book_code": "ehve1",
        "num_chapters": 12,
        "subject_class": "humanities_or_language",
        "content_language": "hi",
    },
    ("Grade 5", "Maths"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 5 - Maths",
        "book_code": "eemm1",
        "num_chapters": 15,
        "subject_class": "science_or_maths",
    },
    ("Grade 5", "EVS"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 5 - World Around Us",
        "book_code": "eeev1",
        "num_chapters": 10,
        "subject_class": "science_or_maths",
    },
    ("Grade 6", "English"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 6 - English",
        "book_code": "fepr1",
        "num_chapters": 5,
        "subject_class": "humanities_or_language",
    },
    ("Grade 6", "Hindi"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 6 - Hindi",
        "book_code": "fhml1",
        "num_chapters": 13,
        "subject_class": "humanities_or_language",
        "content_language": "hi",
    },
    ("Grade 6", "Maths"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 6 - Maths",
        "book_code": "fegp1",
        "num_chapters": 10,
        "subject_class": "science_or_maths",
    },
    ("Grade 6", "Science"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 6 - Science",
        "book_code": "fecu1",
        "num_chapters": 12,
        "subject_class": "science_or_maths",
    },
    ("Grade 6", "Social Science"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 6 - Social",
        "book_code": "fees1",
        "num_chapters": 14,
        "subject_class": "humanities_or_language",
    },
    # ── Grade 7 and Grade 8 books (added 2026-07-29) ─────────────────────
    # PDFs live in TWO places: the "RAG DB/Grade_7/" and "RAG DB/Class 8/"
    # folders inside the repo (Grade 7 Maths/Science, Grade 8 all
    # subjects), and ~/Downloads/Class 7 - <Subject>/ for the remaining
    # Grade 7 subjects supplied separately (Hindi, Social Science split
    # across two physical parts). No Grade 7 English PDF exists locally
    # anywhere (confirmed via search) and no rag_documents id-gap PDF was
    # found for it either — that subject is correctly out of scope, same
    # treatment as Grade 5/6 Computer Science. Grade 8 Science/Maths also
    # have 17-30 supplementary NCERT Exemplar chapters in rag_documents
    # (ids 902-932) that are intentionally OUT of scope for this batch —
    # only the primary textbook chapters are covered here, consistent
    # with how Grade 9 Maths's Exemplar chapters were treated in earlier
    # sessions (not prioritized by default).
    ("Grade 7", "Maths"): {
        # Physically split into two NCERT volumes with INDEPENDENT
        # chapter numbering (Part 1: gegp101..gegp108, chapters 1-8; Part
        # 2: gegp201..gegp207, chapters 1-7 again) — uses the new "parts"
        # multi-volume support added to this script this session.
        "parts": [
            {"pdf_dir": REPO_ROOT / "RAG DB" / "Grade_7" / "Maths", "book_code": "gegp1", "num_chapters": 8},
            {"pdf_dir": REPO_ROOT / "RAG DB" / "Grade_7" / "Maths", "book_code": "gegp2", "num_chapters": 7},
        ],
        "subject_class": "science_or_maths",
    },
    ("Grade 7", "Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Grade_7" / "Science",
        "book_code": "gecu1",
        "num_chapters": 12,
        "subject_class": "science_or_maths",
    },
    ("Grade 7", "Hindi"): {
        "pdf_dir": Path.home() / "Downloads" / "Class 7 - Hindi",
        "book_code": "ghml1",
        "num_chapters": 10,
        "subject_class": "humanities_or_language",
        "content_language": "hi",
    },
    ("Grade 7", "Social Science"): {
        # Physically split into two NCERT volumes with INDEPENDENT
        # chapter numbering (Part 1: gees101..gees112, chapters 1-12;
        # Part 2: gees201..gees208, chapters 1-8 again).
        "parts": [
            {"pdf_dir": Path.home() / "Downloads" / "Class 7 - Social Part 1", "book_code": "gees1", "num_chapters": 12},
            {"pdf_dir": Path.home() / "Downloads" / "Class 7 - Social Part 2", "book_code": "gees2", "num_chapters": 8},
        ],
        "subject_class": "humanities_or_language",
    },
    ("Grade 8", "English"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "English",
        "book_code": "hepr1",
        "num_chapters": 5,
        "subject_class": "humanities_or_language",
    },
    ("Grade 8", "Hindi"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "hindi",
        "book_code": "hhml1",
        "num_chapters": 10,
        "subject_class": "humanities_or_language",
        "content_language": "hi",
    },
    ("Grade 8", "Maths"): {
        # Physically split into two NCERT volumes with INDEPENDENT
        # chapter numbering (Part 1: hegp101..hegp107, chapters 1-7;
        # Part 2: hegp201..hegp207, chapters 1-7 again). Only the 14
        # primary-textbook chapters are covered — the 13 supplementary
        # Exemplar chapters (rag_documents ids 902-914) are out of scope.
        "parts": [
            {"pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "Maths-Part1", "book_code": "hegp1", "num_chapters": 7},
            {"pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "Maths-Part2", "book_code": "hegp2", "num_chapters": 7},
        ],
        "subject_class": "science_or_maths",
    },
    ("Grade 8", "Science"): {
        # Only the 13 primary-textbook chapters — the 17 supplementary
        # Exemplar chapters (rag_documents ids 915-932) are out of scope.
        "pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "Science",
        "book_code": "hecu1",
        "num_chapters": 13,
        "subject_class": "science_or_maths",
    },
    ("Grade 8", "Social Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Class 8" / "Social",
        "book_code": "hees1",
        "num_chapters": 7,
        "subject_class": "humanities_or_language",
    },
}

# Grade 10's syllabus.py only has a single placeholder entry
# ("Uploaded Book Content") per subject rather than a real chapter list,
# so get_chapter_list() cannot read the ordered names from there for this
# grade. These overrides give the exact, correctly-ordered chapter names
# (matching the NCERT book's own chapter numbering) for any (grade,
# subject) pair not yet backed by real syllabus.py data. Verified
# directly against the already-uploaded rag_documents.chapter values.
CHAPTER_NAME_OVERRIDES: dict[tuple[str, str], list[str]] = {
    ("Grade 10", "Maths"): [
        "Real Numbers", "Polynomials",
        "Pair of Linear Equations in Two Variables", "Quadratic Equations",
        "Arithmetic Progressions", "Triangles", "Coordinate Geometry",
        "Introduction to Trigonometry", "Some Applications of Trigonometry",
        "Circles", "Areas Related to Circles", "Surface Areas and Volumes",
        "Statistics", "Probability",
    ],
    ("Grade 10", "Science"): [
        "Chemical Reactions and Equations", "Acids, Bases and Salts",
        "Metals and Non-metals", "Carbon and Its Compounds",
        "Life Processes", "Control and Coordination",
        "How do Organisms Reproduce?", "Heredity",
        "Light – Reflection and Refraction",
        "The Human Eye and the Colourful World", "Electricity",
        "Magnetic Effects of Electric Current", "Our Environment",
    ],
    # ── Grade 5 and Grade 6 overrides (added 2026-07-29) ─────────────────
    # Copied verbatim from rag_documents.chapter (ids 495-600 / 900-901 /
    # 1016) so the GPT-5.5 manifest's "chapter" field will match exactly
    # and the student-facing dropdown can find the ingested content —
    # per the documented lesson (see docs/GPT55_LESSON_UPDATE_STATUS.md,
    # "always check rag_documents.chapter for the EXACT chapter string
    # BEFORE ingesting, not syllabus.py's list").
    ("Grade 5", "English"): [
        "1. Papa's Spectacles", "2. Gone with the Scooter", "3. The Rainbow",
        "4. The Wise Parrot", "5. The Frog", "6. What a Tank!",
        "7. Gilli Danda", "8. The Decision of the Panchayat", "9. Vocation",
        "10. Glass Bangles",
    ],
    ("Grade 5", "Hindi"): [
        "1. किरन", "2. न्याय की कु सी", "3. चाँद का कु रता", "4. साङके न",
        "5. सुंदरिया", "6. चतुर चित्रकार", "7. मेरा बचपन",
        "8. काजीरंगा राष्ट्ीय उद्ान की यात्", "9. न्याय", "10. तीन मछलियाँ",
        "11. हमारे ये कलामंदिर", "12. गंगा की कहानी",
    ],
    ("Grade 5", "Maths"): [
        "Chapter 1: We the Travellers — I", "Chapter 2: Fractions",
        "Chapter 3: Angles as Turns", "Chapter 4: We the Travellers — II",
        "Chapter 5: Far and Near", "Chapter 6: The Dairy Farm",
        "Chapter 7: Shapes and Patterns", "Chapter 8: Weight and Capacity",
        "Chapter 9: Coconut Farm", "Chapter 10: Symmetrical Designs",
        "Chapter 11: Grandmother’s Quilt", "Chapter 12: Racing Seconds",
        "Chapter 13: Animal Jumps", "Chapter 14: Maps and Locations",
        "Chapter 15: Data Through Pictures",
    ],
    ("Grade 5", "EVS"): [
        "Chapter 1: Water — The Essence of Life",
        "Chapter 2: Journey of a River", "Chapter 3: The Mystery of Food",
        "Chapter 4: Our School — A Happy Place",
        "Chapter 5: Our Vibrant Country", "Chapter 6: Some Unique Places",
        "Chapter 7: Energy — How Things Work",
        "Chapter 8: Clothes — How Things are Made",
        "Chapter 9: Rhythms of Nature", "Chapter 10: Earth — Our Shared Home",
    ],
    ("Grade 6", "English"): [
        "Unit 1: Fables and Folk Tales", "Unit 2: Friendship",
        "Unit 3: Nurturing Nature", "Unit 4: Sports and Wellness",
        "Unit 5: Culture and Tradition",
    ],
    ("Grade 6", "Hindi"): [
        "1. मातृभूमि", "2. गोल", "3. पहली बूँद", "4. हार की जीत",
        "5. रहीम के दोहे", "6. मेरी माँ", "7. जलाते चलो",
        "8. समरिया और मबहू नृत्य", "9. मैया मैं नमहं माखन खायो",
        "10. परीक्ा", "11. चेतक की वीरता",
        "12. हिंद महासागर में छोटा-सा हिंदुस्ान", "13. पेड़ की बात",
    ],
    ("Grade 6", "Maths"): [
        "Chapter 1 Patterns in Mathematics", "Chapter 2 Lines and Angles",
        "Chapter 3 Number Play", "Chapter 4 Data Handling and Presentation",
        "Chapter 5 Prime Time", "Chapter 6 Perimeter and Area",
        "Chapter 7 Fractions", "Chapter 8 Playing with Constructions",
        "Chapter 9 Symmetry", "Chapter 10 The Other Side of Zero",
    ],
    ("Grade 6", "Science"): [
        "Chapter 1: The Wonderful World of Science",
        "Chapter 2: Diversity in the Living World",
        "Chapter 3: Mindful Eating: A Path to a Healthy Body",
        "Chapter 4: Exploring Magnets",
        "Chapter 5: Measurement of Length and Motion",
        "Chapter 6: Materials Around Us",
        "Chapter 7: Temperature and its Measurement",
        "Chapter 8: A Journey through States of Water",
        "Chapter 9: Methods of Separation in Everyday Life",
        "Chapter 10: Living Creatures: Exploring their Characteristics",
        "Chapter 11: Nature’s Treasures", "Chapter 12: Beyond Earth",
    ],
    ("Grade 6", "Social Science"): [
        "1. Locating Places on the Earth", "2. Oceans and Continents",
        "3. Landforms and Life", "4. Timeline and Sources of History",
        "5. India, That Is Bharat",
        "6. The Beginnings of Indian Civilisation",
        "7. India's Cultural Roots",
        "8. Unity in Diversity, or 'Many in the One'",
        "9. Family and Community",
        "10. Grassroots Democracy — Part 1: Governance",
        "11. Grassroots Democracy — Part 2: Local Government in Rural Areas",
        "12. Grassroots Democracy — Part 3: Local Government in Urban Areas",
        "13. The Value of Work", "14. Economic Activities Around Us",
    ],
    # ── Grade 7 and Grade 8 overrides (added 2026-07-29) ─────────────────
    # Copied verbatim from rag_documents.chapter, re-ordered by each
    # book's own chapter-number label to match the PDF-file numbering
    # exactly (some ids were inserted out of numeric order in the DB —
    # confirmed and corrected via a direct sort-by-chapter-number query,
    # see docs/GPT55_LESSON_UPDATE_STATUS.md for the verification).
    ("Grade 7", "Maths"): [
        # Part 1 (gegp101-108, chapters 1-8)
        "Chapter 1: Large Numbers Around Us", "Chapter 2: Arithmetic Expressions",
        "Chapter 3: A Peek Beyond the Point", "Chapter 4: Expressions using Letter-Numbers",
        "Chapter 5: Parallel and Intersecting Lines", "Chapter 6: Number Play",
        "Chapter 7: A Tale of Three Intersecting Lines", "Chapter 8: Working with Fractions",
        # Part 2 (gegp201-207, chapters 1-7 renumbered)
        "Chapter 1: Geometric Twins", "Chapter 2: Operations with Integers",
        "Chapter 3: Finding Common Ground", "Chapter 4: Another Peek Beyond the Point",
        "Chapter 5: Connecting the Dots…", "Chapter 6: Constructions and Tilings",
        "Chapter 7: Finding the Unknown",
    ],
    ("Grade 7", "Science"): [
        "Chapter 1: The Ever-Evolving World of Science",
        "Chapter 2: Exploring Substances: Acids, Bases and Neutral",
        "Chapter 3: Electricity: Circuits and Their Components",
        "Chapter 4: The World of Metals and Non-metals",
        "Chapter 5: Changes Around Us: Physical and Chemical",
        "Chapter 6: Adolescence: A Stage of Growth and Change",
        "Chapter 7: Heat Transfer in Nature",
        "Chapter 8: Measurement of Time and Motion",
        "Chapter 9: Life Processes in Animals",
        "Chapter 10: Life Processes in Plants",
        "Chapter 11: Light: Shadows and Reflections",
        "Chapter 12: Earth, Moon, and the Sun",
    ],
    ("Grade 7", "Hindi"): [
        "पाठ 1: माँ, कह एक कहानी", "पाठ 2: तीन बुद्धमान",
        "पाठ 3: फ ू ल और काँटा", "पाठ 4: पानी रे पानी",
        "पाठ 5: नहीं होना बीमार", "पाठ 6: िगरधर किवराय की क ुं डिलया",
        "पाठ 7: वषार्-बहार", "पाठ 8: िबरजू महाराज से साक्षाार",
        "पाठ 9: धिधड़या", "पाठ 10: मुीरा का़े पाद",
    ],
    ("Grade 7", "Social Science"): [
        # Part 1 (gees101-112, chapters 1-12) — reordered by chapter
        # number (rag_documents ids 484/485 were inserted out of order:
        # "Chapter 12" before "Chapter 10")
        "Chapter 1: Geographical Diversity of India", "Chapter 2: Understanding the Weather",
        "Chapter 3: Climates of India", "Chapter 4: New Beginnings: Cities and States",
        "Chapter 5: The Rise of Empires", "Chapter 6: The Age of Reorganisation",
        "Chapter 7: The Gupta Era: An Age of Tireless Creativity",
        "Chapter 8: How the Land Becomes Sacred",
        "Chapter 9: From the Rulers to the Ruled: Types",
        "Chapter 10: The Constitution of India — An Introduction",
        "Chapter 11: From Barter to Money", "Chapter 12: Understanding Markets",
        # Part 2 (gees201-208, chapters 1-8 renumbered)
        "Chapter 1: The Story of Indian Farming", "Chapter 2: India and Her Neighbours",
        "Chapter 3: Empires and Kingdoms: 6th to 10th Centuries",
        "Chapter 4: Turning Tides: 11th and 12th Centuries",
        "Chapter 5: India, a Home to Many",
        "Chapter 6: The State, the Government, and You",
        "Chapter 7: Infrastructure: Engine of India’s Development",
        "Chapter 8: Banks and the Magic of Finance",
    ],
    ("Grade 8", "English"): [
        "Unit 1: Wit and Wisdom", "Unit 2: Values and Dispositions",
        "Unit 3: Mystery and Magic", "Unit 4: Environment",
        "Unit 5: Science and Curiosity",
    ],
    ("Grade 8", "Hindi"): [
        "Chapter 1: स्वदेश", "Chapter 2: दो गौरैैयाा", "Chapter 3: एक आशीर्वाद",
        "Chapter 4: हरिद्वार", "Chapter 5: कबीर के दोहे", "Chapter 6: एक टोकरी भर",
        "Chapter 7: मत बाँधो", "Chapter 8: नए मेहेमाान", "Chapter 9: आदमी का अनुपात",
        "Chapter 10: तरुण केे स्वप्न",
    ],
    ("Grade 8", "Maths"): [
        # Part 1 (hegp101-107, chapters 1-7)
        "Chapter 1: A Square and A Cube", "Chapter 2: Power Play",
        "Chapter 3: A Story of Numbers", "Chapter 4: Quadrilaterals",
        "Chapter 5: Number Play", "Chapter 6: We Distribute, Yet Things Multiply",
        "Chapter 7: Proportional Reasoning",
        # Part 2 (hegp201-207, chapters 1-7 renumbered)
        "Chapter 1: Fractions in Disguise", "Chapter 2: The Baudhayana-Pythagoras Theorem",
        "Chapter 3: Proportional Reasoning-2", "Chapter 4: Exploring Some Geometric Themes",
        "Chapter 5: Tales by Dots and Lines", "Chapter 6: Algebra Play", "Chapter 7: Area",
    ],
    ("Grade 8", "Science"): [
        "Chapter 1: Exploring the Investigative World of Science",
        "Chapter 2: The Invisible Living World: Beyond Our Naked Eye",
        "Chapter 3: Interpreting Health: The Ultimate Treasure",
        "Chapter 4: Electricity: Magnetic and Heating Effects",
        "Chapter 5: Exploring Forces", "Chapter 6: Pressure, Winds, Storms, and Cyclones",
        "Chapter 7: Particulate Nature of Matter",
        "Chapter 8: Nature of Matter: Elements, Compounds, and Mixtures",
        "Chapter 9: The Amazing World of Solutes, Solvents, and Solutions",
        "Chapter 10: Light: Mirrors and Lenses", "Chapter 11: Keeping Time with the Skies",
        "Chapter 12: How Nature Works in Harmony",
        "Chapter 13: Our Home: Earth, a Unique Life Sustaining Planet",
    ],
    ("Grade 8", "Social Science"): [
        "Chapter 1: Natural Resources and Their Use",
        "Chapter 2: Reshaping India’s Political Map",
        "Chapter 3: The Rise of the Marathas",
        "Chapter 4: The Colonial Era in India",
        "Chapter 5: Universal Franchise and India’s Electoral System",
        "Chapter 6: The Parliamentary System: Legislature and Executive",
        "Chapter 7: Factors of Production",
    ],
}

# ── Subject-specific prompt guidance (the actual "teach differently per
# subject" logic, not just the binary science_or_maths/humanities_or_
# language split) ─────────────────────────────────────────────────────
# The SUBJECT_CLASS split (science_or_maths vs humanities_or_language)
# only controls whether numeric worked examples are allowed at all. Within
# each class, different subjects still need materially different guidance
# — e.g. Maths worked examples should show full step-by-step algebraic/
# arithmetic work, while Science worked examples should tie back to a
# real experiment/observation, not just a formula plug-in. Similarly,
# English needs literary-device/grammar-specific guidance that doesn't
# apply to Hindi's different literary tradition, and Social Science needs
# guidance that varies further by whether the chapter is History,
# Geography, Political Science, or Economics. This dict adds ONE extra,
# subject-specific paragraph inserted into the prompt (SUBJECT_GUIDANCE
# placeholder) on top of the shared BINDING RULES — replacing the old
# one-size-fits-all template entirely for this section.
SUBJECT_GUIDANCE: dict[str, str] = {
    "Science": (
        "SUBJECT-SPECIFIC GUIDANCE FOR SCIENCE: Ground every explanation in "
        "a real NCERT experiment, activity, or observation wherever the "
        "chapter has one — cite it explicitly (e.g. \"as shown in Activity "
        "1.2\"). Worked examples should walk through the SCIENTIFIC "
        "REASONING (observation -> hypothesis/principle -> "
        "prediction/explanation), not just formula substitution. Where a "
        "chapter includes a numeric formula (e.g. lens formula, Ohm's "
        "law), the worked example may use realistic textbook-style "
        "numbers, but the emphasis must stay on WHY the relationship holds "
        "physically, not just arithmetic. Flag and correct common "
        "conceptual misconceptions specific to this branch of science "
        "(e.g. confusing mass with weight, confusing speed with velocity, "
        "confusing a physical/chemical change) in the Common Mistake "
        "section wherever the chapter content invites that confusion."
    ),
    "Maths": (
        "SUBJECT-SPECIFIC GUIDANCE FOR MATHS: Worked examples MUST show "
        "COMPLETE, correct step-by-step algebraic/arithmetic/geometric "
        "working — every intermediate step, not just the final answer — "
        "exactly as a student would need to show it in a CBSE board exam "
        "answer. Prefer problems adapted from (or directly citing) the "
        "chapter's own NCERT exercise numbers/examples over invented "
        "numbers, but unlike humanities subjects, inventing a NEW numeric "
        "problem that tests the same concept using the same method as an "
        "NCERT example IS acceptable for Maths specifically, as long as "
        "the mathematical method/formula itself is correct and standard "
        "for this chapter (do not invent a new theorem or formula that "
        "does not exist). In the Common Mistake section, flag a genuine, "
        "well-known student error for this specific topic (e.g. sign "
        "errors in the quadratic formula, forgetting to check for "
        "extraneous roots, mixing up which axis is x vs y)."
    ),
    "Social Science": (
        "SUBJECT-SPECIFIC GUIDANCE FOR SOCIAL SCIENCE: This subject spans "
        "History, Geography, Political Science, and Economics — identify "
        "which of these this specific chapter belongs to from "
        "CHAPTER_PDF_TEXT and tailor accordingly: History chapters should "
        "emphasise chronology, cause-and-effect between events, and "
        "primary-source-style evidence (dates, named figures, named "
        "events) exactly as stated in the text; Geography chapters should "
        "emphasise spatial/physical relationships and named "
        "regions/features exactly as stated in the text; Political "
        "Science chapters should emphasise named institutions, "
        "processes, and constitutional provisions exactly as stated in "
        "the text; Economics chapters MAY use real data/tables/numbers "
        "directly from CHAPTER_PDF_TEXT (e.g. actual demand-supply "
        "schedules, actual GDP figures) as this is inherently "
        "quantitative — but only numbers that actually appear in the "
        "source text, never invented ones. Across all four, avoid "
        "importing outside political/historical opinions not present in "
        "the NCERT text — present only what the text states or directly "
        "implies."
    ),
    "English": (
        "SUBJECT-SPECIFIC GUIDANCE FOR ENGLISH: Ground every literary "
        "claim in a specific quote or close paraphrase from "
        "CHAPTER_PDF_TEXT, cited with enough context to be traceable (a "
        "named character/moment, not just \"the text says\"). For prose "
        "chapters, cover characterisation, theme, narrative "
        "technique/point of view, and vocabulary/idiom explanation drawn "
        "directly from the text. For poems, cover imagery, sound devices "
        "(rhyme/rhythm/alliteration if actually present), tone, and the "
        "central idea, again grounded in the actual lines. For grammar/"
        "language-skill chapters bundled into this subject (if the "
        "chapter is about grammar/writing rather than literature), "
        "worked examples should show a complete, correctly-labelled "
        "grammar exercise (e.g. tense transformation, active/passive "
        "voice) using example sentences, which — unlike literature "
        "content — MAY be freshly composed for clarity as long as the "
        "grammar rule itself is standard English grammar, not invented."
    ),
    "Hindi": (
        "SUBJECT-SPECIFIC GUIDANCE FOR HINDI (हिंदी विषय-विशेष निर्देश): "
        "हर साहित्यिक दावे को CHAPTER_PDF_TEXT के किसी विशिष्ट उद्धरण या "
        "प्रसंग से जोड़ें — कोई सामान्य कथन न दें। गद्य (कहानी/निबंध) के "
        "लिए चरित्र-चित्रण, विषयवस्तु, और भाषा-शैली को मूल पाठ से ही "
        "स्पष्ट करें। कविता के लिए बिम्ब, अलंकार (यदि वास्तव में मौजूद "
        "हो), और केंद्रीय भाव को मूल पंक्तियों से जोड़ें। व्याकरण से "
        "संबंधित किसी भी अंश के लिए मानक हिंदी व्याकरण नियम का ही उपयोग "
        "करें, कोई नया नियम न बनाएं।"
    ),
}


def _get_subject_guidance(subject: str) -> str:
    """Return the subject-specific guidance paragraph, or a generic
    fallback if this exact subject name isn't in SUBJECT_GUIDANCE yet."""
    if subject in SUBJECT_GUIDANCE:
        return SUBJECT_GUIDANCE[subject]
    return (
        f"SUBJECT-SPECIFIC GUIDANCE: No custom guidance is configured yet "
        f"for '{subject}' — follow the shared BINDING RULES above and use "
        f"your best judgement as a subject-matter expert teacher for "
        f"'{subject}' specifically."
    )


# Section headings for the 7 fixed sections every lesson step must use.
# English is the default for every subject except Hindi. The inline
# structural markers used INSIDE these sections — "Question:", "Solution:",
# "Step N:", "Final answer:", "Answer:", "Explanation:" — are deliberately
# NOT translated even for Hindi chapters: the frontend
# (frontend/src/components/LessonSections.jsx: getQuestionPrompt,
# parseMcqQuestion) extracts interactive question/answer/explanation boxes
# by matching these exact English words via regex. Translating them would
# silently break the "Want to try this question?" box and Grade 5's
# quick-check flip card for every Hindi lesson. Mixing "Question: <Hindi
# question text>" is intentional and matches how many bilingual CBSE
# resources present content.
HEADING_SETS = {
    "en": {
        "what_you_will_learn": "What you will learn",
        "simple_explanation": "Simple explanation",
        "step_by_step_breakdown": "Step-by-step breakdown",
        "worked_example": "Worked example",
        "common_mistake": "Common mistake",
        "quick_check_question": "Quick check question",
        "summary": "Summary",
    },
    "hi": {
        "what_you_will_learn": "आप क्या सीखेंगे",
        "simple_explanation": "सरल व्याख्या",
        "step_by_step_breakdown": "चरण-दर-चरण विवरण",
        "worked_example": "हल किया गया उदाहरण",
        "common_mistake": "सामान्य भूल",
        "quick_check_question": "शीघ्र जाँच प्रश्न",
        "summary": "सारांश",
    },
}

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE curriculum expert and textbook author. You are
reviewing and rewriting ONE chapter of an NCERT textbook for an AI
tutoring platform. You must act like a strict, subject-matter-accurate
teacher who never invents facts, numbers, or examples that are not
present in — or a direct, standard consequence of — the provided source
text.

{subject_guidance}

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and worked-example number
   you use MUST come from the CHAPTER_PDF_TEXT provided below, or (only if
   SUBJECT_CLASS = "science_or_maths") from a well-known, standard external
   fact that any qualified subject teacher would consider textbook-level
   common knowledge (e.g. the speed of light, standard atomic masses). If
   SUBJECT_CLASS = "humanities_or_language", you may use ONLY facts present
   in CHAPTER_PDF_TEXT — no external knowledge, no paraphrasing that
   changes meaning, no invented examples.
2. NO FABRICATED NUMBERS OR PSEUDO-MATH: Every worked example and
   quick-check question MUST cite/reuse actual activities, experiments,
   or end-of-chapter exercise numbers from CHAPTER_PDF_TEXT wherever the
   chapter has any (e.g. "NCERT Activity 2.2" or "NCERT Q7"). Never invent
   a numeric scenario (e.g. a fictional cell's exact diameter/timing) that
   does not appear in the source text. If SUBJECT_CLASS =
   "humanities_or_language", this rule is absolute and total: NEVER
   invent arithmetic, dates, durations, counts, or any other quantity to
   "calculate" from a story/poem/chapter — e.g. never invent how many
   days a character spent doing something and then compute it with a
   formula. Literature, language, and social-science chapters are
   evaluated through interpretation, evidence-from-text, and reasoning —
   NOT numeric problem-solving. A "worked example" for these subjects
   means: pose a genuine interpretive/analytical question (ideally citing
   a real NCERT exercise), then show a step-by-step REASONING process
   (identify textual evidence → interpret its significance → connect to
   theme/grammar rule/historical concept → state conclusion) — never
   arithmetic steps, never a "Final answer" derived from a calculation.
3. CHAPTER BOUNDARY: Only include content that belongs to THIS chapter.
   Do NOT include content that would more naturally belong to an adjacent
   or different chapter (e.g. don't teach periodic table classification
   inside a "Structure of Atom" chapter). If you are not fully certain a
   topic is genuinely part of this chapter, leave it out.
4. FULL COVERAGE, NO TUNNEL VISION: Your `must_include_keywords` list and
   your 5 lesson steps together MUST proportionally cover EVERY major
   section/sub-heading that appears in CHAPTER_PDF_TEXT — do not let one
   topic (e.g. one type of numerical calculation) dominate 3+ of the 5
   steps while other major sections of the source text get little or no
   coverage.
4a. NO REPETITION ACROSS STEPS (critical for humanities/language, where
   there is no natural numeric progression to force variety): each of the
   5 steps must cover a DIFFERENT slice of CHAPTER_PDF_TEXT and use
   DIFFERENT illustrative quotes/examples/exercise citations from each
   other. Do not restate the same plot summary, the same 2-3 quotations,
   or the same grammar rule in multiple steps just to fill space — if the
   chapter's content is genuinely thin for a given step, write a SHORTER
   step rather than padding it with material already covered in an
   earlier step. Before finalizing, mentally check: would a student
   reading all 5 steps back-to-back feel like step 3 is just repeating
   step 1 in different words? If yes, rewrite step 3 to cover new ground.
5. NO PLACEHOLDER OR VAGUE TEXT: Every "quick_check" question must have a
   complete, correct, specific Answer and Explanation — never leave a
   question unanswered.
6. LANGUAGE LEVEL: Write for the given GRADE level — simple, clear,
   age-appropriate {content_language_name}, but scientifically/factually
   precise. {content_language_note}

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}
SUBJECT_CLASS: {subject_class}   (one of: "science_or_maths" | "humanities_or_language")

CHAPTER_PDF_TEXT:
\"\"\"
{chapter_pdf_text}
\"\"\"

Your task has two parts. Return ONLY a single valid JSON object (no
markdown fences, no commentary before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}",
    "central_question": "<one sentence: what is the single unifying question this chapter answers?>",
    "in_scope_units": [
      "<one string per major section/sub-heading actually present in CHAPTER_PDF_TEXT, in the order they appear, each describing what that section covers>"
    ],
    "banned_topics": [
      "<any topic that a lesson on this chapter might mistakenly include but that actually belongs to a DIFFERENT chapter — infer this from context; if you cannot identify any with confidence, return an empty array>"
    ],
    "must_include_keywords": [
      "<15-40 specific terms/names/concepts that MUST appear somewhere across the 5 lesson steps combined, drawn from ALL major sections of CHAPTER_PDF_TEXT, not just one>"
    ],
    "known_pitfalls": [
      {{
        "claim": "<a specific, plausible mistake a non-expert AI or student might make about this chapter's content>",
        "correction": "<the precise correct statement, grounded in CHAPTER_PDF_TEXT>"
      }}
    ],
    "recommended_example_progression": [
      "<a short ordered list of worked-example ideas, each one explicitly citing which NCERT activity/exercise/example it is based on>"
    ],
    "ncert_end_of_chapter_exercises_reference": "<one sentence pointing to the actual end-of-chapter exercise section name/number range found in CHAPTER_PDF_TEXT, if present>"
  }},
  "lessons": {{
    "Concept introduction": "<full markdown lesson content, see FORMAT below>",
    "Core explanation": "<full markdown lesson content, see FORMAT below>",
    "Worked examples": "<full markdown lesson content, see FORMAT below>",
    "Exam-style problems": "<full markdown lesson content, see FORMAT below>",
    "Revision and recap": "<full markdown lesson content, see FORMAT below>"
  }}
}}

FORMAT for each value inside "lessons" (this must be a single markdown
string, using exactly these 7 headings, in this order, WORD-FOR-WORD as
given — do not translate or reword them):

# <Step Title>: <Chapter Name>

## {h_what_you_will_learn}
<2-4 sentences>

## {h_simple_explanation}
<a short, plain-language paragraph introducing the core idea(s) for this step>

## {h_step_by_step_breakdown}
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
  (as many bullet points as needed to cover this step's share of the chapter)

## {h_worked_example}
{worked_example_format_note}

## {h_common_mistake}
<one specific, plausible misconception and its correction>

## {h_quick_check_question}
Question: <a specific question>
Answer: <the correct, complete answer>
Explanation: <why this is correct>

## {h_summary}
- <bullet 1>
- <bullet 2>
- <bullet 3>
(3-6 bullets recapping this step's key points)

IMPORTANT: keep the literal English words "Question:", "Answer:", and
"Explanation:" exactly as shown above (in the Quick check section) even
when {content_language_name} is not English — only the surrounding
sentence content should be written in {content_language_name}. The
platform's UI extracts interactive question/answer boxes by matching
these exact English marker words. Follow the Worked example section's
format exactly as specified above for this SUBJECT_CLASS.

IMPORTANT: split the chapter content across the 5 steps so that, combined,
they cover the WHOLE of CHAPTER_PDF_TEXT roughly proportionally to how
much space each major section takes in the original text — do NOT let any
single topic dominate more than 1-2 of the 5 steps.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract full text from a PDF using pdfplumber."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)


def get_chapter_list(grade: str, subject: str) -> list[str]:
    """Load the ordered chapter list for a grade/subject.

    Prefers syllabus.py, but falls back to CHAPTER_NAME_OVERRIDES for
    grade/subject pairs where syllabus.py only has a placeholder entry
    (e.g. Grade 10, which currently just has "Uploaded Book Content").
    """
    override_key = (grade, subject)
    if override_key in CHAPTER_NAME_OVERRIDES:
        return list(CHAPTER_NAME_OVERRIDES[override_key])

    from app.data.syllabus import SYLLABUS  # noqa: PLC0415
    try:
        subjects = SYLLABUS[grade]["CBSE"]
        return list(subjects[subject])
    except KeyError as e:
        raise ValueError(f"Could not find chapter list for {grade}/{subject} in syllabus.py: {e}")


def _resolve_pdf_path_for_chapter(source_cfg: dict, chapter_index_1based: int) -> Path:
    """Return the source PDF path for the i-th chapter (1-based) of a
    book, supporting BOTH the simple single-part shape
    ({pdf_dir, book_code, num_chapters}) and the multi-part shape
    ({parts: [{pdf_dir, book_code, num_chapters}, ...]}) used by NCERT
    books physically split into two volumes (e.g. Grade 7 Maths Part 1/2,
    Grade 7 Social Science Part 1/2, Grade 8 Maths Part 1/2) where each
    part restarts its own chapter numbering (e.g. Part 1 has
    <code1>01..08, Part 2 has <code2>01..07 — NOT a continuous 01..15)."""
    if "parts" in source_cfg:
        remaining = chapter_index_1based
        for part in source_cfg["parts"]:
            if remaining <= part["num_chapters"]:
                return part["pdf_dir"] / f"{part['book_code']}{remaining:02d}.pdf"
            remaining -= part["num_chapters"]
        raise IndexError(
            f"chapter index {chapter_index_1based} exceeds total parts chapter count"
        )
    pdf_dir = source_cfg["pdf_dir"]
    book_code = source_cfg["book_code"]
    return pdf_dir / f"{book_code}{chapter_index_1based:02d}.pdf"


def _total_num_chapters(source_cfg: dict) -> int:
    if "parts" in source_cfg:
        return sum(part["num_chapters"] for part in source_cfg["parts"])
    return source_cfg["num_chapters"]


def run(grade: str, subject: str, output_dir: Path, limit: int | None) -> None:
    key = (grade, subject)
    if key not in BOOK_SOURCES:
        print(f"ERROR: no BOOK_SOURCES entry configured for {grade}/{subject}.")
        print(f"       Configured combinations: {list(BOOK_SOURCES.keys())}")
        sys.exit(1)

    source_cfg = BOOK_SOURCES[key]
    num_chapters = _total_num_chapters(source_cfg)
    subject_class = source_cfg["subject_class"]
    content_language = source_cfg.get("content_language", "en")
    headings = HEADING_SETS.get(content_language, HEADING_SETS["en"])
    if content_language == "hi":
        content_language_name = "Hindi (हिंदी)"
        content_language_note = (
            "Every heading, sentence, question, answer, and explanation in "
            "the lesson body must be written in Hindi (Devanagari script), "
            "matching the language of CHAPTER_PDF_TEXT — do not write any "
            "part of the lesson body in English."
        )
    else:
        content_language_name = "English"
        content_language_note = ""

    # The "Worked example" section's internal structure depends entirely
    # on subject_class — a numeric Question/Solution/Step-1/Step-2/Final-
    # answer format is appropriate for Science/Maths, but forcing that
    # same shape onto literature/language/social-science chapters causes
    # GPT-5.5 to fabricate pseudo-math (e.g. inventing how many days a
    # story character spent doing something, then "calculating" it) —
    # confirmed directly from real generated output. Humanities/language
    # chapters instead get a discursive, evidence-based reasoning format
    # with no arithmetic at all.
    if subject_class == "humanities_or_language":
        worked_example_format_note = (
            "Question: <a genuine interpretive/analytical question — ideally "
            "citing a real NCERT exercise number — about the text's meaning, "
            "a character's motivation, a literary device, a grammar rule, or "
            "a historical/social concept from CHAPTER_PDF_TEXT>\n\n"
            "IF this question cites a specific numbered/labelled extract, "
            "exercise, or activity from CHAPTER_PDF_TEXT (e.g. 'NCERT "
            "Critical Reflection I.2(iv)', 'NCERT Q7', 'Exercise 3.2'), you "
            "MUST immediately follow the Question line with a fenced "
            "```extract-ref``` JSON block containing the ACTUAL verbatim "
            "text of that extract/exercise/activity copied from "
            "CHAPTER_PDF_TEXT, in exactly this shape:\n"
            "```extract-ref\n"
            '{"citation": "<the exact citation, e.g. NCERT Critical '
            'Reflection I.2(iv)>", "extract_text": "<the full verbatim '
            "text of that numbered extract/exercise/activity, copied "
            'exactly from CHAPTER_PDF_TEXT — never summarized or '
            'invented>", "note": "<optional: one short line of context, '
            'e.g. the chapter/section this extract is from>"}\n'
            "```\n"
            "This is MANDATORY whenever you cite a specific numbered "
            "source reference — a bare citation with nothing for the "
            "student to refer back to is not acceptable. If the citation "
            "is a general reference to the whole chapter/story (not a "
            "specific numbered extract), the extract-ref block is not "
            "needed.\n\n"
            "Solution:\n"
            "- Step 1: <identify the relevant textual evidence — a direct "
            "quote or specific reference from CHAPTER_PDF_TEXT>\n"
            "- Step 2: <interpret what that evidence means/shows>\n"
            "- Final answer: <the reasoned conclusion, in prose — NEVER a "
            "number derived from invented arithmetic>\n\n"
            "Do NOT invent any quantity (a count, date, duration, age, "
            "distance, etc.) to calculate — every worked example for this "
            "subject must be answered through reasoning and textual evidence, "
            "not arithmetic."
        )
    else:
        worked_example_format_note = (
            "Question: <a question that cites a real NCERT activity/example/"
            "exercise number>\n\n"
            "Solution:\n"
            "- Step 1: ...\n"
            "- Step 2: ...\n"
            "- Final answer: ..."
        )

    # For single-part books, validate the directory exists up front (as
    # before). For multi-part books, each part's directory is checked
    # implicitly when its first chapter's PDF is resolved below.
    if "parts" not in source_cfg and not source_cfg["pdf_dir"].exists():
        print(f"ERROR: PDF source directory not found: {source_cfg['pdf_dir']}")
        sys.exit(1)

    chapters = get_chapter_list(grade, subject)
    if len(chapters) != num_chapters:
        print(f"  [warn] syllabus.py lists {len(chapters)} chapters for {grade}/{subject}, "
              f"but {num_chapters} PDF files are configured. Proceeding with min() of the two.")
    n = min(len(chapters), num_chapters)
    if limit:
        n = min(n, limit)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 prompts for {grade} / {subject}")
    if "parts" in source_cfg:
        for idx, part in enumerate(source_cfg["parts"], start=1):
            print(f"  Source PDFs (part {idx}): {part['pdf_dir']}")
    else:
        print(f"  Source PDFs: {source_cfg['pdf_dir']}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {n}\n")

    manifest_lines = [f"GPT-5.5 Prompt Bundle — {grade} / {subject}", ""]

    for i in range(1, n + 1):
        chapter_name = chapters[i - 1]
        pdf_path = _resolve_pdf_path_for_chapter(source_cfg, i)

        chapter_slug = _slugify(chapter_name)
        safe_prefix = f"{i:02d}_{chapter_slug}"

        print(f"  [{i:02d}] {chapter_name}")
        if not pdf_path.exists():
            print(f"       [skip] source PDF not found: {pdf_path}")
            continue

        try:
            pdf_text = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"       [error] could not extract text from {pdf_path.name}: {e}")
            continue

        if len(pdf_text.strip()) < 200:
            print(f"       [warn] extracted text is suspiciously short ({len(pdf_text)} chars) — check the PDF")

        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade,
            subject=subject,
            chapter=chapter_name,
            subject_class=subject_class,
            chapter_pdf_text=pdf_text,
            content_language_name=content_language_name,
            content_language_note=content_language_note,
            worked_example_format_note=worked_example_format_note,
            subject_guidance=_get_subject_guidance(subject),
            h_what_you_will_learn=headings["what_you_will_learn"],
            h_simple_explanation=headings["simple_explanation"],
            h_step_by_step_breakdown=headings["step_by_step_breakdown"],
            h_worked_example=headings["worked_example"],
            h_common_mistake=headings["common_mistake"],
            h_quick_check_question=headings["quick_check_question"],
            h_summary=headings["summary"],
        )

        prompt_out_path = output_dir / f"{safe_prefix}_PROMPT.txt"
        pdf_out_path = output_dir / f"{safe_prefix}_source.pdf"

        prompt_out_path.write_text(prompt_text, encoding="utf-8")
        shutil.copy2(pdf_path, pdf_out_path)

        print(f"       -> wrote {prompt_out_path.name} ({len(prompt_text):,} chars)")
        print(f"       -> copied {pdf_out_path.name}")

        manifest_lines.append(f"{i:02d}. {chapter_name}")
        manifest_lines.append(f"    prompt: {prompt_out_path.name}")
        manifest_lines.append(f"    source pdf: {pdf_out_path.name}")
        manifest_lines.append(f"    gpt output should be saved as: {chapter_slug}_gpt_output.json")
        manifest_lines.append("")

    manifest_lines.append("-" * 70)
    manifest_lines.append("Next steps for each chapter:")
    manifest_lines.append("  1. Open the *_PROMPT.txt file, copy its full contents.")
    manifest_lines.append("  2. Paste into a GPT-5.5 chat session.")
    manifest_lines.append("  3. Save GPT-5.5's JSON response as <chapter_slug>_gpt_output.json")
    manifest_lines.append("     inside backend/gpt_output/.")
    manifest_lines.append("  4. Run:")
    manifest_lines.append("       cd backend")
    manifest_lines.append("       python3 scripts/ingest_gpt55_chapter_output.py \\")
    manifest_lines.append("           --input gpt_output/<chapter_slug>_gpt_output.json --force")
    manifest_lines.append("     This writes the manifest, seeds all 5 lesson steps into lesson_cache,")
    manifest_lines.append("     and automatically re-runs the Tier A audit for that chapter.")
    manifest_lines.append("")

    manifest_path = output_dir / "00_README_and_index.txt"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"\n  Wrote index/instructions: {manifest_path}")
    print(f"\nDone. {n} chapter prompt(s) + source PDF(s) prepared in:\n  {output_dir}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 chapter-authoring prompts + source PDFs into a local folder"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Science"')
    parser.add_argument(
        "--output-dir", default=None,
        help="Output folder (default: ~/Downloads/GPT55_Prompts_<Grade>_<Subject>)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N chapters")
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = _slugify(args.grade)
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Prompts_{grade_slug}_{subject_slug}"

    run(grade=args.grade, subject=args.subject, output_dir=output_dir, limit=args.limit)


if __name__ == "__main__":
    main()
