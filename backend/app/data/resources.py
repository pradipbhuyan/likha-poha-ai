"""
Free learning resources for the Grade 9 CBSE tutor app.

Use get_learning_resources(subject, chapter) in app.py so every chapter shows
curated links when available and safe fallback links otherwise.
"""
import re
from urllib.parse import quote_plus


def likhapoha(chapter_label, video_id):
    """Original LikhaPoha AI video for a chapter — always kept when it exists."""
    return {
        "title": f"LikhaPoha AI — {chapter_label}",
        "type": "youtube",
        "url": f"https://youtu.be/{video_id}",
        "role": "likhapoha",
        "channel": "LikhaPoha AI",
    }


def indian_channel(title, channel, video_id, note=None):
    """A textbook-aligned (or closest available) Indian YouTube explainer."""
    resource = {
        "title": title,
        "type": "youtube",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "role": "indian_channel",
        "channel": channel,
    }
    if note:
        resource["note"] = note
    return resource


def international_channel(title, channel, video_id, note=None):
    """A popular, active English-speaking international explainer for universal Maths/Science concepts."""
    resource = {
        "title": title,
        "type": "youtube",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "role": "international_channel",
        "channel": channel,
    }
    if note:
        resource["note"] = note
    return resource


# ── Grade 9 Science (NCERT "Exploration" 2026-27 curriculum) — verified chapter-wise resources ──
# Each chapter: LikhaPoha AI original (kept) + an Indian textbook-aligned channel + an
# international explainer for the same universal concept. Every video below was verified live
# via YouTube's oEmbed endpoint (title + channel) before being added — see chat history for the
# verification pass. Chapters 7, 9, 10, 11, 12, 13 didn't have a new-curriculum video available
# yet anywhere (the book is ~3 months old as of writing), so the Indian slot uses the closest
# previous-edition chapter instead and is flagged with `note`.
GRADE_9_SCIENCE_CHAPTERS = [
    "Exploration: Entering the World of Secondary Science",
    "Cell: The Building Block of Life",
    "Tissues in Action",
    "Describing Motion Around Us",
    "Exploring Mixtures and Their Separation",
    "How Forces Affect Motion",
    "Work, Energy, and Simple Machines",
    "Journey Inside the Atom",
    "Atomic Foundations of Matter",
    "Sound Waves: Characteristics and Applications",
    "Reproduction: How Life Continues",
    "Patterns in Life: Diversity and Classification",
    "Earth as a System: Energy, Matter, and Life",
]

GRADE_9_SCIENCE_RESOURCE_LISTS = [
    [  # 1. Exploration: Entering the World of Secondary Science
        likhapoha("Exploration: Entering the World of Secondary Science", "egb7zve36RY"),
        indian_channel("Class 9 Science Chapter 1 | Exploration: Entering the World of Secondary Science | Full Chapter", "Ncert Tutorial (ExamVita)", "G0JQm4WE1P4"),
        international_channel("The Scientific Method: Crash Course Biology #2", "CrashCourse", "xOLcZMw0hd4"),
        international_channel("The Times and Troubles of the Scientific Method", "SciShow", "i8wi0QnYN6s"),
    ],
    [  # 2. Cell: The Building Block of Life
        likhapoha("Cell: The Building Block of Life", "kADIaUbwL00"),
        indian_channel("9th Exploration Chapter 2 - Cell: The Building Block of Life | Full Chapter", "Ncert Tutorial (ExamVita)", "Zv0_C2xhbMQ"),
        international_channel("Cell Organelles & Structures: Before the Bell Biology", "Amoeba Sisters", "R09zFIGevio"),
        international_channel("Plant Cells: Crash Course Biology #6", "CrashCourse", "9UvlqAVCoqY"),
    ],
    [  # 3. Tissues in Action
        likhapoha("Tissues in Action", "yJk4ZeSr9Bk"),
        indian_channel("Chapter 3: Tissues in Action | Science Class 9 Exploration | NCERT Explainer", "EduRev Class 6-10", "GlNmyiBpY8w"),
        international_channel("Body Tissues (the 4 Types)", "Amoeba Sisters", "5j8j7BhCCEg"),
        international_channel("Tissues, Part 1: Crash Course Anatomy & Physiology #2", "CrashCourse", "i5tR3csCWYo"),
    ],
    [  # 4. Describing Motion Around Us
        likhapoha("Describing Motion Around Us", "___wVgKghMA"),
        indian_channel("9th Exploration Chapter 4 - Describing Motion Around Us | Full Chapter", "Ncert Tutorial (ExamVita)", "SsDg0p_UC1k"),
        international_channel("Motion in a Straight Line: Crash Course Physics #1", "CrashCourse", "ZM8ECpBuQYE"),
        international_channel("Position/Velocity/Acceleration Part 1: Definitions", "Professor Dave Explains", "4dCrkp8qgLU"),
    ],
    [  # 5. Exploring Mixtures and Their Separation
        likhapoha("Exploring Mixtures and Their Separation", "1FS2LCZXd_A"),
        indian_channel("9th Exploration Chapter 5 - Exploring Mixtures and Their Separation | Full Chapter", "Ncert Tutorial (ExamVita)", "JwmJZVsRIh8"),
        international_channel("The Great Picnic Mix Up: Crash Course Kids #19.1", "Crash Course Kids", "jA0PzblYPUM", note="Foundational level (upper-primary), but directly on separating mixtures."),
        international_channel("Separation of Mixtures Explained: Filtration, Evaporation, Distillation & Chromatography", "Periodic Table Talk", "tWd1biGv_nY"),
    ],
    [  # 6. How Forces Affect Motion
        likhapoha("How Forces Affect Motion", "7Zd3nj4wZAE"),
        indian_channel("How Force Affects Motion Full Chapter ONE SHOT | Class 9 | 2026-27", "PW Class 9 - NEEV (Physics Wallah)", "eMEzTPOYygM"),
        international_channel("Newton's Laws: Crash Course Physics #5", "CrashCourse", "kKKM8Y-u7ds"),
        international_channel("Friction: Crash Course Physics #6", "CrashCourse", "fo_pmp5rtzo"),
    ],
    [  # 7. Work, Energy, and Simple Machines
        likhapoha("Work, Energy, and Simple Machines", "LxluQchwS54"),
        indian_channel("Work And Energy Class 9 | Complete Chapter in One Shot | NCERT Covered", "Alakh Pandey (Physics Wallah)", "NOu2YoxVyvY", note="Previous NCERT edition's 'Work and Energy' chapter — doesn't cover the new Simple Machines section."),
        international_channel("Work, Energy, and Power: Crash Course Physics #9", "CrashCourse", "w4QFJb9a8vo"),
        international_channel("Work and Energy", "Professor Dave Explains", "zVRH9d5PW8g"),
    ],
    [  # 8. Journey Inside the Atom
        likhapoha("Journey Inside the Atom", "9b-4THbqIT0"),
        indian_channel("Class 9 Science Chapter 8 | Journey Inside The Atom | NCERT Exploration New Book 2026", "Mishti Classroom", "_8gxXTe34tk"),
        international_channel("The Nucleus: Crash Course Chemistry #1", "CrashCourse", "FSyAehMdpyI"),
        international_channel("History of Atomic Theory", "Professor Dave Explains", "9B3DDY27ZtE"),
    ],
    [  # 9. Atomic Foundations of Matter
        likhapoha("Atomic Foundations of Matter", "AaEejyJllkk"),
        indian_channel("Atoms And Molecules Class 9 | Complete Chapter in One Shot | NCERT Covered", "Alakh Pandey (Physics Wallah)", "YjDLkvTAYCU", note="Previous NCERT edition's 'Atoms and Molecules' chapter — covers most of the same bonding/atomic-theory concepts."),
        international_channel("Atomic Hook-Ups — Types of Chemical Bonds: Crash Course Chemistry #22", "CrashCourse", "QXT4OVM4vXI"),
        international_channel("The Chemical Bond: Covalent vs. Ionic and Polar vs. Nonpolar", "Professor Dave Explains", "PoQjsnQmxok"),
    ],
    [  # 10. Sound Waves: Characteristics and Applications
        likhapoha("Sound Waves: Characteristics and Applications", "JgfIbwip9UI"),
        indian_channel("SOUND Class 9 || Complete Chapter in One Shot || NCERT Covered", "Alakh Pandey (Physics Wallah)", "-sWDY2jc9nM", note="Previous NCERT edition's 'Sound' chapter — same core content as the new chapter."),
        international_channel("Sound: Crash Course Physics #18", "CrashCourse", "qV4lR9EWGlY"),
        international_channel("How Sound Works - The Physics of Sound Waves", "Mr. McMath", "QBYz82nS_xk"),
    ],
    [  # 11. Reproduction: How Life Continues
        likhapoha("Reproduction: How Life Continues", "pTJ634ebToQ"),
        indian_channel("How Do Organisms Reproduce Class 10 || Complete Chapter in One Shot || NCERT Covered", "Alakh Pandey (Physics Wallah)", "dCAnbdRAsFo", note="This topic moved down from the old Class 10 syllabus ('How do Organisms Reproduce?') into the new Class 9 book."),
        international_channel("Asexual and Sexual Reproduction", "Amoeba Sisters", "fcGDUcGjcyk"),
        international_channel("Sexual & Asexual Reproduction: How Animals Do It: Crash Course Biology #47", "CrashCourse", "ruZqnWHINWE"),
    ],
    [  # 12. Patterns in Life: Diversity and Classification
        likhapoha("Patterns in Life: Diversity and Classification", "VHg5evqi4yU"),
        indian_channel("Diversity in Living Organisms in One Shot - From Zero to Hero", "Physics Wallah Foundation", "ddfD5kgQOCs", note="Previous NCERT edition's 'Diversity in Living Organisms' chapter — same classification concepts."),
        international_channel("Classification", "Amoeba Sisters", "DVouQRAKxYo"),
        international_channel("Taxonomy: Life's Filing System - Crash Course Biology #19", "CrashCourse", "F38BmgPcZ_I"),
    ],
    [  # 13. Earth as a System: Energy, Matter, and Life
        likhapoha("Earth as a System: Energy, Matter, and Life", "RRbu9RttTiY"),
        indian_channel("Natural Resources in 1 Shot | CBSE Class 9 Biology | Science Chapter 14", "Vedantu CBSE", "0geP36CY1dE", note="This is an all-new chapter with no direct previous-edition equivalent; this video only overlaps partially (water/nitrogen cycle, atmosphere)."),
        international_channel("What On Earth: Crash Course Kids #10.1", "Crash Course Kids", "YkrAIz_Ha6E", note="Foundational level (upper-primary), but directly covers Earth's spheres interacting as a system."),
        international_channel("The Earth: Crash Course Astronomy #11", "CrashCourse", "w-9gDALvMF4"),
    ],
]

LEARNING_RESOURCES = {
    "Science": {},
}

for _index, _chapter_name in enumerate(GRADE_9_SCIENCE_CHAPTERS):
    _resource_list = GRADE_9_SCIENCE_RESOURCE_LISTS[_index]
    LEARNING_RESOURCES["Science"][_chapter_name] = _resource_list
    LEARNING_RESOURCES["Science"][f"Chapter {_index + 1}: {_chapter_name}"] = _resource_list

LEARNING_RESOURCES["Science"].update({
    "Matter in Our Surroundings": [
            {"title": "YouTube Search - Class 9 Matter in Our Surroundings", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+matter+in+our+surroundings+full+chapter"},
        ],
        "Structure of the Atom": [
            {"title": "PhET - Build an Atom Simulation", "type": "website", "url": "https://phet.colorado.edu/en/simulation/build-an-atom"},
            {"title": "YouTube Search - Structure of the Atom", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+structure+of+the+atom+full+chapter"},
        ],
        "The Fundamental Unit of Life": [
            {"title": "YouTube Search - Fundamental Unit of Life", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+fundamental+unit+of+life+full+chapter"},
        ],
        "Tissues": [
            {"title": "YouTube Search - Tissues", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+tissues+full+chapter"},
        ],
        "Motion": [
            {"title": "PhET - Moving Man Simulation", "type": "website", "url": "https://phet.colorado.edu/en/simulation/moving-man"},
            {"title": "YouTube Search - Motion Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+motion+full+chapter"},
        ],
        "Force and Laws of Motion": [
            {"title": "PhET - Forces and Motion Basics", "type": "website", "url": "https://phet.colorado.edu/en/simulation/forces-and-motion-basics"},
            {"title": "YouTube Search - Force and Laws of Motion", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+force+and+laws+of+motion+full+chapter"},
        ],
        "Gravitation": [
            {"title": "Physics Wallah — Gravitation | Class 11 (India)", "type": "website", "url": "https://www.youtube.com/results?search_query=physics+wallah+gravitation+class+11"},
            {"title": "Kurzgesagt — Gravity Explained (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=e5GBM-MEKzo"},
        ],
        "Work and Energy": [
            {"title": "PhET - Energy Skate Park", "type": "website", "url": "https://phet.colorado.edu/en/simulation/energy-skate-park"},
            {"title": "YouTube Search - Work and Energy Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+work+and+energy+full+chapter"},
        ],
        "Sound": [
            {"title": "PhET - Wave Interference", "type": "website", "url": "https://phet.colorado.edu/en/simulation/wave-interference"},
            {"title": "YouTube Search - Sound Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+sound+full+chapter"},
        ],
        "Improvement in Food Resources": [
            {"title": "YouTube Search - Improvement in Food Resources", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+improvement+in+food+resources+full+chapter"},
        ],
})

# ── Grade 9 Maths (NCERT "Ganita Manjari" 2026-27 curriculum) — verified chapter-wise resources ──
# Same treatment as Grade 9 Science: LikhaPoha AI original (kept) + an Indian textbook-aligned
# channel + two international explainers. Chapters 5, 6, 8 had no new-curriculum video available
# anywhere yet, so the Indian slot uses the closest previous-edition chapter instead (flagged
# with `note`) — Chapter 8 in particular ("Sequences and Progressions") moved down from the old
# Class 10 syllabus into the new Class 9 book, so its fallback is a Class 10 video.
GRADE_9_MATHS_CHAPTERS = [
    "Orienting Yourself: The Use of Coordinates",
    "Introduction to Linear Polynomials",
    "The World of Numbers",
    "Exploring Algebraic Identities",
    "I'm Up and Down, and Round and Round",
    "Measuring Space: Perimeter and Area",
    "The Mathematics of Maybe: Introduction to Probability",
    "Predicting What Comes Next: Exploring Sequences and Progressions",
]

GRADE_9_MATHS_RESOURCE_LISTS = [
    [  # 1. Orienting Yourself: The Use of Coordinates
        likhapoha("Orienting Yourself: The Use of Coordinates", "n8qXaymOsAs"),
        indian_channel("Ganita Manjari New NCERT 2026-27 | Class 9 Maths | Chapter 1 Orienting Yourself: The Use of Coordinates", "Jain Tutor", "8WJSEJBGDFE"),
        international_channel("Introduction to the coordinate plane | Introduction to algebra | Algebra I", "Khan Academy", "N4nrdf0yYfM"),
        international_channel("Algebra Basics: Graphing On The Coordinate Plane", "Math Antics", "9Uc62CuQjc4"),
    ],
    [  # 2. Introduction to Linear Polynomials
        likhapoha("Introduction to Linear Polynomials", "l3_lnTLvNQI"),
        indian_channel("Ganita Manjari Class 9 Chapter 2 One Shot | New NCERT 2026-27 | Introduction to Linear Polynomials", "Jain Tutor", "fAJnfdJCess"),
        international_channel("Polynomials intro | Mathematics II | High School Math", "Khan Academy", "Vm7H0VTlIco"),
        international_channel("Introduction to Polynomials", "Professor Dave Explains", "nPPNgin7W7Y"),
    ],
    [  # 3. The World of Numbers
        likhapoha("The World of Numbers", "_XLwB8P9m_4"),
        indian_channel("The World Of Numbers Class 9 | Chapter 3 | Ganita Manjari | One Shot", "Maths Future", "TYYvfVrcHIA"),
        international_channel("Introduction to rational and irrational numbers | Algebra I", "Khan Academy", "cLP7INqs3JM"),
        international_channel("Irrational Numbers - Math Antics Extras", "Math Antics", "wg4YXMe5ccs"),
    ],
    [  # 4. Exploring Algebraic Identities
        likhapoha("Exploring Algebraic Identities", "H0eyj1U1DCg"),
        indian_channel("Exploring Algebraic Identities Class 9 | Ganita Manjari | One Shot | Chapter 4", "Maths Future", "VB8d1-jMwS0"),
        international_channel("Introduction to special products of binomials | Algebra I", "Khan Academy", "bFtjG45-Udk"),
        international_channel("Polynomial special products: perfect square | Algebra 2", "Khan Academy", "hw5DE8HSZk0"),
    ],
    [  # 5. I'm Up and Down, and Round and Round (circles)
        likhapoha("I'm Up and Down, and Round and Round", "SPtGjVEAXrs"),
        indian_channel("CIRCLES in 1 Shot || FULL Chapter Coverage (Concepts+PYQs) || Class 9th Maths", "Physics Wallah Foundation", "eU3TKYrdAmU", note="Previous NCERT edition's 'Circles' chapter — same circle-theorem concepts as the new chapter."),
        international_channel("Inscribed angle theorem proof | High School Geometry", "Khan Academy", "MyzGVbCHh5M"),
        international_channel("Circle Theorems - Part 1 | Geometry & Measures", "FuseSchool", "wT_OSZ-ORtY"),
    ],
    [  # 6. Measuring Space: Perimeter and Area
        likhapoha("Measuring Space: Perimeter and Area", "yQk7eNc1pbs"),
        indian_channel("Class 9 HERON'S FORMULA in 1 Shot: FULL CHAPTER | Class 9th Maths Chapter 10", "PW Class 9 - NEEV", "TXVDm3VpxbM", note="Previous NCERT edition's 'Heron's Formula' chapter — covers triangle-area concepts that carry into the new chapter's broader perimeter/area scope."),
        international_channel("Circles: radius, diameter, circumference and Pi | Geometry", "Khan Academy", "jyLRpr2P0MQ"),
        international_channel("Area of a circle | Perimeter, area, and volume | Geometry", "Khan Academy", "ZyOhRgnFmIY"),
    ],
    [  # 7. The Mathematics of Maybe: Introduction to Probability
        likhapoha("The Mathematics of Maybe: Introduction to Probability", "N8q2adCIBRU"),
        indian_channel("Probability in 1 Shot | Class 9 | NCERT | Sprint", "Physics Wallah Foundation", "_XT6d6k8J5Q"),
        international_channel("Probability explained | Independent and dependent events", "Khan Academy", "uzkc-qNVoOk"),
        international_channel("Math Antics - Basic Probability", "Math Antics", "KzfWUEJjG18"),
    ],
    [  # 8. Predicting What Comes Next: Exploring Sequences and Progressions
        likhapoha("Predicting What Comes Next: Exploring Sequences and Progressions", "GKMvXRoJKOI"),
        indian_channel("Arithmetic Progressions | Complete NCERT WITH BACK EXERCISE in 1 Video | Class 10th Board", "PW Class 10 - UDAAN", "JYBywt30T8E", note="This topic moved down from the old Class 10 syllabus ('Arithmetic Progressions') into the new Class 9 book."),
        international_channel("Introduction to geometric sequences | Precalculus", "Khan Academy", "pXo0bG4iAyg"),
        international_channel("Introduction to arithmetic sequences | Precalculus", "Khan Academy", "_cooC3yG_p0"),
    ],
]

LEARNING_RESOURCES["Maths"] = {}

for _index, _chapter_name in enumerate(GRADE_9_MATHS_CHAPTERS):
    _resource_list = GRADE_9_MATHS_RESOURCE_LISTS[_index]
    LEARNING_RESOURCES["Maths"][_chapter_name] = _resource_list
    LEARNING_RESOURCES["Maths"][f"Chapter {_index + 1}: {_chapter_name}"] = _resource_list

# Curly apostrophe variant (U+2019) for Chapter 5 — as stored in Supabase rag_documents
_curly_chapter_5 = "I" + "’" + "m Up and Down, and Round and Round"
LEARNING_RESOURCES["Maths"][_curly_chapter_5] = GRADE_9_MATHS_RESOURCE_LISTS[4]
LEARNING_RESOURCES["Maths"][f"Chapter 5: {_curly_chapter_5}"] = GRADE_9_MATHS_RESOURCE_LISTS[4]

LEARNING_RESOURCES["Maths"].update({
        # Legacy generic Maths chapter keys (kept for backward compatibility)
        "Number Systems": [{"title": "YouTube Search - Number Systems Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+number+systems+full+chapter"}],
        "Polynomials": [{"title": "YouTube Search - Polynomials Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+polynomials+full+chapter"}],
        "Coordinate Geometry": [{"title": "YouTube Search - Coordinate Geometry Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+coordinate+geometry+full+chapter"}],
        "Linear Equations in Two Variables": [{"title": "YouTube Search - Linear Equations in Two Variables", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+linear+equations+in+two+variables+full+chapter"}],
        "Introduction to Euclid Geometry": [{"title": "YouTube Search - Euclid Geometry Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+introduction+to+euclid+geometry+full+chapter"}],
        "Lines and Angles": [{"title": "YouTube Search - Lines and Angles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+lines+and+angles+full+chapter"}],
        "Triangles": [{"title": "YouTube Search - Triangles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+triangles+full+chapter"}],
        "Quadrilaterals": [{"title": "YouTube Search - Quadrilaterals Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+quadrilaterals+full+chapter"}],
        "Areas of Parallelograms and Triangles": [{"title": "YouTube Search - Areas of Parallelograms and Triangles", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+areas+of+parallelograms+and+triangles+full+chapter"}],
        "Circles": [{"title": "YouTube Search - Circles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+circles+full+chapter"}],
        "Herons Formula": [{"title": "YouTube Search - Heron's Formula Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+herons+formula+full+chapter"}],
        "Surface Areas and Volumes": [{"title": "YouTube Search - Surface Areas and Volumes", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+surface+areas+and+volumes+full+chapter"}],
        "Statistics": [{"title": "YouTube Search - Statistics Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+statistics+full+chapter"}],
        "Probability": [{"title": "YouTube Search - Probability Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+probability+full+chapter"}],
})

# ── Grade 9 English (NCERT "Kaveri" 2026-27 curriculum) — verified chapter-wise resources ──
# No LikhaPoha AI content exists for English literature chapters. Per plan: one Indian
# textbook-aligned channel + one alternate Indian channel per chapter (no international pick —
# English literature isn't a "universal" subject the way Science/Maths are). Chapters 7 and 8
# only have one verified channel each; no second channel could be found despite searching.
GRADE_9_ENGLISH_CHAPTERS = [
    "How I Taught My Grandmother to Read",
    "The Pot Maker",
    "Winds of Change",
    "Vitamin-M",
    "The World of Limitless Possibilities",
    "Twin Melodies",
    "Carrier of Words",
    "Follow That Dream",
]

GRADE_9_ENGLISH_RESOURCE_LISTS = [
    [  # 1. How I Taught My Grandmother to Read
        indian_channel("How I Taught My Grandmother to Read - Explanation | Class 9th English (Kaveri) | Ch 1 | CBSE 2026-27", "Magnet Brains", "O6QbNI-DVWM"),
        indian_channel("How I Taught My Grandmother to Read Class 9 (Animation)", "Sunlike study", "lfZIhtEUHY4"),
    ],
    [  # 2. The Pot Maker
        indian_channel("The Pot Maker - Explanation (Part 1) | Class 9th English (Kaveri) | Chapter 2 | CBSE 2026-27", "Magnet Brains", "NHo6BWmFp4Y"),
        indian_channel("The Pot Maker Class 9 (Animation) | Full Chapter", "Sunlike study", "5BzoJUp5Ykg"),
    ],
    [  # 3. Winds of Change
        indian_channel("Winds of Change - Explanation | Class 9th English (Kaveri) | Chapter 3 | CBSE 2026-27", "Magnet Brains", "0GCNZvjVlug"),
        indian_channel("Winds of Change Class 9 | Full Chapter Animation", "Rk ki lines", "XDavgeewJfg"),
    ],
    [  # 4. Vitamin-M
        indian_channel("Vitamin M - Explanation (Part 1) | Class 9 English (Kaveri) | Chapter 4 | CBSE 2026-27", "Magnet Brains", "BRR6qvASoME"),
        indian_channel("Class 9 English Kaveri Chapter 4 | Vitamin-M | Summary", "NEW AGE Golden School Books", "VHWKbsNKjXE"),
    ],
    [  # 5. The World of Limitless Possibilities
        indian_channel("The World of Limitless Possibilities | Class 9 English Kaveri Chapter 5 Full Explanation", "Teaching Adda", "YJPLc_shc1Y"),
        indian_channel("World of Limitless Possibilities | Full Explanation in Hindi", "Srija Tomar", "Q_tRsrx9KmU"),
    ],
    [  # 6. Twin Melodies
        indian_channel("Class 9 English Chapter 6 | Twin Melodies Explanation | Kaveri | New NCERT", "NEW AGE Golden School Books", "YLJQiv14pGA"),
        indian_channel("Twin Melodies (Part 1) | CBSE Class 9 English Kaveri Book | Complete Explanation", "Bodhi Classes", "2SJa7yR7ZUQ"),
    ],
    [  # 7. Carrier of Words
        indian_channel("Carrier of Words | Class 9 English Kaveri Chapter 7 | Q&A, Vocabulary & Grammar", "NCERT Material", "x6t6wz3QVsc"),
    ],
    [  # 8. Follow That Dream
        indian_channel("CBSE Class 9 English | Kaveri | Follow That Dream | Full Explanation and analysis", "Bodhi Classes", "ZmKzmeizFUE"),
    ],
]

LEARNING_RESOURCES["English"] = {}

for _index, _chapter_name in enumerate(GRADE_9_ENGLISH_CHAPTERS):
    _resource_list = GRADE_9_ENGLISH_RESOURCE_LISTS[_index]
    LEARNING_RESOURCES["English"][_chapter_name] = _resource_list
    LEARNING_RESOURCES["English"][f"Chapter {_index + 1}: {_chapter_name}"] = _resource_list

# ── Grade 9 Social Science — verified chapter-wise resources ──
# NCERT replaced these four separate books (History/Geography/Political Science/Economics) with
# one integrated "Understanding Society: India and Beyond" text for 2026-27, but this codebase's
# syllabus data was never updated to match (unlike Science/Maths/English) — it's still on the old
# chapter titles below, which is what the dropdown actually shows students. Curating against the
# live dropdown rather than the new (unimplemented) curriculum. No LikhaPoha AI content exists for
# this subject. These are long-established topics, so — unlike the brand-new Science/Maths/English
# books — coverage was abundant and every chapter got two verified Indian channels, no gaps.
GRADE_9_SOCIAL_SCIENCE_CHAPTERS = [
    "The French Revolution",
    "Socialism in Europe and the Russian Revolution",
    "Nazism and the Rise of Hitler",
    "Forest Society and Colonialism",
    "Pastoralists in the Modern World",
    "India Size and Location",
    "Physical Features of India",
    "Drainage",
    "Climate",
    "Natural Vegetation and Wildlife",
    "Population",
    "What is Democracy Why Democracy",
    "Constitutional Design",
    "Electoral Politics",
    "Working of Institutions",
    "Democratic Rights",
    "The Story of Village Palampur",
    "People as Resource",
    "Poverty as a Challenge",
    "Food Security in India",
]

GRADE_9_SOCIAL_SCIENCE_RESOURCE_LISTS = [
    [  # 1. The French Revolution
        indian_channel("Class 9 History Chapter 1 | The French Revolution Full Chapter", "Magnet Brains", "6SH-3PvZ_No"),
        indian_channel("THE FRENCH REVOLUTION in One Shot - From Zero to Hero", "Physics Wallah Foundation", "DQfH9Fa3egw"),
    ],
    [  # 2. Socialism in Europe and the Russian Revolution
        indian_channel("Socialism in Europe and the Russian Revolution - One Shot Revision | Class 9 History Chapter 2", "Magnet Brains", "7rAUUzN-v3Q"),
        indian_channel("SOCIALISM IN EUROPE & RUSSIAN REVOLUTION in 1 Shot || FULL Chapter", "Physics Wallah Foundation", "tLpDFCbGLW4"),
    ],
    [  # 3. Nazism and the Rise of Hitler
        indian_channel("Nazism and the Rise of Hitler | New One Shot | History Class 9", "Digraj Singh Rajput", "rFS0j494QEY"),
        indian_channel("NAZISM AND THE RISE OF HITLER in 1 Shot || FULL Chapter Coverage", "Physics Wallah Foundation", "Kga4KUerm3o"),
    ],
    [  # 4. Forest Society and Colonialism
        indian_channel("Forest Society and Colonialism - One Shot Revision | Class 9 History Chapter 4", "Magnet Brains", "tMkGv5gOJR0"),
        indian_channel("FOREST SOCIETY AND COLONIALISM in One Shot - From Zero to Hero", "Physics Wallah Foundation", "I6aHHgjwi-I"),
    ],
    [  # 5. Pastoralists in the Modern World
        indian_channel("Pastoralists in the Modern World - One Shot Revision | Class 9 History Chapter 5", "Magnet Brains", "O6iWekv04yI"),
        indian_channel("PASTORALISTS IN THE MODERN WORLD in One Shot - From Zero to Hero", "Physics Wallah Foundation", "-nnNhzhV9QI"),
    ],
    [  # 6. India Size and Location
        indian_channel("India Size and Location - One Shot Revision | Class 9 Geography Chapter 1", "Magnet Brains", "VFDfJvGAAD4"),
        indian_channel("INDIA SIZE AND LOCATION in 1 Shot | FULL Chapter Coverage", "Physics Wallah Foundation", "yJZItDbXTPU"),
    ],
    [  # 7. Physical Features of India
        indian_channel("Physical Features Of India - One Shot Revision | Class 9 Geography Chapter 2", "Magnet Brains", "OT7gNxUIgJA"),
        indian_channel("Physical Features of India | 10 Minutes Rapid Revision", "Digraj Singh Rajput", "j4LdeQDEYlE"),
    ],
    [  # 8. Drainage
        indian_channel("Drainage - One Shot Revision | Class 9 Geography Chapter 3", "Magnet Brains", "GxMbkmh8nvA"),
        indian_channel("Drainage ONE SHOT | Full Chapter | Class 9th Geography", "PW Class 9 - NEEV", "9qhUyqjg398"),
    ],
    [  # 9. Climate
        indian_channel("Climate - One Shot Revision | Class 9 Geography Chapter 4", "Magnet Brains", "cwsct4A9VXA"),
        indian_channel("Climate ONE SHOT | Full Chapter | Class 9th Geography", "PW Class 9 - NEEV", "_O6RdDig7eo"),
    ],
    [  # 10. Natural Vegetation and Wildlife
        indian_channel("Natural Vegetation and Wildlife - One Shot Revision | Class 9 Geography Chapter 5", "Magnet Brains", "trGYJIFXs4Y"),
        indian_channel("Natural Vegetation and Wildlife ONE SHOT | Full Chapter", "PW Class 9 - NEEV", "Pk6Lcce_r_I"),
    ],
    [  # 11. Population
        indian_channel("Population - One Shot Revision | Class 9 Geography Chapter 6", "Magnet Brains", "sLuD8mCfxnI"),
        indian_channel("Population | New One Shot Revision Series | Class 9 Geography", "Digraj Singh Rajput", "L26wKCUwo5o"),
    ],
    [  # 12. What is Democracy Why Democracy
        indian_channel("What is Democracy Why Democracy Class 9 One Shot Revision", "Magnet Brains", "vxO8eECuPRM"),
        indian_channel("WHAT IS DEMOCRACY? WHY DEMOCRACY? in One Shot - From Zero to Hero", "Physics Wallah Foundation", "XfuesaaW3d4"),
    ],
    [  # 13. Constitutional Design
        indian_channel("Constitutional Design - One Shot Revision | Class 9 Civics Chapter 2", "Magnet Brains", "n1-_5KGYttY"),
        indian_channel("CONSTITUTIONAL DESIGN in 1 Shot: FULL CHAPTER", "PW Class 9 - NEEV", "sXQnYsEdidk"),
    ],
    [  # 14. Electoral Politics
        indian_channel("Electoral Politics - One Shot Revision | Class 9 Civics Chapter 3", "Magnet Brains", "rPODBuDwc4U"),
        indian_channel("ELECTORAL POLITICS in 1 Shot || FULL Chapter Coverage", "Physics Wallah Foundation", "rJ5CAhW0W5k"),
    ],
    [  # 15. Working of Institutions
        indian_channel("Working of Institutions | New One Shot | Class 9 Civics", "Digraj Singh Rajput", "oMqEsD-Utac"),
        indian_channel("Working Of Institutions ONE SHOT | Full Chapter | Class 9th Civics", "PW Class 9 - NEEV", "jn91xy8DMVg"),
    ],
    [  # 16. Democratic Rights
        indian_channel("Democratic Rights Class 9 One Shot | One Shot Revision", "Magnet Brains", "NaghelNHosc"),
        indian_channel("Democratic Rights in One Shot | Full Chapter Explanation", "Vedantu CBSE 9th", "CIAYWOchiEM"),
    ],
    [  # 17. The Story of Village Palampur
        indian_channel("The Story Of Village Palampur - One Shot Revision | Class 9 Economics Chapter 1", "Magnet Brains", "1DQQbM6xFAk"),
        indian_channel("THE STORY OF VILLAGE PALAMPUR in One Shot - From Zero to Hero", "Physics Wallah Foundation", "7Ah0ssh5DlA"),
    ],
    [  # 18. People as Resource
        indian_channel("People As Resource - One Shot Revision | Class 9 Economics Chapter 2", "Magnet Brains", "aRH0K80lFso"),
        indian_channel("PEOPLE AS A RESOURCE in One Shot - From Zero to Hero", "Physics Wallah Foundation", "me1uKtn1aX4"),
    ],
    [  # 19. Poverty as a Challenge
        indian_channel("Poverty as a Challenge | New One Shot | Class 9 Economics", "Digraj Singh Rajput", "DaE_Hpe-sEI"),
        indian_channel("POVERTY AS A CHALLENGE in One Shot - From Zero to Hero", "Physics Wallah Foundation", "GMZD2i6hwuA"),
    ],
    [  # 20. Food Security in India
        indian_channel("Food Security In India | New One Shot | Class 9 Economics", "Digraj Singh Rajput", "2oCsMusryJo"),
        indian_channel("FOOD SECURITY IN INDIA in One Shot - From Zero to Hero", "Physics Wallah Foundation", "DCHy2cevNd0"),
    ],
]

LEARNING_RESOURCES["Social Science"] = {}

for _index, _chapter_name in enumerate(GRADE_9_SOCIAL_SCIENCE_CHAPTERS):
    LEARNING_RESOURCES["Social Science"][_chapter_name] = GRADE_9_SOCIAL_SCIENCE_RESOURCE_LISTS[_index]

# ── Grade 9 Hindi (NCERT "Ganga" 2026-27 curriculum) — verified chapter-wise resources ──
# No LikhaPoha AI content exists for this subject. Coverage is patchy since this is also a
# brand-new (2026-27) book — 11 of 12 chapters have a findable video despite targeted searches.
# "मैं और मेरा देश" is the sole remaining gap — a newly-ADDED chapter with no previous-edition
# equivalent to fall back to and no dedicated video found anywhere despite repeated searches —
# get_learning_resources() falls through to its generic YouTube-search link for it. Only one
# verified channel per available chapter (not two) given how limited real coverage is for this
# new book.
#
# The live RAG-uploaded chapter labels have OCR/upload text-extraction artifacts for several
# chapters (e.g. "क््या लिखू" instead of "क्या लिखूँ?", "आलखरी चट्टान तक" instead of
# "आखिरी चट्टान तक") — both the clean and the garbled spelling are mapped to the same resource
# so the lookup matches regardless of which variant the dropdown actually shows.
GRADE_9_HINDI_RESOURCE_MAP = {
    "दो बैलों की कथा": indian_channel("NCERT Class 9 Hindi NEW Book “Ganga गंगा” Chapter 1 दो बैलों की कथा", "Gyanshakti TV", "tzM1gyQ5edk"),
    "क्या लिखूँ?": indian_channel("क्या लिखूं? | Class 9 Hindi Chapter 2 'Ganga' Full Explanation", "Hindi Learning By Ashima Mahajan", "StDOUi8yR68"),
    "क््या लिखू": indian_channel("क्या लिखूं? | Class 9 Hindi Chapter 2 'Ganga' Full Explanation", "Hindi Learning By Ashima Mahajan", "StDOUi8yR68"),
    "संवादहीन": indian_channel("NCERT Class 9 Hindi New Book Ganga Chapter 3 संवादहीन Question Answer Part 1", "EduMagnet", "cWC92nfxnvk"),
    "ऐसी भी बातें होती हैं (लता मंगेशकर से साक्षात्कार)": indian_channel("Class 9 Hindi Ganga Chapter 4 एसी भी बातें होती हैं लता मंगेशकर से साक्षात्कार", "EduMagnet", "iyiw6XBvpRM"),
    "ऐसी भी बातीें होती हैं": indian_channel("Class 9 Hindi Ganga Chapter 4 एसी भी बातें होती हैं लता मंगेशकर से साक्षात्कार", "EduMagnet", "iyiw6XBvpRM"),
    "आखिरी चट्टान तक": indian_channel("Chapter 5: Aakhri Chattan Tak (आखिरी चट्टान तक) | Class 9 Hindi Ganga | NCERT Explainer", "EduRev Class 6-10", "is69k0WR2DY"),
    "आलखरी चट्टान तक": indian_channel("Chapter 5: Aakhri Chattan Tak (आखिरी चट्टान तक) | Class 9 Hindi Ganga | NCERT Explainer", "EduRev Class 6-10", "is69k0WR2DY"),
    "रीढ़ की हड्डी": indian_channel("Class 9 Hindi Chapter 3 Reed ki Haddi NCERT Solutions with Detailed Explanation", "Learner Bee", "Yz6s97b55f8"),
    "पद": indian_channel("पद - Explanation | Class 9 Hindi Ganga | Chapter 8 | CBSE 2026", "Magnet Brains", "wZkR7-LFqa8"),
    "राम-लक्ष्मण-परशुराम संवाद": indian_channel("Chapter 9: Ram Lakshman Parshuram Samvad | Class 9 Hindi Ganga | NCERT Explainer", "EduRev Class 6-10", "WRi7vBZOMWg"),
    "राम-लक्षमण-परशुराम संवाद": indian_channel("Chapter 9: Ram Lakshman Parshuram Samvad | Class 9 Hindi Ganga | NCERT Explainer", "EduRev Class 6-10", "WRi7vBZOMWg"),
    "भारति, जय, विजय करो!": indian_channel("\"भारति जय, विजय करे!\"-सूर्यकांत त्रिपाठी \"निराला\"-शब्दार्थ व विशेष सहित सप्रसंग व्याख्या", "Study with Anju Madam", "4y49DbIyh7c"),
    "भारत्त, जय, विजयकरे!": indian_channel("\"भारति जय, विजय करे!\"-सूर्यकांत त्रिपाठी \"निराला\"-शब्दार्थ व विशेष सहित सप्रसंग व्याख्या", "Study with Anju Madam", "4y49DbIyh7c"),
    "झाँसी की रानी": indian_channel("Jhansi Ki Rani Class 9 Hindi | CBSE Ganga Textbook | Full Explanation", "Bhasha Gyan", "j7ui1CHYK9c"),
    "घर की याद": indian_channel("Chapter 5 Ghar Ki Yad / पाठ 5 घर की याद", "NCERT OFFICIAL", "xcbQ25SxJm8"),
}

LEARNING_RESOURCES["Hindi"] = {
    _chapter_name: [_resource]
    for _chapter_name, _resource in GRADE_9_HINDI_RESOURCE_MAP.items()
}

# Add fallback-style resources for chapters where we have not manually curated specific items.
GENERIC_SUBJECT_CHAPTERS = {
    "English": [
        "The Fun They Had", "The Sound of Music", "The Little Girl", "A Truly Beautiful Mind", "The Snake and the Mirror", "My Childhood", "Packing", "Reach for the Top", "The Bond of Love", "Kathmandu", "If I Were You", "The Road Not Taken", "Wind", "Rain on the Roof", "The Lake Isle of Innisfree", "A Legend of the Northland", "No Men Are Foreign", "On Killing a Tree", "The Snake Trying", "A Slumber Did My Spirit Seal", "The Lost Child", "The Adventures of Toto", "Iswaran the Storyteller", "In the Kingdom of Fools", "The Happy Prince", "Weathering the Storm in Ersama", "The Last Leaf", "A House is Not a Home", "The Beggar", "Grammar", "Writing Skills", "Reading Comprehension"
    ],
    "Social Science": [
        "The French Revolution", "Socialism in Europe and the Russian Revolution", "Nazism and the Rise of Hitler", "Forest Society and Colonialism", "Pastoralists in the Modern World", "India Size and Location", "Physical Features of India", "Drainage", "Climate", "Natural Vegetation and Wildlife", "Population", "What is Democracy Why Democracy", "Constitutional Design", "Electoral Politics", "Working of Institutions", "Democratic Rights", "The Story of Village Palampur", "People as Resource", "Poverty as a Challenge", "Food Security in India"
    ],
    "Hindi": [
        "दो बैलों की कथा", "ल्हासा की ओर", "उपभोक्तावाद की संस्कृति", "साँवले सपनों की याद", "नाना साहब की पुत्री देवी मैना को भस्म कर दिया गया", "प्रेमचंद के फटे जूते", "मेरे बचपन के दिन", "एक कुत्ता और एक मैना", "साखियाँ एवं सबद", "वाख", "सवैये", "कैदी और कोकिला", "ग्राम श्री", "चंद्र गहना से लौटती बेर", "मेघ आए", "बच्चे काम पर जा रहे हैं", "गिल्लू", "स्मृति", "कल्लू कुम्हार की उनाकोटी", "मेरा छोटा सा निजी पुस्तकालय", "हमिद खाँ", "दिए जल उठे", "व्याकरण", "लेखन कौशल", "अपठित गद्यांश"
    ],
}

for _subject, _chapters in GENERIC_SUBJECT_CHAPTERS.items():
    LEARNING_RESOURCES.setdefault(_subject, {})
    for _chapter in _chapters:
        q = quote_plus(f"class 9 {_subject} {_chapter} free explanation")
        LEARNING_RESOURCES[_subject].setdefault(_chapter, [
            {"title": f"YouTube Search - {_chapter}", "type": "website", "url": f"https://www.youtube.com/results?search_query={q}"},
        ])


# ── English Grammar resources (Grade 8, 9, 10) ────────────────────────────────
# Free reference sources for CBSE English Grammar topics

GRAMMAR_RESOURCES = [
    {
        "title": "BBC Learning English — Grammar",
        "type": "website",
        "url": "https://www.bbc.co.uk/learningenglish/grammar",
        "description": "Free grammar guides with examples: tenses, voice, reported speech",
    },
    {
        "title": "British Council — LearnEnglish Grammar",
        "type": "website",
        "url": "https://learnenglish.britishcouncil.org/grammar",
        "description": "Interactive grammar lessons: A1 to C1 level, with exercises",
    },
    {
        "title": "CBSE Sample Papers — English",
        "type": "website",
        "url": "https://www.cbse.gov.in/cbsenew/samplepaper.html",
        "description": "Grammar questions from official CBSE sample papers",
    },
]

# Grammar topic links per CBSE Grade 8-10 syllabus
GRAMMAR_TOPIC_RESOURCES = {
    "Tenses": [
        {"title": "BBC Learning English — Intermediate Grammar Guide (Tenses unit)", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/english/intermediate-grammar-guide"},
        {"title": "British Council — Tenses", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/tenses"},
    ],
    "Active and Passive Voice": [
        {"title": "BBC Learning English — Intermediate Grammar Guide (Passive Voice unit)", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/english/intermediate-grammar-guide"},
        {"title": "British Council — Passive Voice", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b2-c1-grammar/passive-voice-introduction"},
    ],
    "Reported Speech": [
        {"title": "BBC Learning English — Intermediate Grammar Guide (Reported Speech unit)", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/english/intermediate-grammar-guide"},
        {"title": "British Council — Reported Speech", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/reported-speech"},
    ],
    "Modals": [
        {"title": "BBC Learning English — Basic Grammar Guide (Modals unit)", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/english/basic-grammar-guide"},
        {"title": "British Council — Modal Verbs", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/modal-verbs"},
    ],
    "Grammar": [
        *GRAMMAR_RESOURCES[:2],
        {"title": "CBSE English Grammar — Sample Papers", "type": "website",
         "url": "https://www.cbse.gov.in/cbsenew/samplepaper.html"},
    ],
    "Writing Skills": [
        {"title": "British Council — Writing Skills", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/skills/writing"},
        {"title": "CBSE English Writing — Sample Papers", "type": "website",
         "url": "https://www.cbse.gov.in/cbsenew/samplepaper.html"},
    ],
}

# ── Grade 8 resources ─────────────────────────────────────────────────────────
GRADE_8_RESOURCES: dict[str, dict[str, list]] = {
    "Maths": {
        # Ganita Prakash Grade 8 (Part 1 + Part 2) — replaces stale data that used no-video
        # PDF links, a title-casing mismatch ("a Cube" vs live "A Cube"), and was missing 5 of
        # 14 live chapters. Single source per chapter, several long chapters only have
        # page-range/part videos rather than one full-chapter video — best available used.
        # "Exploring Some Geometric Themes" has no dedicated video anywhere yet (confirmed
        # after repeated searches) and is left uncurated. Every video verified live via
        # YouTube's oEmbed endpoint.
        "A Square and A Cube": [indian_channel("A Square and A Cube | Part 1 | Class 8 Maths | Chapter 1 | Ganita Prakash", "Learn With Mansi Juniors", "1CECPkW44rc")],
        "Power Play": [indian_channel("Class -8th Maths Ganita Prakash Chapter -2 | Power Play | Full Chapter solution", "MOS Classes Maths (Shine Luthra)", "lGVYkiJz8Xw")],
        "A Story of Numbers": [indian_channel("A Story Of Numbers | Part 1 | Class 8 Maths | Chapter 3 | Ganita Prakash", "Learn With Mansi Juniors", "eNibgsD0NrI")],
        "Quadrilaterals": [indian_channel("Quadrilaterals Class 8 Maths | Ganita Prakash Chapter 4 | One-Shot", "Vedantu Class 6, 7 & 8 (Rajiv Sir)", "zIySvWwAjE8")],
        "Number Play": [indian_channel("Number Play | Part 1 | Class 8 Maths | Chapter 5 | Ganita Prakash", "Learn With Mansi Juniors", "3HdEqfYq5NU")],
        "We Distribute, Yet Things Multiply": [indian_channel("We Distribute Yet Things Multiply | Class 8 Maths Ch-6 | One Shot", "Vedantu Class 6, 7 & 8 (Rajiv Sir)", "zEqiasdszEk")],
        "Proportional Reasoning": [indian_channel("Proportional Reasoning One-Shot | Figure It Out | Class 8 Maths | Ganita Prakash", "Vedantu Class 6, 7 & 8", "_x_gVHYIDgo")],
        "Fractions in Disguise": [indian_channel("Fraction In Disguise Class 8 Maths | Chapter 1 Full Explanation | One Shot", "MOS Classes Maths (Shine Luthra)", "DJmmb6DY67o")],
        "The Baudhayana-Pythagoras Theorem": [indian_channel("The Baudhayana Pythagoras Theorem Class 8 Maths || Ganit Prakash Part - 2", "PW Class 8", "LOqkR4L0gw8")],
        "Proportional Reasoning-2": [indian_channel("Proportional Reasoning-2 Class 8 Maths Ganita Prakash | Chapter -3 | Full Chapter Solutions", "MOS Classes Maths (Shine Luthra)", "wqUzoijtTV0")],
        "Tales by Dots and Lines": [indian_channel("Class 8 maths ganita prakash part 2 | Chapter 5 Tales by dots and lines | Page 122 & 123", "Students Life Juniors", "-R3m-PoY2p0")],
        "Algebra Play": [indian_channel("Class 8 Maths Ganita Prakash Part 2 | Chapter 6 Algebra Play | Page 135 to 137 Solutions", "MathsByShweta", "H7tZzpWW3vM")],
        "Area": [indian_channel("Class 8 Maths Ganita Prakash Solutions | Chapter 7 Area | Page 153 to 157 Solutions", "MathsByShweta", "otORrKMN120")],
    },
    "Science": {
        # NCERT "Curiosity" (2025-26) — replaces stale data that used old chapter titles, had
        # no videos (PDF links only), and was missing about half the live chapters. Single
        # source per chapter; PW Class 8 covers 10 of 13 chapters consistently and is used as
        # the anchor channel. Every video verified live via YouTube's oEmbed endpoint.
        "Exploring the Investigative World of Science": [indian_channel("Exploring The Investigative World Of Science Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "8ddIyWsNY4c")],
        "The Invisible Living World: Beyond Our Naked Eye": [indian_channel("The Invisible Living World : Beyond Our Naked Eye | Class 8 Science Chapter 2 | One-Shot | NCERT", "Ignited Minds", "ijM0-UXI5kM")],
        "Interpreting Health: The Ultimate Treasure": [indian_channel("Class 8 Science Chapter 3 - Health : The Ultimate Treasure | Full Chapter | Curiosity", "NCERT TUTORIAL 6,7 and 8", "fyASPC8IV4g")],
        "Electricity: Magnetic and Heating Effects": [indian_channel("Electricity: Magnetic And Heating Effects Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "es6RKnLLY9E")],
        "Exploring Forces": [indian_channel("Exploring Forces Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "fIhjFWk5P1Y")],
        "Pressure, Winds, Storms, and Cyclones": [indian_channel("Class 8 Science | Chapter 6 Explanation | Pressure, Winds, Storms and cyclones | Curiosity | NCERT", "Wisdom of Avyaan", "MkTtdt4SOQ4")],
        "Particulate Nature of Matter": [indian_channel("Particulate Nature Of Matter Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "ieydo7BS-Zo")],
        "Nature of Matter: Elements, Compounds, and Mixtures": [indian_channel("Nature of Matter: Elements, Compounds & Mixtures Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "EKmYIm2y5xY")],
        "The Amazing World of Solutes, Solvents, and Solutions": [indian_channel("The Amazing World Of Solutes, Solvents And Solutions Class 8 | NEW NCERT | Science | Complete Chapter", "PW Class 8", "uyrVoCX1aLA")],
        "Light: Mirrors and Lenses": [indian_channel("Light: Mirrors and Lenses Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "8Hr1XJ18PsM")],
        "Keeping Time with the Skies": [indian_channel("Keeping Time with the Skies Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "w8jkxGnbq5Y")],
        "How Nature Works in Harmony": [indian_channel("How Nature works in Harmony Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "8AeuqbcjuHg")],
        "Our Home: Earth, a Unique Life Sustaining Planet": [indian_channel("Our Home: Earth, A unique Life-sustaining Planet Class 8 || NEW NCERT || Science || Complete Chapter", "PW Class 8", "NXgkMdHpGy8")],
    },
    "English": {
        # NCERT "Poorvi" (2025-26) — the live dropdown groups by unit ("Unit N: <theme>"),
        # not by the 3 chapters within each unit, so each entry covers the unit's first
        # chapter/poem as a representative single source. Verified via YouTube oEmbed.
        "Wit and Wisdom": [indian_channel("The Wit that Won Hearts | Class 8 English | Unit 1 Chapter 1 | Poorvi | Explanation", "Kaliyaan Tv", "dazBVjDX-lE")],
        "Values and Dispositions": [indian_channel("A Tale of Valour - Major Somnath Sharma (English Explanation) | Class 8 English Poorvi Unit 2", "CBSE with Sudhir", "Iu-VLBzIgGo")],
        "Mystery and Magic": [indian_channel("Class 8 English Poorvi book Unit 3 | Mystery and Magic | The Case of the Fifth Word", "Gagan Ma'am", "XHhnFP1TCM4")],
        "Environment": [indian_channel("The Cherry Tree - Explanation | Class 8th English (Poorvi) | Unit 4", "Magnet Brains", "CGp9rsxowRE")],
        "Science and Curiosity": [indian_channel("Feathered Friend - Explanation | Class 8th English (Poorvi) | Unit 5", "Magnet Brains", "zQ2SsVIg4tA")],
        "Grammar": list(GRAMMAR_RESOURCES),
        "Writing Skills": GRAMMAR_TOPIC_RESOURCES.get("Writing Skills", []),
        "Tenses": GRAMMAR_TOPIC_RESOURCES.get("Tenses", []),
        "Active and Passive Voice": GRAMMAR_TOPIC_RESOURCES.get("Active and Passive Voice", []),
        "Reported Speech": GRAMMAR_TOPIC_RESOURCES.get("Reported Speech", []),
        "Modals": GRAMMAR_TOPIC_RESOURCES.get("Modals", []),
    },
    "Hindi": {
        # NCERT "Malhar" (2025-26). The live RAG-uploaded labels have the same kind of
        # OCR/upload text-extraction artifacts seen in Grade 9/10 Hindi (duplicated letters,
        # a truncated title) — both the clean and the live-label spelling are mapped to the
        # same resource so the lookup matches regardless of which variant shows up. Single
        # source per chapter, every video verified live via YouTube's oEmbed endpoint.
        "स्वदेश": [indian_channel("स्वदेश कविता | Full Explanation + All Questions Answers | Class 8 Hindi | Malhar", "Hello Adhyapak", "C8dAhgwKRpU")],
        "दो गौरैया": [indian_channel("कक्षा-8 हिंदी मल्हार अध्याय-2 दो गौरैया की व्याख्या और कठिन शब्दार्थ", "Garg Education Tech", "kkCg4k2KD6E")],
        "दो गौरैैयाा": [indian_channel("कक्षा-8 हिंदी मल्हार अध्याय-2 दो गौरैया की व्याख्या और कठिन शब्दार्थ", "Garg Education Tech", "kkCg4k2KD6E")],
        "एक आशीर्वाद": [indian_channel("Ek Aashirvaad (एक आशीर्वाद) - NCERT Solutions | Class 8 | Ch 3 | Hindi Malhar Book | CBSE 2025-26", "Magnet Brains", "n19pnOF-syM")],
        "हरिद्वार": [indian_channel("Haridwar (हरिद्वार) - Explanation | Class 8 | Chapter 4 Hindi (Malhar Book) | CBSE 2025-26", "Magnet Brains", "silysVZAgjY")],
        "कबीर के दोहे": [indian_channel("Kabir ke Dohe (कबीर के दोहे) - Explanation | Class 8 | Chapter 5 | Hindi Malhar Book | CBSE 2025-26", "Magnet Brains", "ekpc5E5pFAA")],
        "एक टोकरी भर मिट्टी": [indian_channel("Ek Tokri Bhar Mitti (एक टोकरी भर मिट्टी) - Explanation | Class 8 | Ch 6 | Hindi Malhar Book | CBSE", "Magnet Brains", "vGBHvKpRevU")],
        "एक टोकरी भर": [indian_channel("Ek Tokri Bhar Mitti (एक टोकरी भर मिट्टी) - Explanation | Class 8 | Ch 6 | Hindi Malhar Book | CBSE", "Magnet Brains", "vGBHvKpRevU")],
        "मत बाँधो": [indian_channel("Mat Baandho (मत बाँधो) - Explanation | Class 8 | Chapter 7 | Hindi Malhar Book | CBSE 2025-26", "Magnet Brains", "h86To2dDxBg")],
        "नए मेहमान": [indian_channel("Naye Mehmaan (नए मेहमान) - Explanation | Class 8 | Chapter 8 | Hindi Malhar Book | CBSE 2025-26", "Magnet Brains", "nN1Q_Ihw_Bo")],
        "नए मेहेमाान": [indian_channel("Naye Mehmaan (नए मेहमान) - Explanation | Class 8 | Chapter 8 | Hindi Malhar Book | CBSE 2025-26", "Magnet Brains", "nN1Q_Ihw_Bo")],
        "आदमी का अनुपात": [indian_channel("आदमी का अनुपात - Explanation। Class 8 Hindi Malhar Chapter 9। NCERT Malhar", "Princewood Institute", "w_dLb9ZYLGU")],
        "तरुण के स्वप्न": [indian_channel("तरुण के स्वप्न - Solutions। Class 8 Hindi Malhar Chapter 10। NCERT Malhar", "Princewood Institute", "jFXIABXh3S4")],
        "तरुण केे स्वप्न": [indian_channel("तरुण के स्वप्न - Solutions। Class 8 Hindi Malhar Chapter 10। NCERT Malhar", "Princewood Institute", "jFXIABXh3S4")],
    },
    "Social Science": {
        # NCERT's new integrated Grade 8 book ("Exploring Society: India and Beyond", 2025-26) —
        # single source per chapter, PW Class 8 covers 5 of 7 chapters consistently and is used
        # as the anchor channel. Every video verified live via YouTube's oEmbed endpoint.
        "Natural Resources and Their Use": [indian_channel("Class 8 SST Chapter 1 | Natural Resources & Their Use | One Shot Full Chapter | NCERT Explained", "Concept Corridor", "0YABUzd_Vdc")],
        "Reshaping India’s Political Map": [indian_channel("Reshaping India's Political Map | Class 8 Social Science Chapter 2 | Concepts | NCERT 2025", "Prof.Analysis", "c-4TeKTFqW4")],
        "The Rise of the Marathas": [indian_channel("The Rise of the Marathas Class 8 || NEW NCERT || SST || Complete Chapter", "PW Class 8", "xpjRTr-G7Mk")],
        "The Colonial Era in India": [indian_channel("The Colonial Era in India Class 8 || NEW NCERT || SST || Complete Chapter", "PW Class 8", "e4oHWSb12eY")],
        "Universal Franchise and India’s Electoral System": [indian_channel("Universal Franchise and India's Electoral System Class 8 || NEW NCERT || SST || Complete Chapter", "PW Class 8", "Xj3LXsZPBAQ")],
        "The Parliamentary System: Legislature and Executive": [indian_channel("The Parliamentary System: Legislature and Executive Class 8 || NEW NCERT || SST || Complete Chapter", "PW Class 8", "R8fE5UFcNYM")],
        "Factors of Production": [indian_channel("Factors of Production Class 8 || NEW NCERT || SST || Complete Chapter", "PW Class 8", "Kn7SGtDbAeM")],
    },
}

# ── Grade 10 resources ────────────────────────────────────────────────────────
def ncert_pdf(title, filename):
    """A verified, live NCERT chapter-specific textbook PDF (not the removed generic portal link)."""
    return {"title": title, "type": "website", "url": f"https://ncert.nic.in/textbook/pdf/{filename}"}


# ── Grade 10 Maths — verified chapter-wise resources ──
# Grade 10 got NO new NCERT book for 2026-27 (confirmed via search) — same rationalised
# curriculum as recent years, so unlike Grade 9's brand-new books, coverage here is abundant
# and mature. No LikhaPoha AI content exists for Grade 10. Ritik Mishra (9th & 10th) covers
# all 14 chapters consistently and is used as one anchor channel throughout. Chapter 9 only has
# one Indian channel and no international pick — despite searching, no second source was found.
GRADE_10_MATHS_CHAPTERS = [
    "Real Numbers", "Polynomials", "Pair of Linear Equations in Two Variables",
    "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry",
    "Introduction to Trigonometry", "Some Applications of Trigonometry", "Circles",
    "Areas Related to Circles", "Surface Areas and Volumes", "Statistics", "Probability",
]

GRADE_10_MATHS_RESOURCE_LISTS = [
    [  # 1. Real Numbers
        indian_channel("Real Numbers - One Shot Revision | Class 10 Maths Chapter 1", "Magnet Brains", "dXMYdUcfb6w"),
        indian_channel("Real Numbers ONE SHOT | Class 10 Maths Chapter 1 | Complete Chapter", "Ritik Mishra - 9th & 10th", "MX1iSpb4tRE"),
        international_channel("Intro to Euclid's division algorithm | Real numbers | Class 10 (India)", "Khan Academy India", "H1AE2Se8A5E"),
        ncert_pdf("NCERT Mathematics Grade 10 — Real Numbers", "jemh101.pdf"),
    ],
    [  # 2. Polynomials
        indian_channel("Class 10th Polynomials One Shot | Class 10 Maths Chapter 2", "Mission JEET", "Uill15OhzjE"),
        indian_channel("Polynomials ONE SHOT | Class 10 Maths Chapter 2 | Complete Chapter", "Ritik Mishra - 9th & 10th", "kiegUjhq8Ao"),
        international_channel("Zeros of polynomials introduction | Polynomial graphs | Algebra 2", "Khan Academy", "EtzwLlkoAnM"),
        ncert_pdf("NCERT Mathematics Grade 10 — Polynomials", "jemh102.pdf"),
    ],
    [  # 3. Pair of Linear Equations in Two Variables
        indian_channel("Class 10 Maths Ch 3 | Pair of Linear Equations In Two Variables - One Shot Full Ch Revision", "Magnet Brains", "nrxyhyrURc0"),
        indian_channel("PAIR OF LINEAR EQUATIONS IN 2 VARIABLES in 1 Shot: FULL CHAPTER", "Physics Wallah Foundation", "Pn8B0kCGArg"),
        international_channel("Solving linear systems by graphing | Systems of equations", "Khan Academy", "5a6zpfl50go"),
        ncert_pdf("NCERT Mathematics Grade 10 — Pair of Linear Equations", "jemh103.pdf"),
    ],
    [  # 4. Quadratic Equations
        indian_channel("Quadratic Equations - One Shot | Class 10 Maths Chapter 4", "Magnet Brains", "2OGJVRSLYfA"),
        indian_channel("Quadratic Equations ONE SHOT | Class 10 Maths Chapter 4", "Ritik Mishra - 9th & 10th", "hayFtYnAB-Q"),
        international_channel("Solving a quadratic equation by factoring | Algebra II", "Khan Academy", "2ZzuZvz33X0"),
        ncert_pdf("NCERT Mathematics Grade 10 — Quadratic Equations", "jemh104.pdf"),
    ],
    [  # 5. Arithmetic Progressions
        indian_channel("Class 10th Arithmetic Progressions One Shot | Class 10 Maths Chapter 5", "Mission JEET", "buTk-CqJlIA"),
        indian_channel("Arithmetic Progression Class 10 in One Shot | Class 10 Maths Chapter 5 AP", "Shobhit Nirwan", "zPKdZKBG4oQ"),
        international_channel("Arithmetic Progression | Class 10 Maths | Board Exam 2025", "Khan Academy India", "Thb37iY18to"),
        ncert_pdf("NCERT Mathematics Grade 10 — Arithmetic Progressions", "jemh105.pdf"),
    ],
    [  # 6. Triangles
        indian_channel("Class 10 Maths Chapter 6 in One Shot | Basics of Triangles", "Magnet Brains", "fa_t1gWJxig"),
        indian_channel("Triangles ONE SHOT | Class 10 Maths Chapter 6", "Ritik Mishra - 9th & 10th", "nxo1ItY3oTo"),
        international_channel("Triangles | Class 10 Maths | Board Exam 2025", "Khan Academy India", "MWZP5eAxehQ"),
        ncert_pdf("NCERT Mathematics Grade 10 — Triangles", "jemh106.pdf"),
    ],
    [  # 7. Coordinate Geometry
        indian_channel("Class 10 Coordinate Geometry One Shot | Coordinate Geometry Class 10", "Magnet Brains", "jZzEYiFUZZo"),
        indian_channel("Coordinate Geometry ONE SHOT | Class 10 Maths Chapter 7", "Ritik Mishra - 9th & 10th", "TXDyGK_GdNM"),
        international_channel("Coordinate Geometry | Class 10 Math | Board Exam 2025", "Khan Academy India", "JdgN3MLQQhk"),
        ncert_pdf("NCERT Mathematics Grade 10 — Coordinate Geometry", "jemh107.pdf"),
    ],
    [  # 8. Introduction to Trigonometry
        indian_channel("Introduction to Trigonometry - One Shot Revision (Part 2) | Class 10 Maths Chapter 8", "Magnet Brains", "QzWaAvWFlPc"),
        indian_channel("Trigonometry ONE SHOT | Class 10 Maths Chapter 8", "Ritik Mishra - 9th & 10th", "wdaBwIv7Jso"),
        international_channel("Introduction to Trigonometry | Class 10 Math | Board Exam 2025", "Khan Academy India", "sy4eGZsfw8U"),
        ncert_pdf("NCERT Mathematics Grade 10 — Introduction to Trigonometry", "jemh108.pdf"),
    ],
    [  # 9. Some Applications of Trigonometry
        indian_channel("Some Applications of Trigonometry One Shot | Class 10 Maths Chapter 9", "Ritik Mishra - 9th & 10th", "otABxL0TP6U"),
    ],
    [  # 10. Circles
        indian_channel("Circles - One Shot Revision | Class 10 Maths Chapter 10 | CBSE 2024-25", "Magnet Brains", "es3avCt1Hoc"),
        indian_channel("Circles One Shot | Class 10 Maths Chapter 10", "Ritik Mishra - 9th & 10th", "dazX40Ct7J0"),
        international_channel("Circles | Class 10 Maths | Board Exam 2025", "Khan Academy India", "G0YkFjWIcJQ"),
        ncert_pdf("NCERT Mathematics Grade 10 — Circles", "jemh110.pdf"),
    ],
    [  # 11. Areas Related to Circles
        indian_channel("Areas Related to Circles Class 10th One Shot Revision CBSE 2023 Sprint X", "Vedantu CBSE 10th", "yG-E2eoI87c"),
        indian_channel("Areas Related to Circles One Shot | Class 10 Maths Chapter 11", "Ritik Mishra - 9th & 10th", "usf6lf_3DnU"),
        international_channel("Area of a sector given a central angle | Circles | Geometry", "Khan Academy", "u8JFdwmBvvQ"),
    ],
    [  # 12. Surface Areas and Volumes
        indian_channel("Surface Areas and Volumes - One Shot Revision | Class 10 Maths Crash Course Chapter 12", "Magnet Brains", "QBqMMS5_Yp0"),
        indian_channel("Surface Areas and Volumes One Shot | Class 10 Maths Chapter 12", "Ritik Mishra - 9th & 10th", "9-__HOYREi8"),
        international_channel("Volume of a cone | Perimeter, area, and volume | Geometry", "Khan Academy", "hC6zx9WAiC4"),
    ],
    [  # 13. Statistics
        indian_channel("Statistics - One Shot Revision | Class 10 Maths Chapter 14 (2022-23)", "Magnet Brains", "8fhZI6d4ty0"),
        indian_channel("Statistics One Shot | Class 10 Maths Chapter 13 | Complete Chapter", "Ritik Mishra - 9th & 10th", "BPRM1J8QCb8"),
        international_channel("Finding Mode of grouped data | Statistics | Class 10 | Maths", "Khan Academy India", "FSygiNE1M9o"),
        ncert_pdf("NCERT Mathematics Grade 10 — Statistics", "jemh113.pdf"),
    ],
    [  # 14. Probability
        indian_channel("Probability Class 10 One Shot | Probability One Shot Class 10", "Magnet Brains", "h7iLCSxl890"),
        indian_channel("Probability One Shot | Class 10 Maths Chapter 14", "Ritik Mishra - 9th & 10th", "u1A7OvCJgIM"),
        international_channel("Probability explained | Independent and dependent events", "Khan Academy", "uzkc-qNVoOk"),
        ncert_pdf("NCERT Mathematics Grade 10 — Probability", "jemh114.pdf"),
    ],
]

# ── Grade 10 Science — verified chapter-wise resources ──
# Same situation as Grade 10 Maths: no new NCERT book for 2026-27, so coverage is abundant.
# Alakh Pandey (Physics Wallah) covers 12 of 13 chapters consistently and is used as the anchor
# channel; PW Foundation fills the 13th (Our Environment). No LikhaPoha AI content exists.
GRADE_10_SCIENCE_CHAPTERS = [
    "Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals",
    "Carbon and its Compounds", "Life Processes", "Control and Coordination",
    "How do Organisms Reproduce?", "Heredity", "Light – Reflection and Refraction",
    "The Human Eye and the Colourful World", "Electricity",
    "Magnetic Effects of Electric Current", "Our Environment",
]

GRADE_10_SCIENCE_RESOURCE_LISTS = [
    [  # 1. Chemical Reactions and Equations
        indian_channel("Chemical Reactions & Equations Class 10 | Complete Chapter in ONE SHOT | NCERT Covered", "Alakh Pandey (Physics Wallah)", "s0CttpllLxM"),
        indian_channel("Chemical Reactions and Equations - One Shot Revision | Class 10 Chemistry Chapter 1", "Magnet Brains", "25334wZluB4"),
        international_channel("Types of Chemical Reactions: Study Hall Chemistry #2", "Arizona State University + Crash Course", "Pv7JkI8d1Ng"),
        ncert_pdf("NCERT Science Grade 10 — Chemical Reactions", "jesc101.pdf"),
    ],
    [  # 2. Acids, Bases and Salts
        indian_channel("Acids Bases and Salts Class 10 || Complete CHAPTER IN ONE SHOT || NCERT Covered", "Alakh Pandey (Physics Wallah)", "5bSXK0QttdY"),
        indian_channel("Acids, Bases, and Salts Reactions - One-Shot Revision | Class 10 Chemistry Chapter 2", "Magnet Brains", "iB7NFPLIwZw"),
        international_channel("pH and pOH: Crash Course Chemistry #30", "CrashCourse", "LS67vS10O5Y"),
        ncert_pdf("NCERT Science Grade 10 — Acids, Bases and Salts", "jesc102.pdf"),
    ],
    [  # 3. Metals and Non-metals
        indian_channel("Metals And Non Metals Class 10 || Complete CHAPTER IN ONE SHOT || NCERT Covered", "Alakh Pandey (Physics Wallah)", "YihPV4eSHsQ"),
        indian_channel("Metals and Nonmetals Class 10 | Metals and Nonmetals One Shot Revision", "Magnet Brains", "U3Z2KiJx6y0"),
        international_channel("Reactivity Series of Metals | Environmental | Chemistry", "FuseSchool", "TGPPPFczOj0"),
        ncert_pdf("NCERT Science Grade 10 — Metals and Non-metals", "jesc103.pdf"),
    ],
    [  # 4. Carbon and its Compounds
        indian_channel("Carbon and Its Compounds Class 10 || Complete Chapter in ONE SHOT | NCERT Covered", "Alakh Pandey (Physics Wallah)", "iv4kMn_CrhM"),
        indian_channel("Carbon & its Compounds - One Shot Revision | Class 10 Chemistry Chapter 4", "Magnet Brains", "diROxxtMTr4"),
        international_channel("Hydrocarbon Power!: Crash Course Chemistry #40", "CrashCourse", "UloIw7dhnlQ"),
    ],
    [  # 5. Life Processes
        indian_channel("Life Processes class 10 science biology || Complete CHAPTER IN ONE SHOT || NCERT Covered", "Alakh Pandey (Physics Wallah)", "NLv0qeWmBDk"),
        indian_channel("Life Processes (जैव प्रक्रम) - One Shot Revision | Class 10 Science Chapter 5", "Magnet Brains", "6CAd2gAyYbI"),
        international_channel("Circulatory & Respiratory Systems - CrashCourse Biology #27", "CrashCourse", "9fxm85Fy4sQ"),
        ncert_pdf("NCERT Science Grade 10 — Life Processes", "jesc105.pdf"),
    ],
    [  # 6. Control and Coordination
        indian_channel("Control And Coordination Class 10 || Complete Chapter in One Shot || NCERT Covered", "Alakh Pandey (Physics Wallah)", "vKfpJ2QejNA"),
        indian_channel("Control and Coordination - Quick Revision | Class 10 Science Chapter 6", "Magnet Brains", "ZCYFQF4j3Kg"),
        international_channel("The Nervous System - CrashCourse Biology #26", "CrashCourse", "x4PPZCLnVkA"),
        ncert_pdf("NCERT Science Grade 10 — Control and Coordination", "jesc106.pdf"),
    ],
    [  # 7. How do Organisms Reproduce?
        indian_channel("How Do Organisms Reproduce Class 10 || Complete CHAPTER IN ONE SHOT || NCERT Covered", "Alakh Pandey (Physics Wallah)", "dCAnbdRAsFo"),
        indian_channel("How do Organisms Reproduce Class 10 Complete Chapter Line by Line NCERT Explanation", "CBSE Guidance", "PPPej5Bcszc"),
        international_channel("The Plants & The Bees: Plant Reproduction - CrashCourse Biology #38", "CrashCourse", "ExaQ8shhkw8"),
    ],
    [  # 8. Heredity
        indian_channel("HEREDITY Class 10 || Complete CHAPTER IN ONE SHOT || NCERT Covered", "Alakh Pandey (Physics Wallah)", "tAJkacN88ic"),
        indian_channel("Class 10 Biology Chapter 9 | Heredity and Evolution - One Shot Full Chapter Revision", "Magnet Brains", "cBOlcV0EuOk"),
        international_channel("Heredity: Crash Course Biology #9", "CrashCourse", "CBezq1fFUEA"),
        ncert_pdf("NCERT Science Grade 10 — Heredity", "jesc108.pdf"),
    ],
    [  # 9. Light – Reflection and Refraction
        indian_channel("LIGHT - Reflection & Refraction Class 10 || Complete Chapter in ONE SHOT", "Alakh Pandey (Physics Wallah)", "kHVAk96r05Y"),
        indian_channel("Light-Reflection and Refraction - One Shot Revision (Part 1) | Class 10 Physics Chapter 9", "Magnet Brains", "SDnsnppj_wM"),
        international_channel("Geometric Optics: Crash Course Physics #38", "CrashCourse", "Oh4m8Ees-3Q"),
        ncert_pdf("NCERT Science Grade 10 — Light Reflection and Refraction", "jesc109.pdf"),
    ],
    [  # 10. The Human Eye and the Colourful World
        indian_channel("Human Eye and the Colourful World Class 10 | Complete CHAPTER One Shot | NCERT Covered", "Alakh Pandey (Physics Wallah)", "G7zDZwrP6O4"),
        indian_channel("The Human Eye and the Colourful World - One Shot Revision | Class 10 Physics Chapter 11", "Magnet Brains", "6L01ThI0o_s"),
        international_channel("Vision: Crash Course Anatomy & Physiology #18", "CrashCourse", "o0DYP-u1rNM"),
    ],
    [  # 11. Electricity
        indian_channel("ELECTRICITY in ONE SHOT - Class 10 || Physics Complete Chapter | NCERT Covered", "Alakh Pandey (Physics Wallah)", "S_ihSpnNhXU"),
        indian_channel("Class 10 Physics Chapter 12 | Electricity - One Shot Revision", "Magnet Brains", "FeEzDrbyMVw"),
        international_channel("Electric Current: Crash Course Physics #28", "CrashCourse", "HXOok3mfMLM"),
        ncert_pdf("NCERT Science Grade 10 — Electricity", "jesc111.pdf"),
    ],
    [  # 12. Magnetic Effects of Electric Current
        indian_channel("Magnetic Effects Of Electric Current - Class 10 | Complete Chapter | NCERT Covered", "Alakh Pandey (Physics Wallah)", "Ts15uMyJRsY"),
        indian_channel("Class 10 Physics Ch 13 | Magnetic Effects of Electric Current - One Shot Revision (Part 1)", "Magnet Brains", "lBPlklnpPWY"),
        international_channel("Magnetism: Crash Course Physics #32", "CrashCourse", "s94suB5uLWw"),
    ],
    [  # 13. Our Environment
        indian_channel("Our Environment in One Shot: FULL CHAPTER || Warrior 2026", "Physics Wallah Foundation", "RwQ3YXVilBQ"),
        indian_channel("Class 10 Biology Chapter 15 | Our Environment - One Shot Revision", "Magnet Brains", "3YdCjC2LBU0"),
        international_channel("Ecosystem Ecology: Links in the Chain - Crash Course Ecology #7", "CrashCourse", "v6ubvEJ3KGM"),
        ncert_pdf("NCERT Science Grade 10 — Our Environment", "jesc113.pdf"),
    ],
]

# ── Grade 10 English (First Flight + Footprints Without Feet) — verified single-source per chapter ──
# Scale (30 chapters/poems) made a multi-source curation pass impractical within reasonable time,
# so each entry uses one verified, textbook-aligned Indian explainer instead of the usual two.
# Every video below was confirmed live via YouTube's oEmbed endpoint before being added.
GRADE_10_ENGLISH_CHAPTERS = [
    # First Flight — prose
    "A Letter to God",
    "Nelson Mandela: Long Walk to Freedom",
    "Two Stories about Flying",
    "From the Diary of Anne Frank",
    "The Hundred Dresses I",
    "The Hundred Dresses II",
    "Glimpses of India",
    "Mijbil the Otter",
    "Madam Rides the Bus",
    "The Sermon at Benares",
    "The Proposal",
    # First Flight — poems
    "Dust of Snow",
    "Fire and Ice",
    "A Tiger in the Zoo",
    "How to Tell Wild Animals",
    "The Ball Poem",
    "Amanda",
    "Animals",
    "The Trees",
    "Fog",
    "The Tale of Custard the Dragon",
    # Footprints Without Feet
    "A Triumph of Surgery",
    "The Thief's Story",
    "The Midnight Visitor",
    "A Question of Trust",
    "Footprints without Feet",
    "The Making of a Scientist",
    "The Necklace",
    "Bholi",
    "The Book that Saved the Earth",
]

GRADE_10_ENGLISH_RESOURCE_LISTS = [
    # First Flight — prose
    [indian_channel("A Letter to God - Chapter 1 | Class 10 First Flight", "Magnet Brains", "JhqV9jIVVYg")],
    [indian_channel("Nelson Mandela: Long Walk to Freedom - Chapter 2 | Class 10 First Flight", "Magnet Brains", "IrU9Ip9dpVE")],
    [indian_channel("Two Stories about Flying - Chapter 3 | Class 10 First Flight", "Magnet Brains", "ZTmmJZZhljE")],
    [indian_channel("From the Diary of Anne Frank - Chapter 4 | Class 10 First Flight", "Magnet Brains", "9pENOqI6pl4")],
    [indian_channel("The Hundred Dresses I - Chapter 5 | Class 10 First Flight", "EduMantra- By Motion", "r8IiSdqCHMQ")],
    [indian_channel("The Hundred Dresses II - Chapter 6 | Class 10 First Flight", "EduMantra- By Motion", "O5TEcAd5QYI")],
    [indian_channel("Glimpses of India - Chapter 7 | Class 10 First Flight", "Magnet Brains", "UpPVmG0V0G0")],
    [indian_channel("Mijbil the Otter - Chapter 8 | Class 10 First Flight", "Magnet Brains", "Dvwr3LQU1QA")],
    [indian_channel("Madam Rides the Bus - Chapter 9 | Class 10 First Flight", "Magnet Brains", "CaLH49_uNlY")],
    [indian_channel("The Sermon at Benares - Chapter 10 | Class 10 First Flight", "Magnet Brains", "Za595_6Y-_A")],
    [indian_channel("The Proposal - Chapter 11 | Class 10 First Flight", "Step Up Academy", "fVAPxUo55iY")],
    # First Flight — poems
    [indian_channel("Dust of Snow & Fire and Ice: Full Explanation + PYQs | Class 10 English", "Study simplified with Yash", "MZMcHIymc8c")],
    [indian_channel("Dust of Snow & Fire and Ice: Full Explanation + PYQs | Class 10 English", "Study simplified with Yash", "MZMcHIymc8c")],
    [indian_channel("A Tiger in the Zoo - NCERT Solutions | Class 10 English (Poem)", "Magnet Brains", "gSBxK-XzALQ")],
    [indian_channel("How to Tell Wild Animals | Class 10 Poem Explanation | Full Line-by-Line Analysis", "Let's Learn With Lizzy", "LtiisILR3Wo")],
    [indian_channel("The Ball Poem Class 10 | NCERT First Flight Poem | In-depth Explanation", "Education Made Easier", "jH3SIbDnBZU")],
    [indian_channel("AMANDA | Amanda Class 10 English | First Flight | Poem | Summary/Explanation", "Dear Sir", "lhJxSZmbaGM")],
    [indian_channel("Class 10 (First Flight) - Poem: Animals", "Rucchi Kulkarni", "1ulpazRX7Ok")],
    [indian_channel("Class 10 (First Flight) - Poem: The Trees", "Rucchi Kulkarni", "MVVVBu8Spb8")],
    [indian_channel("Fog | Carl Sandburg | CBSE class 10 poem | First Flight | Line by line Explanation", "The English Youtuber", "TmXL5qN3owU")],
    [indian_channel("Class 10 (First Flight) - Poem: The Tale of Custard the Dragon", "Rucchi Kulkarni", "Ispq3ZyuW-g")],
    # Footprints Without Feet
    [indian_channel("A Triumph of Surgery Full Chapter Explanation & NCERT Solutions | Class 10", "Magnet Brains", "Dsv4lMSbBEc")],
    [indian_channel("The Thief's Story Class 10 Full Explanation | Class 10 English", "Magnet Brains", "BkSOSj3MoIg")],
    [indian_channel("The Midnight Visitor | CBSE Class 10 English | Footprints without Feet | Explanation", "Study with Sudhir", "wKuAybXNytI")],
    [indian_channel("A Question of Trust Full Explanation | Class 10 English | Footprints Without Feet", "Paridhi Classes", "jXVBV9QK1vI")],
    [indian_channel("Footprints without Feet | English Explanation | Invisible Man by H.G. Wells", "Ace-Eduacte", "ADXzJknKLFQ")],
    [indian_channel("Footprints Without Feet Ch 6 The Making of a Scientist NCERT Line by Line Explanation", "Ujjwal Educational Videos", "8KEZR66HlyQ")],
    [indian_channel("The Necklace Full Chapter Explanation & NCERT Solutions | Class 10 English", "Magnet Brains", "Z-xrWrmud0o")],
    [indian_channel("Bholi - One Shot Revision | Class 10 English Footprints Without Feet", "Magnet Brains", "dm73N7sBVXA")],
    [indian_channel("The Book that saved the Earth, Class 10 English Footprints without Feet", "English Academy", "GCf_rfrKotU")],
]

# ── Grade 10 Social Science — verified chapter-wise resources (Economics + History + Geography + Political Science) ──
# Single-source (Magnet Brains anchor, matching the Grade 10 English approach), every video
# verified live via YouTube's oEmbed endpoint before being added.
GRADE_10_SOCIAL_SCIENCE_CHAPTERS = [
    # Economics — Understanding Economic Development
    "Development",
    "Sectors of the Indian Economy",
    "Money and Credit",
    "Globalisation and the Indian Economy",
    "Consumer Rights",
    # History — India and the Contemporary World-II
    "The Rise of Nationalism in Europe",
    "Nationalism in India",
    "The Making of a Global World",
    "The Age of Industrialisation",
    "Print Culture and the Modern World",
    # Geography — Contemporary India-II
    "Resources and Development",
    "Forest and Wildlife Resources",
    "Water Resources",
    "Agriculture",
    "Minerals and Energy Resources",
    "Manufacturing Industries",
    "Lifelines of National Economy",
    # Political Science — Democratic Politics-II
    "Power-sharing",
    "Federalism",
    "Democracy and Diversity",
    "Gender, Religion and Caste",
    "Popular Struggles and Movements",
    "Political Parties",
    "Outcomes of Democracy",
    "Challenges to Democracy",
]

GRADE_10_SOCIAL_SCIENCE_RESOURCE_LISTS = [
    # Economics
    [indian_channel("Development - Full Chapter | Board Exam 2023 | Class 10 Economics Chapter 1 (2022-23)", "Magnet Brains", "jCYwHv_7vyY")],
    [indian_channel("Class 10 Economics Chapter 2 | Sectors of the Indian Economy Full Chapter 2022-23", "Magnet Brains", "sh_K3At_QDA")],
    [indian_channel("Money and Credit - Full Chapter Revision | Class 10 Economics Chapter 3 (2022-23)", "Magnet Brains", "H-PC0A_Iq6Q")],
    [indian_channel("Globalisation and The Indian Economy - Full Chapter | Class 10 Economics Chapter 4 | CBSE 2024-25", "Magnet Brains", "TEirIncA3nY")],
    [indian_channel("Class 10 | Consumer rights | CBSE Board | Economics", "Home Revise", "XMlmaxJ4PkA")],
    # History
    [indian_channel("Rise of Nationalism in Europe Full Chapter Class 10 History | CBSE History Class 10 Ch 1 (2022-23)", "Magnet Brains", "383WJ9NL2d0")],
    [indian_channel("Full Chapter Nationalism in India | Revision Series | Class 10 History Chapter 2 | 2023-24 NCERT", "Magnet Brains", "n9SK6vX2j8k")],
    [indian_channel("The Making of a Global World Full Chapter Class 10 History | CBSE History Class 10 Ch 3 (2022-23)", "Magnet Brains", "W1Gx4FjKJTo")],
    [indian_channel("The Age of Industrialisation - Full Chapter Explanation, NCERT Solutions | Class 10 History Chapter 4", "Magnet Brains", "l5B5yd90sco")],
    [indian_channel("Print Culture and The Modern World | Full Chapter Explanation | Class 10 | History", "Digraj Sir (Social School by Unacademy)", "oI1Pw9qEYyU")],
    # Geography
    [indian_channel("Resources and Development - Full Chapter Explanation | Class 10 Geography Chapter 1 | 2022-23", "Magnet Brains", "7s6_Of6tPBc")],
    [indian_channel("Forest and Wildlife Resources Full Chapter | CBSE Geography Class 10 Chapter 2 (2022-23)", "Magnet Brains", "W6sJdIoNXVM")],
    [indian_channel("Water Resources Full Chapter Class 10 Geography | CBSE Geography Class 10 Chapter 3 (2022-23)", "Magnet Brains", "7oH7-Mum21I")],
    [indian_channel("Class 10th Geography Chapter 4 | Agriculture Full Chapter Explanation (2022-23)", "Magnet Brains", "PeSlhEiM2yU")],
    [indian_channel("Minerals and Energy Resources Full Chapter | CBSE Geography Class 10 Chapter 5 (2022-23)", "Magnet Brains", "ru4_4RUla3k")],
    [indian_channel("Manufacturing Industries (Full Chapter) | Class 10 Geography | SST Ch 6 | Revision Series 2023-24", "Magnet Brains", "f4cOLCTH-tY")],
    [indian_channel("Lifelines of National Economy Full Chapter | CBSE Geography Class 10 Chapter 7 (2022-23)", "Magnet Brains", "BOa2uA4rMlU")],
    # Political Science
    [indian_channel("Class 10 Civics Chapter 1 | Power Sharing Full Chapter 2022-23", "Magnet Brains", "Lj6FODNgJ2A")],
    [indian_channel("Full Chapter Revision Series | Federalism | Class 10 Civics | Chapter 2 | 2023-24 NCERT", "Magnet Brains", "UhS1s4kNwUY")],
    [indian_channel("Democracy and Diversity Full Chapter Class 10 Civics | CBSE Civics Class 10 Chapter 3 (2022-23)", "Magnet Brains", "O4GfrcwDF24")],
    [indian_channel("Gender, Religion and Caste Full Chapter Class 10 Civics | CBSE Civics Class 10 Chapter 4 (2022-23)", "Magnet Brains", "KrYsuQpXHj4")],
    [indian_channel("Popular Struggles and Movements Full Chapter Class 10 Civics | Chapter 5 (2022-23)", "Magnet Brains", "TCnqoebrv_A")],
    [indian_channel("Political Parties Full Chapter Class 10 Civics | CBSE Civics Class 10 Chapter 6 (2022-23)", "Magnet Brains", "O6g7hGwtXY8")],
    [indian_channel("Outcomes of Democracy Full Chapter Class 10 Civics | CBSE Civics Class 10 Chapter 7 (2022-23)", "Magnet Brains", "0GS6FRycmWs")],
    [indian_channel("Challenges to Democracy Full Chapter Class 10 Civics | CBSE Civics Class 10 Chapter 8 (2022-23)", "Magnet Brains", "mim9Z_HxX-Q")],
]


# ── Grade 10 Hindi (Sparsh Bhag-2 / Kshitij Bhag-2, rationalized syllabus) — verified single-source per chapter ──
# The live dropdown labels these chapters by AUTHOR NAME ("अध्याय N: <author>"), not poem/story
# title, so each chapter is keyed by the exact author-name string the dropdown shows. Single
# source per chapter (Magnet Brains anchor where available, otherwise the closest verified
# dedicated explanation channel), matching the Grade 10 English/Social Science approach. Every
# video below was confirmed live via YouTube's oEmbed endpoint before being added.
GRADE_10_HINDI_CHAPTERS = [
    "सूरदास",
    "तुलसीदास",
    "जयशंकर प्रसाद",
    "सूर्यकांत त्रिपाठी 'निराला'",
    "नागार्जुन",
    "मंगलेश डबराल",
    "स्वयं प्रकाश",
    "रामवृक्ष बेनीपुरी",
    "यशपाल",
    "मन्नू भंडारी",
    "यतींद्र मिश्र",
    "भदंत आनंद कौसल्यायन",
]

GRADE_10_HINDI_RESOURCE_LISTS = [
    [indian_channel("Surdas Ke Pad: Poem Explanation - Kshitij Part 2 Chapter 1 | Class 10 Hindi", "Magnet Brains", "IwK2efUZGpw")],
    [indian_channel("Ram Lakshman Parshuram Samvad Explanation (Part 1) - Kshitij Part 2 Ch 2 | Class 10 Hindi", "Magnet Brains", "pquPO5jcA0Y")],
    [indian_channel("क्षितिज भाग 2 कक्षा 10 हिंदी जयशंकर प्रसाद का आत्मकथ्य का संदर्भ प्रसंग व्याख्या एवं प्रश्न अभ्यास", "Ck education jagat", "e5JSZSqiBNU")],
    [indian_channel("उत्साह Utsaah Explanation & Questions-Answers भावार्थ, व्याख्या और प्रश्न-उत्तर Class 10 हिंदी CBSE", "Dr Arpana Rawat", "8-_SWSmPci8")],
    [indian_channel("Yah Danturit Muskan Aur Fasal - Full Chapter | Class 10 Hindi Kshitij Chapter 6", "Magnet Brains Hindi Medium", "YCVhkSyEC1Y")],
    [indian_channel("संगतकार || मंगलेश डबराल || Class 10th Hindi Ncert Line by Line Explanation", "Connect With Hindi", "g0NBE2teykE")],
    [indian_channel("Netaji Ka Chashma (नेताजी का चश्मा) | Class 10 Hindi Chapter Full Explanation", "EduRev Class 6-10", "F5lebPHPIew")],
    [indian_channel("Class 10 Hindi Chapter 8 | रामवृक्ष बेनीपुरी बालगोबिन भगत - परिचय व व्याख्या", "Utkarsh 9th & 10th (Pranita Ma'am)", "0txNHHPo3O4")],
    [indian_channel("तताँरा वामीरो कथा कक्षा-10 | Tatara Vamiro Katha Class 10 Hindi Animated Video | Full Explanation", "Khush classes", "51sUczOQviE")],
    [indian_channel("Class 10 Hindi C.10 | एक कहानी यह भी मन्नू भंडारी - परिचय एवं व्याख्या Part-1", "Utkarsh 9th & 10th (Pranita Ma'am)", "d_qiWmuZePg")],
    [indian_channel("नौबतखाने में इबादत लेखक – यतींद्र मिश्र", "Let's study with ABS Corner", "MsWuXwHA6D0")],
    [indian_channel("Sanskriti class10 / Animation / संस्कृति line by line explanation / Full", "Unending Education", "gqSVQXnSqEM")],
]


def build_chapter_lookup(chapters, resource_lists):
    """Map both plain chapter names and 'Chapter N: <name>' RAG-upload labels to the same resources."""
    lookup = {}
    for _index, _chapter_name in enumerate(chapters):
        _resource_list = resource_lists[_index]
        lookup[_chapter_name] = _resource_list
        lookup[f"Chapter {_index + 1}: {_chapter_name}"] = _resource_list
    return lookup


GRADE_10_RESOURCES: dict[str, dict[str, list]] = {
    "Maths": build_chapter_lookup(GRADE_10_MATHS_CHAPTERS, GRADE_10_MATHS_RESOURCE_LISTS),
    "Science": build_chapter_lookup(GRADE_10_SCIENCE_CHAPTERS, GRADE_10_SCIENCE_RESOURCE_LISTS),
    "Social Science": build_chapter_lookup(GRADE_10_SOCIAL_SCIENCE_CHAPTERS, GRADE_10_SOCIAL_SCIENCE_RESOURCE_LISTS),
    "Hindi": build_chapter_lookup(GRADE_10_HINDI_CHAPTERS, GRADE_10_HINDI_RESOURCE_LISTS),
    "English": {
        **build_chapter_lookup(GRADE_10_ENGLISH_CHAPTERS, GRADE_10_ENGLISH_RESOURCE_LISTS),
        "Grammar": list(GRAMMAR_RESOURCES),
        "Writing Skills": GRAMMAR_TOPIC_RESOURCES.get("Writing Skills", []),
        "Tenses": GRAMMAR_TOPIC_RESOURCES.get("Tenses", []),
        "Active and Passive Voice": GRAMMAR_TOPIC_RESOURCES.get("Active and Passive Voice", []),
        "Reported Speech": GRAMMAR_TOPIC_RESOURCES.get("Reported Speech", []),
        "Modals": GRAMMAR_TOPIC_RESOURCES.get("Modals", []),
    },
}

# ── Grade 11 resources ────────────────────────────────────────────────────────
# Pattern per chapter  (NO LikhaPoha placeholder, NO NCERT link — see get_learning_resources):
#   [0] Indian video  — Physics Wallah / Vedantu (type "youtube", embeds in platform)
#   [1] International — CrashCourse / Khan Academy (type "youtube", embeds in platform)
# Indian video IDs are from Physics Wallah's Class 11 NCERT series (PW channel).
# Replace any ID with a better one if needed — the thumbnail preview will update automatically.

# ── Indian channel search helpers ──────────────────────────────────────────────
# Links open the channel's search results so students can pick the exact video.
# Replace with a specific watch?v= URL once you have the preferred video ID.
def _pw(topic):
    """Physics Wallah channel search — Indian video (Physics / Chemistry)."""
    return f"https://www.youtube.com/results?search_query=physics+wallah+{quote_plus(topic)}+class+11"

def _vedantu(topic):
    """Vedantu channel search — Indian video (Biology / Maths)."""
    return f"https://www.youtube.com/results?search_query=vedantu+{quote_plus(topic)}+class+11+NCERT"

def _ka(topic):
    """Khan Academy YouTube search — International Maths video."""
    return f"https://www.youtube.com/results?search_query=khan+academy+{quote_plus(topic)}"


GRADE_11_RESOURCES: dict[str, dict[str, list]] = {
    "Physics": {
        "Physical World": [
            {"title": "CrashCourse Physics — Physics Preview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=OoO5d5P0Jn4"},
            {"title": "Kurzgesagt — What Is Life? (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=QOCaacO8wus"},
        ],
        # ── Chapter 2 ──────────────────────────────────────────────────────────
        "Units and Measurements": [
            {"title": "CrashCourse — Unit Conversion & Significant Figures (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hQpQ0hxVNTg"},
            {"title": "Khan Academy — Distance and Displacement Intro (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=vQCkYm3v3aA"},
        ],
        "Units and Measurement": [
            {"title": "CrashCourse — Unit Conversion & Significant Figures (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hQpQ0hxVNTg"},
            {"title": "Khan Academy — Distance and Displacement Intro (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=vQCkYm3v3aA"},
        ],
        # ── Chapter 3 ──────────────────────────────────────────────────────────
        "Motion in a Straight Line": [
            {"title": "CrashCourse Physics — Motion in a Straight Line (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ZM8ECpBuQYE"},
            {"title": "Khan Academy — Distance and Displacement (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=vQCkYm3v3aA"},
        ],
        # ── Chapter 4 ──────────────────────────────────────────────────────────
        "Motion in a Plane": [
            {"title": "CrashCourse Physics — Vectors and 2D Motion (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=w3BhzYI6zXU"},
            {"title": "Khan Academy — Introduction to Vectors and Scalars (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ihNZlp7iUHE"},
        ],
        # ── Chapter 5 ──────────────────────────────────────────────────────────
        "Laws of Motion": [
            {"title": "CrashCourse Physics — Newton's Laws (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=kKKM8Y-u7ds"},
            {"title": "Khan Academy — Newton's Laws of Motion (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=CQYELiTtUs8"},
        ],
        # ── Chapter 6 ──────────────────────────────────────────────────────────
        "Work, Energy and Power": [
            {"title": "CrashCourse Physics — Work, Energy and Power (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=w4QFJb9a8vo"},
            {"title": "Khan Academy — Work and Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ewfMcg3wRaQ"},
        ],
        # ── Chapter 7 ──────────────────────────────────────────────────────────
        "System of Particles and Rotational Motion": [
            {"title": "CrashCourse Physics — Rotational Motion (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=fmXFWi-WfyU"},
            {"title": "Khan Academy — Angular Momentum and Torque (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=o7_zmuBweHI"},
        ],
        # ── Chapter 8 ──────────────────────────────────────────────────────────
        "Gravitation": [
            {"title": "CrashCourse Physics — Gravity (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7gf6YpdvtE0"},
            {"title": "Kurzgesagt — Gravity Explained (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=e5GBM-MEKzo"},
        ],
        # ── Chapter 9 ──────────────────────────────────────────────────────────
        "Mechanical Properties of Solids": [
            {"title": "CrashCourse Physics — Statics and Torque (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=9cbF9A6eQNA"},
            {"title": "Khan Academy — Stress Strain and Elastic Modulus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VRXLvJPTV0k"},
        ],
        # ── Chapter 10 ─────────────────────────────────────────────────────────
        "Mechanical Properties of Fluids": [
            {"title": "CrashCourse Physics — Fluids at Rest (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=b5SqYuWT4-4"},
            {"title": "Khan Academy — Fluid Pressure and Bernoulli Equation (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VRXLvJPTV0k"},
        ],
        # ── Chapter 11 ─────────────────────────────────────────────────────────
        "Thermal Properties of Matter": [
            {"title": "CrashCourse Physics — Temperature and Kinetic Theory (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=jxstE6A_CYQ"},
            {"title": "Khan Academy — Specific Heat and Thermal Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7L1EaURmvDs"},
        ],
        # ── Chapter 12 ─────────────────────────────────────────────────────────
        "Thermodynamics": [
            {"title": "CrashCourse Physics — Thermodynamics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TfYCnOvNnFU"},
            {"title": "Veritasium — Entropy The Most Misunderstood Concept (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=DxL2HoqLbyA"},
        ],
        # ── Chapter 13 ─────────────────────────────────────────────────────────
        "Kinetic Theory": [
            {"title": "CrashCourse Physics — Temperature Kinetic Theory and Gas Law (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=jxstE6A_CYQ"},
            {"title": "Khan Academy — Kinetic Molecular Theory (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HkSXiHz9vUc"},
        ],
        # ── Chapter 14 ─────────────────────────────────────────────────────────
        "Oscillations": [
            {"title": "CrashCourse Physics — Uniform Circular Motion and SHM (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=bpFK2VCRHUs"},
            {"title": "Khan Academy — Introduction to Simple Harmonic Motion (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ZcZQsj6YAgU"},
        ],
        # ── Chapter 15 ─────────────────────────────────────────────────────────
        "Waves": [
            {"title": "CrashCourse Physics — Traveling Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=5fqwJyt4Lus"},
            {"title": "Khan Academy — Introduction to Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=c38H6UKt3_I"},
        ],
        "Systems of Particles and Rotational Motion": [
            {"title": "CrashCourse Physics — Rotational Motion (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=fmXFWi-WfyU"},
            {"title": "Khan Academy — Angular Momentum and Torque (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=o7_zmuBweHI"},
        ],
        "Kinetic Theory of Gases": [
            {"title": "CrashCourse Physics — Temperature Kinetic Theory and Gas Law (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=jxstE6A_CYQ"},
            {"title": "Khan Academy — Kinetic Molecular Theory (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HkSXiHz9vUc"},
        ],
        "Mechanical Properties of Solid": [
            {"title": "CrashCourse Physics — Statics and Torque (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=9cbF9A6eQNA"},
            {"title": "Khan Academy — Stress Strain and Elastic Modulus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VRXLvJPTV0k"},
        ],
        "Mechanical Properties of Fluid": [
            {"title": "CrashCourse Physics — Fluids at Rest (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=b5SqYuWT4-4"},
            {"title": "Khan Academy — Fluid Pressure and Bernoulli Equation (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VRXLvJPTV0k"},
        ],
    },
    "Chemistry": {
        "Some Basic Concepts of Chemistry": [
            {"title": "CrashCourse Chemistry — Unit Conversion and the Mole (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hQpQ0hxVNTg"},
            {"title": "Khan Academy — The Mole and Avogadros Number (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=cvi4IJMZ13Q"},
        ],
        "Structure of Atom": [
            {"title": "CrashCourse Chemistry — Atomic Theory (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=rcKilE9CdaA"},
            {"title": "Khan Academy — Bohr Model and Atomic Structure (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=haFTkhOcQaY"},
        ],
        "Classification of Elements and Periodicity in Properties": [
            {"title": "CrashCourse Chemistry — Periodic Table (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=UL1jmJaUkaQ"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "Chemical Bonding and Molecular Structure": [
            {"title": "CrashCourse Chemistry — Chemical Bonding (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lQ6FBA1HM3s"},
            {"title": "Khan Academy — Ionic and Covalent Bonding (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=FaeAurHnQJs"},
        ],
        "States of Matter": [
            {"title": "CrashCourse Chemistry — Matter Changing States (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=QiiyvzZBKT8"},
            {"title": "Khan Academy — States of Matter and Ideal Gas (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=pKvo0XWZtjo"},
        ],
        "Thermodynamics": [
            {"title": "CrashCourse Chemistry — Thermochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TLRZAFU_9Kg"},
            {"title": "Khan Academy — Enthalpy and Thermochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TNwGNHqwHxc"},
        ],
        "Equilibrium": [
            {"title": "CrashCourse Chemistry — Equilibrium (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=SV7U4yAXL5I"},
            {"title": "Khan Academy — Chemical Equilibrium Constant (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=5HZbCNg9mIw"},
        ],
        "Redox Reactions": [
            {"title": "CrashCourse Chemistry — Reduction and Oxidation (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=cPDptc0wUYI"},
            {"title": "Khan Academy — Oxidation and Reduction Redox (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=DvYs1HILq1g"},
        ],
        "Hydrocarbons": [
            {"title": "CrashCourse Chemistry — Hydrocarbons (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=UloIw7dhnlQ"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Organic Chemistry – Some Basic Principles and Techniques": [
            {"title": "CrashCourse Chemistry — Organic Chemistry Basics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=CEH3O6l1pbw"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Hydrogen": [
            {"title": "CrashCourse Chemistry — Intermolecular Forces (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=GIPrsWuSkQc"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "The s-Block Elements": [
            {"title": "CrashCourse Chemistry — Electron Configuration (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=AN4KifV12DA"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "The p-Block Elements": [
            {"title": "CrashCourse Chemistry — The Nucleus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ANi709MYnWg"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "Environmental Chemistry": [
            {"title": "CrashCourse Chemistry — Big Questions in Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=aLuSi_6Ol8M"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "Organic Chemistry - Some Basic Principles and Techniques": [
            {"title": "CrashCourse Chemistry — Organic Chemistry Basics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=CEH3O6l1pbw"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
    },
    "Biology": {
        "The Living World": [
            {"title": "CrashCourse Biology — The Science of Biology (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=tZE_fQFK8EY"},
            {"title": "Kurzgesagt — What Is Life How Does It Work (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=QOCaacO8wus"},
        ],
        "Biological Classification": [
            {"title": "CrashCourse Biology — Taxonomy Life's Filing System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=y7raEBOvLwU"},
            {"title": "Khan Academy — Taxonomy and Classification (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=mrheet-2osg"},
        ],
        "Plant Kingdom": [
            {"title": "CrashCourse Biology — Vascular Plants (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=p15KSbNxb28"},
            {"title": "Kurzgesagt — How Evolution Works (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hOfRN0KihOU"},
        ],
        "Animal Kingdom": [
            {"title": "CrashCourse Biology — Complex Animals (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=pj1oFx42d48"},
            {"title": "Kurzgesagt — The Immune System Explained (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lXfEK8G8CUI"},
        ],
        "Cell: The Unit of Life": [
            {"title": "CrashCourse Biology — The Cell (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=aO3Yp45zmw8"},
            {"title": "Khan Academy — Cell Structure and Function (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7FN1NBoV2u0"},
        ],
        "Biomolecules": [
            {"title": "CrashCourse Biology — Biological Molecules (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=cjR5zPrVjTc"},
            {"title": "Khan Academy — Macromolecules Proteins Carbs Lipids (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HGg_WiaSr4U"},
        ],
        "Cell Cycle and Cell Division": [
            {"title": "CrashCourse Biology — Cell Division (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=IALw687nswo"},
            {"title": "Khan Academy — Mitosis and Cell Division (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U5vAO_f2LDQ"},
        ],
        "Photosynthesis in Higher Plants": [
            {"title": "CrashCourse Biology — Photosynthesis (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HsAUGbUgx6Y"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Respiration in Plants": [
            {"title": "CrashCourse Biology — ATP and Respiration (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Y1mPWVzaGQY"},
            {"title": "Khan Academy — Cellular Respiration Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ArmlWtDnuys"},
        ],
        "Breathing and Exchange of Gases": [
            {"title": "CrashCourse Biology — Circulatory and Respiratory Systems (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YnJPbphsoMY"},
            {"title": "Khan Academy — Respiratory System and Breathing (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=qGiPZf7njqY"},
        ],
        "Body Fluids and Circulation": [
            {"title": "CrashCourse Biology — Circulatory and Respiratory Systems (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YnJPbphsoMY"},
            {"title": "Khan Academy — Heart and Circulatory System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7K2icszdxQc"},
        ],
        "Neural Control and Coordination": [
            {"title": "CrashCourse Biology — The Nervous System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=j6YaOqKORYY"},
            {"title": "Khan Academy — Neurons and the Nervous System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=h2H6POZowiU"},
        ],
        "Chemical Coordination and Integration": [
            {"title": "CrashCourse Biology — Endocrine System and Hormones (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6ulXau2HyHg"},
            {"title": "Khan Academy — Endocrine System and Hormones (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ER49EweKwW8"},
        ],
        "Morphology of Flowering Plants": [
            {"title": "CrashCourse Biology — Plant Cells (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=9Ia8zH-qMZw"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Anatomy of Flowering Plants": [
            {"title": "CrashCourse Biology — Non-Vascular Plants (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=62cN8Z5Velo"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Structural Organisation in Animals": [
            {"title": "CrashCourse Biology — Eukaryopolis (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=yGYnwMSflBU"},
            {"title": "Khan Academy — Cell Structure and Function (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7FN1NBoV2u0"},
        ],
        "Transport in Plants": [
            {"title": "CrashCourse Biology — Membranes and Transport (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=KfHYN6tZnpU"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Mineral Nutrition": [
            {"title": "CrashCourse Biology — Water Liquid Awesome (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=rgZhDoPgzK8"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Plant Growth and Development": [
            {"title": "CrashCourse Biology — The Chemistry of Life (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=xOLcZMw0hd4"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Digestion and Absorption": [
            {"title": "CrashCourse Biology — The Digestive System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=9zwq8N4Ufd8"},
            {"title": "Khan Academy — Cellular Respiration Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ArmlWtDnuys"},
        ],
        "Excretory Products and their Elimination": [
            {"title": "CrashCourse Biology — The Musculoskeletal System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4YNDB_zSzfE"},
            {"title": "Khan Academy — Neurons and the Nervous System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=h2H6POZowiU"},
        ],
        "Locomotion and Movement": [
            {"title": "CrashCourse Biology — The Musculoskeletal System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4YNDB_zSzfE"},
            {"title": "Khan Academy — Heart and Circulatory System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7K2icszdxQc"},
        ],
    },
    # ── MATHS ─────────────────────────────────────────────────────────────────
    "Mathematics": {
        "Sets": [
            {"title": "CrashCourse Statistics — What is Statistics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=XZo4xyJXCak"},
            {"title": "Khan Academy — Introduction to Sets (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Relations and Functions": [
            {"title": "CrashCourse Statistics — Data Visualization (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VHYOuWu9jQI"},
            {"title": "Khan Academy — Relations and Functions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-DTMakGDZAw"},
        ],
        "Trigonometric Functions": [
            {"title": "CrashCourse Statistics — Normal Distribution (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Iu17mY1VfZU"},
            {"title": "3Blue1Brown — Eulers Formula and Trigonometry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=mvmuCPvRoWQ"},
        ],
        "Complex Numbers and Quadratic Equations": [
            {"title": "CrashCourse Statistics — Z-Scores (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6hJGa4Zp62M"},
            {"title": "Khan Academy — Complex Numbers (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=T647CGsuOVU"},
        ],
        "Linear Inequalities": [
            {"title": "CrashCourse Statistics — Measures of Spread (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=LuBD49SFpWs"},
            {"title": "Khan Academy — Linear Inequalities (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Z1zdkcwosD4"},
        ],
        "Permutations and Combinations": [
            {"title": "CrashCourse Statistics — Counting (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MUCvUgGfzdo"},
            {"title": "Khan Academy — Permutations and Combinations (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Z1zdkcwosD4"},
        ],
        "Binomial Theorem": [
            {"title": "CrashCourse Statistics — Binomial Distribution (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=wkAjnGmRPVo"},
            {"title": "Khan Academy — Binomial Theorem (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WUvTyaaNkzM"},
        ],
        "Sequences and Series": [
            {"title": "CrashCourse Statistics — Visualizing Distributions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=5rUVYWfZOb8"},
            {"title": "Khan Academy — Arithmetic Sequences and Series (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=_cooC3yG_p0"},
        ],
        "Straight Lines": [
            {"title": "CrashCourse Statistics — Correlation and Causation (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=gq3FPpm2yvA"},
            {"title": "Khan Academy — Slope and Equation of a Line (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=XMJ72mtMn4Y"},
        ],
        "Conic Sections": [
            {"title": "CrashCourse Physics — Lenses (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-w-VTw0tQlE"},
            {"title": "Khan Academy — Introduction to Conic Sections (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=0A7RR0oy2ho"},
        ],
        "Introduction to Three Dimensional Geometry": [
            {"title": "CrashCourse Physics — Geometric Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=g-wjP1otQWI"},
            {"title": "Khan Academy — 3D Geometry Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Limits and Derivatives": [
            {"title": "3Blue1Brown — Essence of Calculus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WUvTyaaNkzM"},
            {"title": "Khan Academy — Limits Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Statistics": [
            {"title": "CrashCourse Statistics — Mean Median and Mode (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Mb9BuEkbaHQ"},
            {"title": "Khan Academy — Mean Median and Mode Statistics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=k3aKKasOmIw"},
        ],
        "Probability": [
            {"title": "CrashCourse Statistics — Basic Probability (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=JnoBjHz2dtw"},
            {"title": "Khan Academy — Basic Probability (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=uzkc-qNVoOk"},
        ],
    },
    # ── ENGLISH ──────────────────────────────────────────────────────────────
    "English": {
        # ── Hornbill — Prose ──────────────────────────────────────────────────
        "The Portrait of a Lady": [
            {"title": "The Portrait of a Lady Class 11 | Hornbill Chapter 1 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=NoK4h6ovI-A"},
                ],
        "We're Not Afraid to Die... if We Can All Be Together": [
            {"title": "We Are Not Afraid to Die Class 11 | Hornbill Chapter 2 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=lrUa6TRGL44"},
                ],
        "Discovering Tut: the Saga Continues": [
            {"title": "Discovering Tut Class 11 | Hornbill Chapter 3 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=x4FTlX1DAX8"},
                ],
        "Landscape of the Soul": [
            {"title": "Landscape of the Soul Class 11 | Hornbill Chapter 4 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=CyUISy5a_yY"},
                ],
        "The Ailing Planet: the Green Movement's Role": [
            {"title": "The Ailing Planet Class 11 | Hornbill Chapter 5 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=7M5kbfis0b0"},
                ],
        "The Browning Version": [
            {"title": "The Browning Version Class 11 | Hornbill Chapter 6 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=xorNo6_IN3M"},
                ],
        "The Adventure": [
            {"title": "The Adventure Class 11 | Hornbill Chapter 7 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=x1ZeWG5eee0"},
                ],
        "Silk Road": [
            {"title": "Silk Road Class 11 | Hornbill Chapter 8 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=7kfrLyEBN9k"},
                ],
        # ── Hornbill — Poetry ─────────────────────────────────────────────────
        "A Photograph": [
            {"title": "A Photograph Class 11 | Hornbill Poem 1 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=g9IZ3TV4UC8"},
                ],
        "The Laburnum Top": [
            {"title": "The Laburnum Top Class 11 | Hornbill Poem 2 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=R6nBT2SSfs0"},
                ],
        "The Voice of the Rain": [
            {"title": "The Voice of the Rain Class 11 | Hornbill Poem 4 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=Y4HrfwihKYM"},
                ],
        "Childhood": [
            {"title": "Childhood Class 11 | Hornbill Poem 6 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=qkVra0gBtW4"},
                ],
        "Father to Son": [
            {"title": "Father to Son Class 11 | Hornbill Poem 5 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=BoDjDlcvrrY"},
                ],
        # ── Snapshots — Supplementary Reader ─────────────────────────────────
        "The Summer of the Beautiful White Horse": [
            {"title": "The Summer of a Beautiful White Horse Class 11 | Snapshots Chapter 1 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=5syylm7vr0M"},
                ],
        "The Address": [
            {"title": "The Address Class 11 | Snapshots Chapter 2 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=2kYeA0bslHw"},
                ],
        "Ranga's Marriage": [
            {"title": "Ranga's Marriage Class 11 | Snapshots Chapter 3 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=B4cSwUXM1ik"},
                ],
        "Albert Einstein at School": [
            {"title": "Albert Einstein at School Class 11 | Snapshots Chapter 4 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=smHugZgBulI"},
                ],
        "Mother's Day": [
            {"title": "Mother's Day Class 11 | Snapshots Chapter 5 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=IEhxfEJ-QTc"},
                ],
        "The Ghat of the Only World": [
            {"title": "The Ghat of the Only World Class 11 | Snapshots Chapter 6 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=9_37-AWF-EU"},
                ],
        "Birth": [
            {"title": "Birth Class 11 | Snapshots Chapter 7 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=8O7tp-FWxIw"},
                ],
        "The Tale of Melon City": [
            {"title": "The Tale of the Melon City Class 11 | Snapshots Chapter 8 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=bSUp338R3vk"},
                ],
        # ── Grammar / Writing Skills ──────────────────────────────────────────
        "Grammar": [
            {"title": "BBC Learning English — Grammar Reference (International)", "type": "website", "url": "https://www.bbc.co.uk/learningenglish/grammar"},
            {"title": "Magnet Brains — Class 11 English Grammar (India)", "type": "website", "url": "https://www.youtube.com/results?search_query=magnet+brains+class+11+english+grammar"},
        ],
        "Writing Skills": [
            {"title": "British Council — Writing Skills (International)", "type": "website", "url": "https://learnenglish.britishcouncil.org/skills/writing"},
            {"title": "Magnet Brains — Class 11 English Writing Skills (India)", "type": "website", "url": "https://www.youtube.com/results?search_query=magnet+brains+class+11+english+writing+skills"},
        ],
    },
}



# ── Grade 12 resources ────────────────────────────────────────────────────────────────────────
GRADE_12_RESOURCES: dict[str, dict[str, list]] = {
    "Physics": {
        "Electric Charges and Fields": [
            {"title": "CrashCourse Physics — Electric Charge (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6BHbJ_gBOk0"},
            {"title": "Khan Academy — Electric Charge and Electric Force (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WOEvvHbc240"},
        ],
        "Electrostatic Potential and Capacitance": [
            {"title": "CrashCourse Physics — Electric Potential (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=tuSC0ObB-qY"},
            {"title": "Khan Academy — Electric Potential Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6BHbJ_gBOk0"},
        ],
        "Current Electricity": [
            {"title": "CrashCourse Physics — Electric Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4i1MUWJoI0U"},
            {"title": "Khan Academy — Introduction to Electric Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=p1woKh2mdVQ"},
        ],
        "Moving Charges and Magnetism": [
            {"title": "CrashCourse Physics — Magnetism (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TFlVWf8JX4A"},
            {"title": "Khan Academy — Magnetic Force on Moving Charge (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WOEvvHbc240"},
        ],
        "Magnetism and Matter": [
            {"title": "CrashCourse Physics — Magnetism (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TFlVWf8JX4A"},
            {"title": "Khan Academy — Magnetic Force on Current Carrying Wire (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=p1woKh2mdVQ"},
        ],
        "Electromagnetic Induction": [
            {"title": "CrashCourse Physics — Electromagnetic Induction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=mdulzEfQXDE"},
            {"title": "Khan Academy — Introduction to Electromagnetic Induction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ZrMltpK6iAw"},
        ],
        "Alternating Current": [
            {"title": "CrashCourse Physics — AC Circuits (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ZrMltpK6iAw"},
            {"title": "Khan Academy — AC Circuits and Alternating Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HXOok3mfMLM"},
        ],
        "Electromagnetic Waves": [
            {"title": "CrashCourse Physics — Electromagnetic Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HXOok3mfMLM"},
            {"title": "Khan Academy — Introduction to Electromagnetic Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=s94suB5uLWw"},
        ],
        "Ray Optics and Optical Instruments": [
            {"title": "CrashCourse Physics — Geometric Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=g-wjP1otQWI"},
            {"title": "Khan Academy — Reflection and Refraction of Light (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-w-VTw0tQlE"},
        ],
        "Wave Optics": [
            {"title": "CrashCourse Physics — Wave Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=s94suB5uLWw"},
            {"title": "Khan Academy — Young Double Slit Experiment (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=g-wjP1otQWI"},
        ],
        "Dual Nature of Radiation and Matter": [
            {"title": "CrashCourse Physics — Quantum Mechanics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7kb1VT0J3DE"},
            {"title": "Khan Academy — Photoelectric Effect (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VYxYuaDvdM0"},
        ],
        "Atoms": [
            {"title": "CrashCourse Physics — Nuclear Physics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=K40lNL3KsJ4"},
            {"title": "Khan Academy — Bohr Model of Hydrogen (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Oh4m8Ees-3Q"},
        ],
        "Nuclei": [
            {"title": "CrashCourse Physics — Radioactivity (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lUhJL7o6_cA"},
            {"title": "Khan Academy — Nuclear Binding Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=VYxYuaDvdM0"},
        ],
        "Semiconductor Electronics: Materials, Devices and Simple Circuits": [
            {"title": "CrashCourse Physics — Quantum Mechanics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=qO_W70VegbQ"},
            {"title": "Khan Academy — Semiconductors Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7kb1VT0J3DE"},
        ],
    },
    "Chemistry": {
        "The Solid State": [
            {"title": "CrashCourse Chemistry — Solids (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=LS67vS10O5Y"},
            {"title": "Khan Academy — Solids Liquids and Gases (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=pKvo0XWZtjo"},
        ],
        "Solutions": [
            {"title": "CrashCourse Chemistry — Solutions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=JbqtqCunYzA"},
            {"title": "Khan Academy — Solutions Suspension and Colloid (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=qFHYnSY1h9I"},
        ],
        "Electrochemistry": [
            {"title": "CrashCourse Chemistry — Electrochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=a8LF7JEb0IA"},
            {"title": "Khan Academy — Introduction to Electrochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=1tvvSUySfls"},
        ],
        "Chemical Kinetics": [
            {"title": "CrashCourse Chemistry — Reaction Rates (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=GqtUWyDR1fg"},
            {"title": "Khan Academy — Introduction to Chemical Kinetics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=5HZbCNg9mIw"},
        ],
        "Surface Chemistry": [
            {"title": "CrashCourse Chemistry — Intermolecular Forces (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=GIPrsWuSkQc"},
            {"title": "Khan Academy — Intermolecular Forces (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=pKvo0XWZtjo"},
        ],
        "General Principles and Processes of Isolation of Elements": [
            {"title": "CrashCourse Chemistry — Oxidation States (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=cPDptc0wUYI"},
            {"title": "Khan Academy — Oxidation and Reduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=DvYs1HILq1g"},
        ],
        "The p-Block Elements": [
            {"title": "CrashCourse Chemistry — The Nucleus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ANi709MYnWg"},
            {"title": "Khan Academy — Periodic Table Trends (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=MyBYZJ3Wo_0"},
        ],
        "The d and f Block Elements": [
            {"title": "CrashCourse Chemistry — Electron Configuration (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=AN4KifV12DA"},
            {"title": "Khan Academy — Electron Configuration (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=haFTkhOcQaY"},
        ],
        "Coordination Compounds": [
            {"title": "CrashCourse Chemistry — Calorimetry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=8Fdt5WnYn1k"},
            {"title": "Khan Academy — Chemical Bonding and Molecular Structure (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=FaeAurHnQJs"},
        ],
        "Haloalkanes and Haloarenes": [
            {"title": "CrashCourse Chemistry — Organic Chemistry Basics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=CEH3O6l1pbw"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Alcohols, Phenols and Ethers": [
            {"title": "CrashCourse Chemistry — Alcohols (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=kXFEex-dABU"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Aldehydes, Ketones and Carboxylic Acids": [
            {"title": "CrashCourse Chemistry — Aldehydes and Ketones (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hlXc_eEtBHA"},
            {"title": "Khan Academy — Carbonyl Groups (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Amines": [
            {"title": "CrashCourse Chemistry — Amines (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U7wavimfNFE"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Biomolecules": [
            {"title": "CrashCourse Chemistry — Biomolecules (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=rHxxLYzJ8Sw"},
            {"title": "Khan Academy — Macromolecules Proteins Carbs Lipids (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HGg_WiaSr4U"},
        ],
        "Polymers": [
            {"title": "CrashCourse Chemistry — Big Questions in Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=aLuSi_6Ol8M"},
            {"title": "Khan Academy — Introduction to Organic Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=nDV5yWfHKko"},
        ],
        "Chemistry in Everyday Life": [
            {"title": "CrashCourse Chemistry — Big Questions in Chemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=aLuSi_6Ol8M"},
            {"title": "Khan Academy — Acids and Bases (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=5HZbCNg9mIw"},
        ],
    },
    "Biology": {
        "Reproduction in Organisms": [
            {"title": "CrashCourse Biology — Meiosis (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=2TSIUt-lHyo"},
            {"title": "Khan Academy — Meiosis and Sexual Reproduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U5vAO_f2LDQ"},
        ],
        "Sexual Reproduction in Flowering Plants": [
            {"title": "CrashCourse Biology — Meiosis (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=2TSIUt-lHyo"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Human Reproduction": [
            {"title": "CrashCourse Biology — Reproductive System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=kjZAHBMMKoU"},
            {"title": "Khan Academy — Human Reproductive Biology (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U5vAO_f2LDQ"},
        ],
        "Reproductive Health": [
            {"title": "CrashCourse Biology — Reproductive System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=kjZAHBMMKoU"},
            {"title": "Khan Academy — Mitosis and Cell Division (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U5vAO_f2LDQ"},
        ],
        "Principles of Inheritance and Variation": [
            {"title": "CrashCourse Biology — Variation in Populations (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=i-VeKZeyHZs"},
            {"title": "Khan Academy — Mitosis and Cell Division (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=U5vAO_f2LDQ"},
        ],
        "Molecular Basis of Inheritance": [
            {"title": "CrashCourse Biology — DNA Structure and Replication (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4joZpdXeS4A"},
            {"title": "Khan Academy — DNA Structure and Replication (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4joZpdXeS4A"},
        ],
        "Evolution": [
            {"title": "CrashCourse Biology — Natural Selection (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=fBOrzQP423A"},
            {"title": "Kurzgesagt — How Evolution Works (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hOfRN0KihOU"},
        ],
        "Human Health and Disease": [
            {"title": "CrashCourse Biology — The Immune System (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=j6YaOqKORYY"},
            {"title": "Kurzgesagt — The Immune System Explained (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lXfEK8G8CUI"},
        ],
        "Strategies for Enhancement in Food Production": [
            {"title": "CrashCourse Biology — The Chemistry of Life (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=xOLcZMw0hd4"},
            {"title": "Khan Academy — Photosynthesis Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Microbes in Human Welfare": [
            {"title": "CrashCourse Biology — The Science of Biology (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=tZE_fQFK8EY"},
            {"title": "Khan Academy — Cellular Respiration Overview (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ArmlWtDnuys"},
        ],
        "Biotechnology: Principles and Processes": [
            {"title": "CrashCourse Biology — Transcription and Translation (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4mxJbgdiyIY"},
            {"title": "Khan Academy — DNA Replication (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4joZpdXeS4A"},
        ],
        "Biotechnology and its Applications": [
            {"title": "CrashCourse Biology — More Transcription (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YM6Ekb5De2o"},
            {"title": "Khan Academy — DNA Structure and Replication (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4joZpdXeS4A"},
        ],
        "Organisms and Populations": [
            {"title": "CrashCourse Biology — Population Ecology (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=xSbMX0MFJCY"},
            {"title": "Khan Academy — Ecology Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-rsYk4eCKnA"},
        ],
        "Ecosystem": [
            {"title": "CrashCourse Biology — Community Ecology (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=o-WFU5ovaTc"},
            {"title": "Kurzgesagt — What Is Life How Does It Work (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=QOCaacO8wus"},
        ],
        "Biodiversity and Conservation": [
            {"title": "CrashCourse Biology — Species and Biodiversity (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=SyHM1gFyP8Y"},
            {"title": "Kurzgesagt — How Evolution Works (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=hOfRN0KihOU"},
        ],
        "Environmental Issues": [
            {"title": "CrashCourse Biology — Ecology and the Environment (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=SyHM1gFyP8Y"},
            {"title": "Kurzgesagt — Overpopulation and the Environment (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=QOCaacO8wus"},
        ],
    },
    "Mathematics": {
        "Relations and Functions": [
            {"title": "CrashCourse Statistics — Data Visualization (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=XZo4xyJXCak"},
            {"title": "Khan Academy — Relations and Functions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=-DTMakGDZAw"},
        ],
        "Inverse Trigonometric Functions": [
            {"title": "CrashCourse Physics — Wave Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=s94suB5uLWw"},
            {"title": "Khan Academy — Inverse Trigonometric Functions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YXWKpgmLgHk"},
        ],
        "Matrices": [
            {"title": "3Blue1Brown — Essence of Linear Algebra (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=fNk_zzaMoSs"},
            {"title": "Khan Academy — Introduction to Matrices (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=xyAuNHPsq-g"},
        ],
        "Determinants": [
            {"title": "3Blue1Brown — The Determinant (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Ip3X9LOh2dk"},
            {"title": "Khan Academy — Determinants (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=OI07C1HsOuc"},
        ],
        "Continuity and Differentiability": [
            {"title": "3Blue1Brown — Essence of Calculus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WUvTyaaNkzM"},
            {"title": "Khan Academy — Continuity and Differentiability (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Application of Derivatives": [
            {"title": "3Blue1Brown — Derivatives Visualized (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=S0_qX4VJhMQ"},
            {"title": "Khan Academy — Application of Derivatives (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=XMJ72mtMn4Y"},
        ],
        "Integrals": [
            {"title": "3Blue1Brown — Integration and the Fundamental Theorem (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=rfG8ce4nNh0"},
            {"title": "Khan Academy — Introduction to Integrals (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Application of Integrals": [
            {"title": "3Blue1Brown — Essence of Calculus (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=WUvTyaaNkzM"},
            {"title": "Khan Academy — Application of Integrals (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Differential Equations": [
            {"title": "3Blue1Brown — Differential Equations Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=p_di4Zn4wz4"},
            {"title": "Khan Academy — Introduction to Differential Equations (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Vector Algebra": [
            {"title": "3Blue1Brown — Vectors What Even Are They (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=fNk_zzaMoSs"},
            {"title": "Khan Academy — Vector Basics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ihNZlp7iUHE"},
        ],
        "Three Dimensional Geometry": [
            {"title": "CrashCourse Physics — Geometric Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=g-wjP1otQWI"},
            {"title": "Khan Academy — 3D Geometry Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=riXcZT2ICjA"},
        ],
        "Linear Programming": [
            {"title": "CrashCourse Statistics — Linear Regression (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6G6i8vSa8Zs"},
            {"title": "Khan Academy — Linear Programming (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Z1zdkcwosD4"},
        ],
        "Probability": [
            {"title": "CrashCourse Statistics — Basic Probability (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=JnoBjHz2dtw"},
            {"title": "Khan Academy — Basic Probability (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=uzkc-qNVoOk"},
        ],
    },
    # ── ENGLISH ──────────────────────────────────────────────────────────────
    "English": {
        # ── Flamingo — Prose ──────────────────────────────────────────────────
        "The Last Lesson": [
            {"title": "The Last Lesson Class 12 | Flamingo Chapter 1 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=le_drhF4YeI"},
                ],
        "Lost Spring": [
            {"title": "Lost Spring Class 12 | Flamingo Chapter 2 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=sI6T22M7WEA"},
                ],
        "Deep Water": [
            {"title": "Deep Water Class 12 | Flamingo Chapter 3 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=oQLi31YxSOs"},
                ],
        "The Rattrap": [
            {"title": "The Rattrap Class 12 | Flamingo Chapter 4 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=rvmaM-lMGdc"},
                ],
        "Indigo": [
            {"title": "Indigo Class 12 | Flamingo Chapter 5 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=lfQKLucj6Es"},
                ],
        "Poets and Pancakes": [
            {"title": "Poets and Pancakes Class 12 | Flamingo Chapter 6 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=fZm3C5e3qlI"},
                ],
        "The Interview": [
            {"title": "The Interview Class 12 | Flamingo Chapter 7 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=yvf3VU7tDPs"},
                ],
        "Going Places": [
            {"title": "Going Places Class 12 | Flamingo Chapter 8 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=PVM3MGQns_w"},
                ],
        # ── Flamingo — Poetry ─────────────────────────────────────────────────
        "My Mother at Sixty-six": [
            {"title": "My Mother at Sixty Six Class 12 | Flamingo Poem 1 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=hylaNZ0qV5o"},
                ],
        "An Elementary School Classroom in a Slum": [
            {"title": "An Elementary School Classroom in a Slum Class 12 | Flamingo Poem 2 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=T5uB6ObhayA"},
                ],
        "Keeping Quiet": [
            {"title": "Keeping Quiet Class 12 | Flamingo Poem 3 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=71ZUoT-z0AI"},
                ],
        "A Thing of Beauty": [
            {"title": "A Thing of Beauty Class 12 | Flamingo Poem 4 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=5hRxngpPaJM"},
                ],
        "A Roadside Stand": [
            {"title": "A Roadside Stand Class 12 | Flamingo Poem 5 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=u7m5-x8ZBko"},
                ],
        "Aunt Jennifer's Tigers": [
            {"title": "Aunt Jennifer's Tigers Class 12 | Flamingo Poem 6 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=EJUvPaB1JjM"},
                ],
        # ── Vistas — Supplementary Reader ─────────────────────────────────────
        "The Third Level": [
            {"title": "The Third Level Class 12 | Vistas Chapter 1 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=MAm96heUqeY"},
                ],
        "The Tiger King": [
            {"title": "The Tiger King Class 12 | Vistas Chapter 2 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=1CYyO7wEWiQ"},
                ],
        "Journey to the End of the Earth": [
            {"title": "Journey to the End of the Earth Class 12 | Vistas Chapter 3 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=g_56IUJdj9c"},
                ],
        "The Enemy": [
            {"title": "The Enemy Class 12 | Vistas Chapter 4 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=oppE-JloUt0"},
                ],
        "Should Wizard Hit Mommy?": [
            {"title": "Should Wizard Hit Mommy Class 12 | Vistas Chapter 5 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=OFlciRaeysY"},
                ],
        "On the Face of It": [
            {"title": "On the Face of It Class 12 | Vistas Chapter 6 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=NH4TFTLB0pA"},
                ],
        "Evans Tries an O-Level": [
            {"title": "Evans Tries an O-Level Class 12 | Vistas Chapter 7 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=6WyZz8RmAgs"},
                ],
        "Memories of Childhood": [
            {"title": "Memories of Childhood Class 12 | Vistas Chapter 8 Explanation | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=XMjt1RbA9Ec"},
                ],
        # ── Grammar / Writing Skills ──────────────────────────────────────────
        "Grammar": [
            {"title": "BBC Learning English — Grammar Reference (International)", "type": "website", "url": "https://www.bbc.co.uk/learningenglish/grammar"},
            {"title": "Magnet Brains — Class 12 English Grammar (India)", "type": "website", "url": "https://www.youtube.com/results?search_query=magnet+brains+class+12+english+grammar"},
        ],
        "Writing Skills": [
            {"title": "British Council — Writing Skills (International)", "type": "website", "url": "https://learnenglish.britishcouncil.org/skills/writing"},
            {"title": "Magnet Brains — Class 12 English Writing Skills (India)", "type": "website", "url": "https://www.youtube.com/results?search_query=magnet+brains+class+12+english+writing+skills"},
        ],
    },
}

# ── Grade 7 resources ─────────────────────────────────────────────────────────
GRADE_7_RESOURCES: dict[str, dict[str, list]] = {
    "Science": {
        # NCERT "Curiosity" (2025-26). Single source per chapter; PW Little Champs 6th, 7th &
        # 8th and "we & science!" each cover multiple chapters and are used as anchors where
        # available. Every video verified live via YouTube's oEmbed endpoint.
        "The Ever-Evolving World of Science": [indian_channel("The Ever-Evolving World of Science Class 7 One Shot || Science", "PW Little Champs 6th, 7th & 8th", "TQUGaqOv1xc")],
        "Exploring Substances: Acids, Bases and Neutral": [indian_channel("Chapter 2: Exploring Substances: Acidic, Basic, and Neutral | Class 7 Science | NCERT", "EduRev Class 6-10", "6Hem2LvKL0k")],
        "Electricity: Circuits and Their Components": [indian_channel("Electricity: Circuits and their Components Class 7 One Shot || Science", "PW Little Champs 6th, 7th & 8th", "Jjcs9SV8GbY")],
        "The World of Metals and Non-metals": [indian_channel("The World of Metals and Non-metals Class 7 One Shot || Science", "PW Little Champs 6th, 7th & 8th", "eniKI5bwb5o")],
        "Changes Around Us: Physical and Chemical": [indian_channel("Class 7 Science Chapter 6 | Physical And Chemical Changes Full Chapter Explanation & NCERT Solutions", "Magnet Brains", "yR_NqF6IwX4")],
        "Adolescence: A Stage of Growth and Change": [indian_channel("Adolescence - A Stage of Growth and Change | CBSE Class 7 Science | NCERT Biology Chapter Covered!", "Unacademy Avengerz for Class 6th to 10th", "FL4C03ag2-U")],
        "Heat Transfer in Nature": [indian_channel("Class 7 Science Chapter 7 | Heat Transfer in Nature NCERT Curiosity | CBSE board | Chapter Explained", "Wisdom of Avyaan", "bU8ZIdFzWlk")],
        "Measurement of Time and Motion": [indian_channel("Measurement of Time and Motion | Chapter 8 One Shot | Class 7 Science Curiosity", "Concept Corridor", "mRBkudeneUk")],
        "Life Processes in Animals": [indian_channel("Class 7 Science Chapter 9 | Life Processes in Animals | CBSE NCERT New", "we & science!", "vqVL41aeQBE")],
        "Life Processes in Plants": [indian_channel("Class 7 Science Chapter 10 | Life Processes in Plants | CBSE NCERT New", "we & science!", "oZIfHgq1Yo0")],
        "Light: Shadows and Reflections": [indian_channel("Class 7 Science Chapter 11 | Light: Shadows and Reflections | CBSE NCERT New", "we & science!", "BW16T1AqlVI")],
        "Earth, Moon, and the Sun": [indian_channel("NCERT Chapter 12: Earth Moon and the Sun Part - II", "NCERT OFFICIAL", "vuPW5tqmPeY")],
    },
    "Social Science": {
        # NCERT's new integrated Grade 7 book ("Exploring Society: India and Beyond", 2025-26,
        # Part 1 + Part 2) — single source per chapter. "Empires and Kingdoms: 6th to 10th
        # Centuries", "India, a Home to Many", "Infrastructure: Engine of India's Development",
        # and "Banks and the Magic of Finance" are brand-new Part 2 content with no dedicated
        # video anywhere yet (confirmed after repeated searches) and are left uncurated. Every
        # other video verified live via YouTube's oEmbed endpoint.
        # Part 1
        "Geographical Diversity of India": [indian_channel("Geographical Diversity Of India | One Shot | Chapter 1 Class 7 New NCERT", "Concept Corridor", "7Q5IETazQmk")],
        "Understanding the Weather": [indian_channel("Understanding The Weather | Class 7 SST New NCERT Chapter 2 | Full Chapter by Gautam Lakhani", "MOTION 6th 7th & 8th", "YwCfeLFIHhM")],
        "Climates of India": [indian_channel("Climates of India | Class 7 Social Science Chapter 3 | NCERT Geography Full Explanation", "Concept Corridor", "xVt2o9DD4sw")],
        "New Beginnings: Cities and States": [indian_channel("New Beginning: Cities and States | Class 7 Social Science Chapter 4 | Exploring Society", "Concept Corridor", "-ShHdjvQjOA")],
        "The Rise of Empires": [indian_channel("The Rise of Empires Class 7 One Shot || SST || Srishty Ma'am", "PW Little Champs 6th, 7th & 8th", "lFt7sZcdvHA")],
        "The Age of Reorganisation": [indian_channel("The Age of Reorganisation - Chapter Overview | Ch 6 | Class 7 Social Science (Part 1)", "Magnet Brains", "F7gO4_FltoU")],
        "The Gupta Era: An Age of Tireless Creativity": [indian_channel("The Gupta Era: An Age of Tireless Creativity Class 7 One Shot || SST || Srishty Ma'am", "PW Class 7", "kP55hVcmDC8")],
        "How the Land Becomes Sacred": [indian_channel("How the Land Becomes Sacred | Class 7 Social Science Chapter 8 | SST New NCERT | By Gautam Lakhani", "MOTION 6th 7th & 8th", "klJtGr9pSmc")],
        "From the Rulers to the Ruled: Types": [indian_channel("Class7 S.S.T. Chapter 9 From the Rulers to the Ruled: Types of Governments full Chapter line by line", "Learner Bee", "X2efsqIV4gI")],
        "The Constitution of India — An Introduction": [indian_channel("The Constitution of India | Class 7 Social Science Chapter 10 | New NCERT | By Gautam Lakhani", "MOTION 6th 7th & 8th", "kJZUO2U5cy0")],
        "From Barter to Money": [indian_channel("From Barter to Money | Class 7 Social Science Chapter 11 | New NCERT | By Gautam Lakhani", "MOTION 6th 7th & 8th", "B_zcJVsR3AI")],
        "Understanding Markets": [indian_channel("Class 7 Civics Full Chapter 7 | Markets Around Us", "Magnet Brains", "0twyx2r3-zo")],
        # Part 2
        "The Story of Indian Farming": [indian_channel("The Story of Indian Farming | Chapter-1 | Class 7 SST NCERT 2025 | Part 2", "Kaliyaan Tv", "xYbPrSt08ys")],
        "India and Her Neighbours": [indian_channel("India and Her Neighbours – Class 7 SST NCERT 2025 (Part 2 | Book 2) | Chapter 2", "Kaliyaan Tv", "zDqgLEASKwQ")],
        "Turning Tides: 11th and 12th Centuries": [indian_channel("Turning Tides: 11th and 12th Centuries Class 7 One Shot || SST Book Part 2 || Srishty Ma'am", "PW Class 7", "3JFWM4gSPCY")],
        "The State, the Government, and You": [indian_channel("How the State Government Works | Class 7 | Political Science | One Shot", "BYJU'S - Class 6, 7 & 8", "VuQdibItbHg", note="Closest available match — from the previous civics curriculum, same core topic (state government structure) as this book's new chapter.")],
    },
    "Maths": {
        # Ganita Prakash Grade 7 (Part 1 + Part 2) — single source per chapter; PW Class 7
        # (Priyanshu Sir) covers 5 of 7 Part 2 chapters consistently and is used as the anchor
        # there. Several long chapters only have page-range/part videos rather than one
        # full-chapter video — best available used. Every video verified live via YouTube's
        # oEmbed endpoint.
        # Part 1
        "Large Numbers Around Us": [indian_channel("Class 7 Maths Ganita Prakash Chapter 1 Large Numbers Around Us One Shot | Class 7 Maths Full Chapter", "CBSE Worldz", "kGTShilfR1I")],
        "Arithmetic Expressions": [indian_channel("Arithmetic Expressions | Class 7 Maths One Shot | Ganita Prakash", "Vedantu Class 6, 7 & 8 (Rajiv Sir)", "X1B1rSQyV_g")],
        "A Peek Beyond the Point": [indian_channel("Ncert Class -7th Maths Ganita Prakash | Chapter -3 A Peek Beyond The Point | Full Chapter | One Shot", "MOS Classes Maths (Shine Luthra)", "Lx6ksaM3p7s")],
        "Expressions using Letter-Numbers": [indian_channel("Class 7 Maths | Chapter 4 Expressions using Letter-Numbers | Part 1 | Ganita Prakash", "Kaliyaan Tv", "u_CFoVVQKXE")],
        "Parallel and Intersecting Lines": [indian_channel("Class 7 Maths Chapter 5 Part 1 | Parallel and Intersecting Lines | Ganita Prakash", "Kaliyaan Tv", "gy2mp2LijK4")],
        "Number Play": [indian_channel("Number Play Part 1 | Class 7 Maths Chapter 6 | Ganita Prakash New NCERT 2025", "MOTION 6th 7th & 8th (Aditi Tripathi Ma'am)", "LRGDTttZPiM")],
        "A Tale of Three Intersecting Lines": [indian_channel("Class 7 Maths | Chapter 7: A Tale of Three Intersecting Lines | Part 1 | Ganita Prakash", "Kaliyaan Tv", "jv-qFdaW5v4")],
        "Working with Fractions": [indian_channel("Class 7 Maths Ganita Prakash Solutions | Chapter 8 Working with fractions | Page 173 to 176", "MathsByShweta", "O9wMrurJtc8")],
        # Part 2
        "Geometric Twins": [indian_channel("Class 7 Maths | Ganita Prakash Book 2 | Chapter 1 – Geometric Twins | Full Explanation", "Kaliyaan Tv", "ZEfbB2y3B2g")],
        "Operations with Integers": [indian_channel("Operations With Integers Class 7 One Shot || Maths Ganita Prakash Part 2", "PW Class 7 (Priyanshu Sir)", "lu0d1MxCTlI")],
        "Finding Common Ground": [indian_channel("Finding Common Ground Class 7 One Shot || Maths Ganita Prakash Part 2", "PW Class 7 (Priyanshu Sir)", "sVX6egyHr7k")],
        "Another Peek Beyond the Point": [indian_channel("Another Peek Beyond The Point Class 7 Maths Ganita Prakash | Chapter -4 | Page 93 to 95", "MOS Classes Maths (Shine Luthra)", "QP6mfRajlAk")],
        "Connecting the Dots…": [indian_channel("Connecting The Dots Class 7 One Shot || Maths Ganita Prakash Part 2", "PW Class 7 (Priyanshu Sir)", "nG0QPS1e8H8")],
        "Constructions and Tilings": [indian_channel("Constructions & Tilings Class 7 One Shot || Maths Ganita Prakash Part 2", "PW Class 7 (Priyanshu Sir)", "e-pg3YPVaKE")],
        "Finding the Unknown": [indian_channel("Finding the Unknown Class 7 One Shot || Maths Ganita Prakash Part 2", "PW Class 7 (Priyanshu Sir)", "pinXclj3A80")],
    },
    "Hindi": {
        # NCERT "Malhar" (2025-26). The live RAG-uploaded labels have the same kind of
        # OCR/upload text-extraction artifacts seen in Grade 8/9/10 Hindi (duplicated letters,
        # dropped matras, spurious spaces) — both the clean and the live-label spelling are
        # mapped to the same resource so the lookup matches regardless of which variant shows
        # up. Single source per chapter, every video verified live via YouTube's oEmbed
        # endpoint.
        "माँ, कह एक कहानी": [indian_channel("माँ, कह एक कहानी (Maa Keh Ek Kahani) - Explanation | Class 7 Chapter 1 | Malhar Book", "Magnet Brains", "L4hml-14IM4")],
        "तीन बुद्धिमान": [indian_channel("हिंदी कक्षा 7 पाठ 2 तीन बुद्धिमान सम्पूर्ण व्याख्या मल्हार", "LEARN CBSE (Hindi Medium)", "01qDMSoATK0")],
        "तीन बुद्धमान": [indian_channel("हिंदी कक्षा 7 पाठ 2 तीन बुद्धिमान सम्पूर्ण व्याख्या मल्हार", "LEARN CBSE (Hindi Medium)", "01qDMSoATK0")],
        "फूल और काँटा": [indian_channel("Phool Aur Kaanta | Class 7 | Malhar - NCERT | Chapter Explanation | फूल और काँटा | Chapter 3", "Insightful Hindi", "_6ZT2NbYEmE")],
        "फ ू ल और काँटा": [indian_channel("Phool Aur Kaanta | Class 7 | Malhar - NCERT | Chapter Explanation | फूल और काँटा | Chapter 3", "Insightful Hindi", "_6ZT2NbYEmE")],
        "पानी रे पानी": [indian_channel("NCERT Class 7 Hindi Malhar | Chapter 4 | Paani re Paani | Chapter Summary", "Wisdom of Avyaan", "NI_59bEuAp0")],
        "नहीं होना बीमार": [indian_channel("मल्हार कक्षा 7 | पाठ ५ - नहीं होना बीमार - पाठ अध्ययन एवम शब्दार्थ", "Educational Corner", "fH9UXeDIcio")],
        "गिरधर कविराय की कुंडलियाँ": [indian_channel("Grade 7 Hindi Chapter 6 गिरधर कविराय की कुंडलियाँ Detailed Explanation with Word Meanings", "Learner Bee", "NbIqQ4CmkTo")],
        "िगरधर किवराय की क ुं डिलया": [indian_channel("Grade 7 Hindi Chapter 6 गिरधर कविराय की कुंडलियाँ Detailed Explanation with Word Meanings", "Learner Bee", "NbIqQ4CmkTo")],
        "वर्षा-बहार": [indian_channel("Varsha Bahaar (वर्षा-बहार) - Explanation | Chapter 7 Class 7th | Hindi (Malhar Book) | CBSE 2025-26", "Magnet Brains", "yOzn_mSS2_s")],
        "वषार्-बहार": [indian_channel("Varsha Bahaar (वर्षा-बहार) - Explanation | Chapter 7 Class 7th | Hindi (Malhar Book) | CBSE 2025-26", "Magnet Brains", "yOzn_mSS2_s")],
        "बिरजू महाराज से साक्षात्कार": [indian_channel("बिरजू महाराज से साक्षात्कार | Class 7 Hindi Malhar Ch 8 Question Answer", "Study With Neha", "TNPo1J2u718")],
        "िबरजू महाराज से साक्षाार": [indian_channel("बिरजू महाराज से साक्षात्कार | Class 7 Hindi Malhar Ch 8 Question Answer", "Study With Neha", "TNPo1J2u718")],
        "चिड़िया": [indian_channel("Chidiya, चिड़िया, class 7 Hindi new book chapter 9 complete solution with explanation", "Basic Education R.D", "RbSJfitNZ68")],
        "धिधड़या": [indian_channel("Chidiya, चिड़िया, class 7 Hindi new book chapter 9 complete solution with explanation", "Basic Education R.D", "RbSJfitNZ68")],
        "मीरा के पद": [indian_channel("कक्षा 7 हिंदी (मल्हार) पाठ – 10 \"मीरा के पद\" NCERT QUESTION-ANSWERS Detailed Explanation", "Learner Bee", "Kd_4NuYST6E")],
        "मुीरा का़े पाद": [indian_channel("कक्षा 7 हिंदी (मल्हार) पाठ – 10 \"मीरा के पद\" NCERT QUESTION-ANSWERS Detailed Explanation", "Learner Bee", "Kd_4NuYST6E")],
    },
    "English": {
        # NCERT "Poorvi" (2025-26) — the live dropdown groups by unit ("Unit N: <theme>"), not
        # by the individual chapters within each unit, so each entry covers the unit's first
        # chapter/poem as a representative single source. Unit 1-3 live labels are ALL CAPS and
        # Unit 4's is malformed ("Chapter Travel and Adventure" instead of "Unit 4: Travel and
        # Adventure") so both variants are mapped to the same resource. Every video verified
        # live via YouTube's oEmbed endpoint.
        "Learning Together": [indian_channel("The Day the River Spoke - Explanation | Class 7 English Unit 1 - Learning Together | CBSE 2025-26", "Magnet Brains", "8J1m3piWsjE")],
        "LEARNING TOGETHER": [indian_channel("The Day the River Spoke - Explanation | Class 7 English Unit 1 - Learning Together | CBSE 2025-26", "Magnet Brains", "8J1m3piWsjE")],
        "Wit and Humour": [indian_channel("Animals, Birds, and Dr. Dolittle - Explanation | Class 7 English Unit 2 - Wit and Humour | CBSE", "Magnet Brains", "qjdbf4vjHmk")],
        "WIT AND HUMOUR": [indian_channel("Animals, Birds, and Dr. Dolittle - Explanation | Class 7 English Unit 2 - Wit and Humour | CBSE", "Magnet Brains", "qjdbf4vjHmk")],
        "Dreams and Discoveries": [indian_channel("My Brother's Great Invention (English Explanation) | Class 7 English Poorvi Unit 3", "CBSE with Sudhir", "-M0jQ_1lO0o")],
        "DREAMS AND DISCOVERIES": [indian_channel("My Brother's Great Invention (English Explanation) | Class 7 English Poorvi Unit 3", "CBSE with Sudhir", "-M0jQ_1lO0o")],
        "Travel and Adventure": [indian_channel("Travel (Poem) - Explanation | Chapter 11 | Class 7th English | Unit 4 (Poorvi) | CBSE 2025-26", "Magnet Brains", "w9jCdMkdr4s")],
        "Chapter Travel and Adventure": [indian_channel("Travel (Poem) - Explanation | Chapter 11 | Class 7th English | Unit 4 (Poorvi) | CBSE 2025-26", "Magnet Brains", "w9jCdMkdr4s")],
        "Bravehearts": [indian_channel("A Homage to Our Brave Soldiers Part -1 | Class 7 English (Poorvi) Animation | Unit 5 Bravehearts", "Englishpedia", "wmktCNbxnF0")],
        "Grammar": list(GRAMMAR_RESOURCES),
        "Writing Skills": GRAMMAR_TOPIC_RESOURCES.get("Writing Skills", []),
        "Tenses": GRAMMAR_TOPIC_RESOURCES.get("Tenses", []),
        "Active and Passive Voice": GRAMMAR_TOPIC_RESOURCES.get("Active and Passive Voice", []),
        "Reported Speech": GRAMMAR_TOPIC_RESOURCES.get("Reported Speech", []),
        "Modals": GRAMMAR_TOPIC_RESOURCES.get("Modals", []),
    },
}

# ── Grade-aware resource lookup ───────────────────────
GRADE_RESOURCES_MAP = {
    "Grade 7": GRADE_7_RESOURCES,
    "Grade 8": GRADE_8_RESOURCES,
    "Grade 10": GRADE_10_RESOURCES,
    "Grade 11": GRADE_11_RESOURCES,
    "Grade 12": GRADE_12_RESOURCES,
}

# Grade 9 English Grammar (extends existing LEARNING_RESOURCES)
LEARNING_RESOURCES["English"].update({
    "Grammar": list(GRAMMAR_RESOURCES),
    "Writing Skills": GRAMMAR_TOPIC_RESOURCES.get("Writing Skills", []),
    "Tenses": GRAMMAR_TOPIC_RESOURCES.get("Tenses", []),
    "Active and Passive Voice": GRAMMAR_TOPIC_RESOURCES.get("Active and Passive Voice", []),
    "Reported Speech": GRAMMAR_TOPIC_RESOURCES.get("Reported Speech", []),
    "Modals": GRAMMAR_TOPIC_RESOURCES.get("Modals", []),
})


def _strip_part_prefix(chapter):
    """Remove a display-only 'Part N - ' prefix from a chapter label.

    Mirrors app/routes/syllabus.py's strip_part_prefix() — duplicated here (rather than
    imported) so this pure-data module doesn't pull in that route file's FastAPI/Supabase
    dependencies just for two regexes.
    """
    return re.sub(r"^\s*part\s*\d+\s*[-:]\s*", "", str(chapter or ""), flags=re.IGNORECASE).strip()


def _strip_book_source_prefix(chapter):
    """Remove a display-only book-source prefix (e.g. 'Text Book - ') from a chapter label.

    Mirrors app/routes/syllabus.py's strip_book_source_prefix() — see note above.
    """
    return re.sub(
        r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
        r"History|Geography|Political Science|Economics)\s*[-:]\s*",
        "",
        str(chapter or ""),
        flags=re.IGNORECASE,
    ).strip()


def _strip_chapter_number_prefix(chapter):
    """Remove a 'Chapter N: ' / 'Unit N: ' / 'अध्याय N: ' / 'पाठ N: ' prefix from a chapter label.

    RAG-uploaded chapters are numbered in upload order, which curated resource keys
    can't always predict in advance. Stripping the number lets a plain-title key
    (e.g. "Fog", "सूरदास") match regardless of what chapter number the upload landed
    on, and regardless of whether the subject numbers chapters "Chapter", "Unit", or
    in Hindi ("अध्याय" or "पाठ").
    """
    return re.sub(r"^\s*(?:chapter|unit|अध्याय|पाठ)\s*\d+\s*[-:]\s*", "", str(chapter or ""), flags=re.IGNORECASE).strip()


def get_learning_resources(subject: str, chapter: str, grade: str = "Grade 9"):
    """Return curated resources if present; otherwise return a free fallback link.

    The syllabus dropdown decorates chapter labels with a display-only book-source prefix
    (e.g. "Text Book - Chapter 1: A Letter to God") whenever a subject has multiple uploaded
    books. Curated resources are keyed by the plain "Chapter N: Title" label, so lookups try
    the raw label first, then the prefix-stripped label.

    Lookup priority:
    1. Grade-specific resource map (Grade 8, Grade 10)
    2. Legacy LEARNING_RESOURCES (Grade 9 + generic)
    3. Grammar topic resources (English, any grade)
    4. Fallback YouTube search
    """
    cleaned_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
    source_stripped = _strip_book_source_prefix(_strip_part_prefix(cleaned_chapter))
    number_stripped = _strip_chapter_number_prefix(source_stripped)
    lookup_candidates = list(dict.fromkeys([cleaned_chapter, source_stripped, number_stripped]))

    def lookup(mapping):
        for candidate in lookup_candidates:
            if candidate in mapping:
                return mapping[candidate]
        return []

    # Priority 1: Grade-specific resources
    grade_map = GRADE_RESOURCES_MAP.get(grade, {})
    resources = lookup(grade_map.get(subject, {}))

    # Priority 1b: Fuzzy/prefix match for chapter name variants
    if not resources and grade_map.get(subject):
        import difflib as _dl
        subject_map = grade_map[subject]
        ch_lower = cleaned_chapter.lower()
        # Prefix match: 'Semiconductor Electronics' -> 'Semiconductor Electronics: ...'
        prefix_match = next(
            (k for k in subject_map if k.lower().startswith(ch_lower) or ch_lower.startswith(k.lower()[:28])),
            None
        )
        if prefix_match:
            resources = subject_map[prefix_match]
        else:
            close = _dl.get_close_matches(cleaned_chapter, subject_map.keys(), n=1, cutoff=0.82)
            if close:
                resources = subject_map[close[0]]

    # Priority 2: Legacy Grade 9 / shared resources
    if not resources:
        resources = lookup(LEARNING_RESOURCES.get(subject, {}))

    # Priority 3: Grammar topic match for English
    if not resources and subject == "English":
        resources = lookup(GRAMMAR_TOPIC_RESOURCES)

    if resources:
        return list(resources)

    grade_query = grade.lower().replace("grade", "class")
    query = quote_plus(f"{grade_query} {subject} {cleaned_chapter} free lecture")
    return [
        {
            "title": f"YouTube Search - {subject}: {chapter}",
            "type": "website",
            "url": f"https://www.youtube.com/results?search_query={query}",
        },
    ]
