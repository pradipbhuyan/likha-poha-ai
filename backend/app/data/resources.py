"""
Free learning resources for the Grade 9 CBSE tutor app.

Use get_learning_resources(subject, chapter) in app.py so every chapter shows
curated links when available and safe fallback links otherwise.
"""
from urllib.parse import quote_plus

NCERT_RESOURCE = {
    "title": "NCERT Official Textbooks",
    "type": "website",
    "url": "https://ncert.nic.in/textbook.php",
}

FREE_COMMON_RESOURCES = [
    NCERT_RESOURCE,
    {
        "title": "PhET Free Science and Maths Simulations",
        "type": "website",
        "url": "https://phet.colorado.edu/",
    },
]


def add_ncert_link(resources):
    """Ensure every resource list includes NCERT in second position."""
    filtered = [
        resource
        for resource in resources
        if resource.get("url") != NCERT_RESOURCE["url"]
    ]

    if not filtered:
        return [NCERT_RESOURCE]

    return [filtered[0], NCERT_RESOURCE, *filtered[1:]]

LEARNING_RESOURCES = {
    "Science": {
        "Exploration: Entering the World of Secondary Science": [
            {
                "title": "LikhapohaAI - Exploration: Entering the World of Secondary Science",
                "type": "youtube",
                "url": "https://youtu.be/egb7zve36RY",
            },
        ],
        "Chapter 1: Exploration: Entering the World of Secondary Science": [
            {
                "title": "LikhapohaAI - Exploration: Entering the World of Secondary Science",
                "type": "youtube",
                "url": "https://youtu.be/egb7zve36RY",
            },
        ],
        "Matter in Our Surroundings": [
            {"title": "YouTube Search - Class 9 Matter in Our Surroundings", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+matter+in+our+surroundings+full+chapter"},
        ],
        "Is Matter Around Us Pure": [
            {"title": "LikhaPoha AI - Is Matter Around Us Pure | Class 9 Science Chapter 2", "type": "youtube", "url": "https://youtu.be/kADIaUbwL00"},
        ],
        "Atoms and Molecules": [
            {"title": "LikhaPoha AI - Atoms and Molecules | Class 9 Science Chapter 3", "type": "youtube", "url": "https://youtu.be/yJk4ZeSr9Bk"},
        ],
        # RAG-uploaded chapter label variants (chapter name as stored in Supabase rag_documents)
        "Cell: The Building Block of Life": [
            {"title": "LikhaPoha AI - Cell: The Building Block of Life | Class 9 Science Chapter 2", "type": "youtube", "url": "https://youtu.be/kADIaUbwL00"},
        ],
        "Chapter 2: Cell: The Building Block of Life": [
            {"title": "LikhaPoha AI - Cell: The Building Block of Life | Class 9 Science Chapter 2", "type": "youtube", "url": "https://youtu.be/kADIaUbwL00"},
        ],
        "Tissues in Action": [
            {"title": "LikhaPoha AI - Tissues in Action | Class 9 Science Chapter 3", "type": "youtube", "url": "https://youtu.be/yJk4ZeSr9Bk"},
        ],
        "Chapter 3: Tissues in Action": [
            {"title": "LikhaPoha AI - Tissues in Action | Class 9 Science Chapter 3", "type": "youtube", "url": "https://youtu.be/yJk4ZeSr9Bk"},
        ],
        "Describing Motion Around Us": [
            {"title": "LikhaPoha AI - Describing Motion Around Us | Class 9 Science Chapter 4", "type": "youtube", "url": "https://youtu.be/___wVgKghMA"},
        ],
        "Chapter 4: Describing Motion Around Us": [
            {"title": "LikhaPoha AI - Describing Motion Around Us | Class 9 Science Chapter 4", "type": "youtube", "url": "https://youtu.be/___wVgKghMA"},
        ],
        "Exploring Mixtures and Their Separation": [
            {"title": "LikhaPoha AI - Exploring Mixtures and Their Separation | Class 9 Science Chapter 5", "type": "youtube", "url": "https://youtu.be/1FS2LCZXd_A"},
        ],
        "Chapter 5: Exploring Mixtures and Their Separation": [
            {"title": "LikhaPoha AI - Exploring Mixtures and Their Separation | Class 9 Science Chapter 5", "type": "youtube", "url": "https://youtu.be/1FS2LCZXd_A"},
        ],
        "How Forces Affect Motion": [
            {"title": "LikhaPoha AI - How Forces Affect Motion | Class 9 Science Chapter 6", "type": "youtube", "url": "https://youtu.be/7Zd3nj4wZAE"},
        ],
        "Chapter 6: How Forces Affect Motion": [
            {"title": "LikhaPoha AI - How Forces Affect Motion | Class 9 Science Chapter 6", "type": "youtube", "url": "https://youtu.be/7Zd3nj4wZAE"},
        ],
        "Work, Energy, and Simple Machines": [
            {"title": "LikhaPoha AI - Work, Energy, and Simple Machines | Class 9 Science Chapter 7", "type": "youtube", "url": "https://youtu.be/LxluQchwS54"},
        ],
        "Chapter 7: Work, Energy, and Simple Machines": [
            {"title": "LikhaPoha AI - Work, Energy, and Simple Machines | Class 9 Science Chapter 7", "type": "youtube", "url": "https://youtu.be/LxluQchwS54"},
        ],
        "Journey Inside the Atom": [
            {"title": "LikhaPoha AI - Journey Inside the Atom | Class 9 Science Chapter 8", "type": "youtube", "url": "https://youtu.be/9b-4THbqIT0"},
        ],
        "Chapter 8: Journey Inside the Atom": [
            {"title": "LikhaPoha AI - Journey Inside the Atom | Class 9 Science Chapter 8", "type": "youtube", "url": "https://youtu.be/9b-4THbqIT0"},
        ],
        "Atomic Foundations of Matter": [
            {"title": "LikhaPoha AI - Atomic Foundations of Matter | Class 9 Science Chapter 9", "type": "youtube", "url": "https://youtu.be/AaEejyJllkk"},
        ],
        "Chapter 9: Atomic Foundations of Matter": [
            {"title": "LikhaPoha AI - Atomic Foundations of Matter | Class 9 Science Chapter 9", "type": "youtube", "url": "https://youtu.be/AaEejyJllkk"},
        ],
        "Sound Waves: Characteristics and Applications": [
            {"title": "LikhaPoha AI - Sound Waves: Characteristics and Applications | Class 9 Science Chapter 10", "type": "youtube", "url": "https://youtu.be/JgfIbwip9UI"},
        ],
        "Chapter 10: Sound Waves: Characteristics and Applications": [
            {"title": "LikhaPoha AI - Sound Waves: Characteristics and Applications | Class 9 Science Chapter 10", "type": "youtube", "url": "https://youtu.be/JgfIbwip9UI"},
        ],
        "Reproduction: How Life Continues": [
            {"title": "LikhaPoha AI - Reproduction: How Life Continues | Class 9 Science Chapter 11", "type": "youtube", "url": "https://youtu.be/pTJ634ebToQ"},
        ],
        "Chapter 11: Reproduction: How Life Continues": [
            {"title": "LikhaPoha AI - Reproduction: How Life Continues | Class 9 Science Chapter 11", "type": "youtube", "url": "https://youtu.be/pTJ634ebToQ"},
        ],
        "Patterns in Life: Diversity and Classification": [
            {"title": "LikhaPoha AI - Patterns in Life: Diversity and Classification | Class 9 Science Chapter 12", "type": "youtube", "url": "https://youtu.be/VHg5evqi4yU"},
        ],
        "Chapter 12: Patterns in Life: Diversity and Classification": [
            {"title": "LikhaPoha AI - Patterns in Life: Diversity and Classification | Class 9 Science Chapter 12", "type": "youtube", "url": "https://youtu.be/VHg5evqi4yU"},
        ],
        "Earth as a System: Energy, Matter, and Life": [
            {"title": "LikhaPoha AI - Earth as a System | Class 9 Science Chapter 13", "type": "youtube", "url": "https://youtu.be/RRbu9RttTiY"},
        ],
        "Chapter 13: Earth as a System: Energy, Matter, and Life": [
            {"title": "LikhaPoha AI - Earth as a System | Class 9 Science Chapter 13", "type": "youtube", "url": "https://youtu.be/RRbu9RttTiY"},
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
    },
    "Maths": {
        # RAG-uploaded chapter labels (Chapter N: Title format from Supabase)
        "Orienting Yourself: The Use of Coordinates": [
            {"title": "LikhaPoha AI - Orienting Yourself: The Use of Coordinates | Class 9 Maths Chapter 1", "type": "youtube", "url": "https://youtu.be/n8qXaymOsAs"},
        ],
        "Chapter 1: Orienting Yourself: The Use of Coordinates": [
            {"title": "LikhaPoha AI - Orienting Yourself: The Use of Coordinates | Class 9 Maths Chapter 1", "type": "youtube", "url": "https://youtu.be/n8qXaymOsAs"},
        ],
        "Introduction to Linear Polynomials": [
            {"title": "LikhaPoha AI - Introduction to Linear Polynomials | Class 9 Maths Chapter 2", "type": "youtube", "url": "https://youtu.be/l3_lnTLvNQI"},
        ],
        "Chapter 2: Introduction to Linear Polynomials": [
            {"title": "LikhaPoha AI - Introduction to Linear Polynomials | Class 9 Maths Chapter 2", "type": "youtube", "url": "https://youtu.be/l3_lnTLvNQI"},
        ],
        "The World of Numbers": [
            {"title": "LikhaPoha AI - The World of Numbers | Class 9 Maths Chapter 3", "type": "youtube", "url": "https://youtu.be/_XLwB8P9m_4"},
        ],
        "Chapter 3: The World of Numbers": [
            {"title": "LikhaPoha AI - The World of Numbers | Class 9 Maths Chapter 3", "type": "youtube", "url": "https://youtu.be/_XLwB8P9m_4"},
        ],
        "Exploring Algebraic Identities": [
            {"title": "LikhaPoha AI - Exploring Algebraic Identities | Class 9 Maths Chapter 4", "type": "youtube", "url": "https://youtu.be/H0eyj1U1DCg"},
        ],
        "Chapter 4: Exploring Algebraic Identities": [
            {"title": "LikhaPoha AI - Exploring Algebraic Identities | Class 9 Maths Chapter 4", "type": "youtube", "url": "https://youtu.be/H0eyj1U1DCg"},
        ],
        "I'm Up and Down, and Round and Round": [
            {"title": "LikhaPoha AI - I'm Up and Down, and Round and Round | Class 9 Maths Chapter 5", "type": "youtube", "url": "https://youtu.be/SPtGjVEAXrs"},
        ],
        "Chapter 5: I'm Up and Down, and Round and Round": [
            {"title": "LikhaPoha AI - I'm Up and Down, and Round and Round | Class 9 Maths Chapter 5", "type": "youtube", "url": "https://youtu.be/SPtGjVEAXrs"},
        ],
        # Curly apostrophe variant (U+2019) — as stored in Supabase rag_documents
        "I\u2019m Up and Down, and Round and Round": [
            {"title": "LikhaPoha AI - I'm Up and Down, and Round and Round | Class 9 Maths Chapter 5", "type": "youtube", "url": "https://youtu.be/SPtGjVEAXrs"},
        ],
        "Chapter 5: I\u2019m Up and Down, and Round and Round": [
            {"title": "LikhaPoha AI - I'm Up and Down, and Round and Round | Class 9 Maths Chapter 5", "type": "youtube", "url": "https://youtu.be/SPtGjVEAXrs"},
        ],
        "Measuring Space: Perimeter and Area": [
            {"title": "LikhaPoha AI - Measuring Space: Perimeter and Area | Class 9 Maths Chapter 6", "type": "youtube", "url": "https://youtu.be/yQk7eNc1pbs"},
        ],
        "Chapter 6: Measuring Space: Perimeter and Area": [
            {"title": "LikhaPoha AI - Measuring Space: Perimeter and Area | Class 9 Maths Chapter 6", "type": "youtube", "url": "https://youtu.be/yQk7eNc1pbs"},
        ],
        "The Mathematics of Maybe: Introduction to Probability": [
            {"title": "LikhaPoha AI - The Mathematics of Maybe: Introduction to Probability | Class 9 Maths Chapter 7", "type": "youtube", "url": "https://youtu.be/N8q2adCIBRU"},
        ],
        "Chapter 7: The Mathematics of Maybe: Introduction to Probability": [
            {"title": "LikhaPoha AI - The Mathematics of Maybe: Introduction to Probability | Class 9 Maths Chapter 7", "type": "youtube", "url": "https://youtu.be/N8q2adCIBRU"},
        ],
        "Predicting What Comes Next: Exploring Sequences and Progressions": [
            {"title": "LikhaPoha AI - Predicting What Comes Next | Class 9 Maths Chapter 8", "type": "youtube", "url": "https://youtu.be/GKMvXRoJKOI"},
        ],
        "Chapter 8: Predicting What Comes Next: Exploring Sequences and Progressions": [
            {"title": "LikhaPoha AI - Predicting What Comes Next | Class 9 Maths Chapter 8", "type": "youtube", "url": "https://youtu.be/GKMvXRoJKOI"},
        ],
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
    },
    "English": {},
    "Social Science": {},
    "Hindi": {},
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
        LEARNING_RESOURCES[_subject].setdefault(_chapter, add_ncert_link([
            {"title": f"YouTube Search - {_chapter}", "type": "website", "url": f"https://www.youtube.com/results?search_query={q}"},
        ]))


for _subject in LEARNING_RESOURCES:
    for _chapter in LEARNING_RESOURCES[_subject]:
        LEARNING_RESOURCES[_subject][_chapter] = add_ncert_link(
            LEARNING_RESOURCES[_subject][_chapter]
        )


# ── NCERT Exemplar Problem links (Grade 8, 9, 10) ────────────────────────────
# These are grade-level resources — shown for any chapter of the subject.
# Direct PDFs verified from ncert.nic.in/exemplar-problems.php (June 2026)

NCERT_EXEMPLAR_BASE = "https://ncert.nic.in/pdf/publication/exemplarproblem"

EXEMPLAR_GRADE_RESOURCES = {
    "Grade 8": {
        "Maths": {
            "title": "NCERT Exemplar Problems — Class 8 Mathematics",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classVIII/mathematics/heep201.pdf",
            "description": "13 units of practice problems with solutions (NCERT official)",
        },
        "Science": {
            "title": "NCERT Exemplar Problems — Class 8 Science",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classVIII/science/heep101.pdf",
            "description": "18 chapters of practice problems with solutions (NCERT official)",
        },
    },
    "Grade 9": {
        "Maths": {
            "title": "NCERT Exemplar Problems — Class 9 Mathematics",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classIX/mathematics/ieep201.pdf",
            "description": "16 units covering all Class 9 Maths topics (NCERT official)",
        },
        "Science": {
            "title": "NCERT Exemplar Problems — Class 9 Science",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classIX/science/ieep101.pdf",
            "description": "17 chapters of higher-order problems with solutions (NCERT official)",
        },
    },
    "Grade 10": {
        "Maths": {
            "title": "NCERT Exemplar Problems — Class 10 Mathematics",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classX/mathematics/jeep201.pdf",
            "description": "15 units of board-exam level problems with solutions (NCERT official)",
        },
        "Science": {
            "title": "NCERT Exemplar Problems — Class 10 Science",
            "type": "website",
            "url": f"{NCERT_EXEMPLAR_BASE}/classX/science/jeep101.pdf",
            "description": "18 chapters of practice problems including MCQs (NCERT official)",
        },
    },
}

# Full exemplar book page (browse all units)
EXEMPLAR_PAGE = {
    "title": "NCERT Exemplar Problems — Browse All",
    "type": "website",
    "url": "https://ncert.nic.in/exemplar-problems.php",
}

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
        "title": "NCERT English Textbook (Honeydew / Beehive / First Flight)",
        "type": "website",
        "url": "https://ncert.nic.in/textbook.php",
        "description": "Official NCERT English textbooks — grammar sections included",
    },
    {
        "title": "CBSE Sample Papers — English",
        "type": "website",
        "url": "https://cbseacademic.nic.in/SampleQuestion_Papers.html",
        "description": "Grammar questions from official CBSE sample papers",
    },
]

# Grammar topic links per CBSE Grade 8-10 syllabus
GRAMMAR_TOPIC_RESOURCES = {
    "Tenses": [
        {"title": "BBC — Tenses Overview", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/grammar/b1-b2-grammar/tenses"},
        {"title": "British Council — Tenses", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/tenses"},
    ],
    "Active and Passive Voice": [
        {"title": "BBC — Passive Voice", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/grammar/b1-b2-grammar/active-and-passive-voice"},
        {"title": "British Council — Passive Voice", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b2-c1-grammar/passive-voice-introduction"},
    ],
    "Reported Speech": [
        {"title": "BBC — Reported Speech", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/grammar/b1-b2-grammar/reported-speech"},
        {"title": "British Council — Reported Speech", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/reported-speech"},
    ],
    "Modals": [
        {"title": "BBC — Modal Verbs", "type": "website",
         "url": "https://www.bbc.co.uk/learningenglish/grammar/b1-b2-grammar/modals"},
        {"title": "British Council — Modal Verbs", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/grammar/b1-b2-grammar/modal-verbs"},
    ],
    "Grammar": [
        *GRAMMAR_RESOURCES[:2],
        {"title": "CBSE English Grammar — Sample Papers", "type": "website",
         "url": "https://cbseacademic.nic.in/SampleQuestion_Papers.html"},
    ],
    "Writing Skills": [
        {"title": "British Council — Writing Skills", "type": "website",
         "url": "https://learnenglish.britishcouncil.org/skills/writing"},
        {"title": "CBSE English Writing — Sample Papers", "type": "website",
         "url": "https://cbseacademic.nic.in/SampleQuestion_Papers.html"},
    ],
}

# ── Grade 8 resources ─────────────────────────────────────────────────────────
GRADE_8_RESOURCES: dict[str, dict[str, list]] = {
    "Maths": {
        # Ganita Prakash Grade 8 chapters (NEW curriculum)
        "A Square and a Cube": [
            {"title": "NCERT Ganita Prakash Grade 8 — A Square and a Cube", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp101.pdf"},
        ],
        "Power Play": [
            {"title": "NCERT Ganita Prakash Grade 8 — Power Play", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp102.pdf"},
        ],
        "A Story of Numbers": [
            {"title": "NCERT Ganita Prakash Grade 8 — A Story of Numbers", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp103.pdf"},
        ],
        "Quadrilaterals": [
            {"title": "NCERT Ganita Prakash Grade 8 — Quadrilaterals", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp104.pdf"},
        ],
        "Number Play": [
            {"title": "NCERT Ganita Prakash Grade 8 — Number Play", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp105.pdf"},
        ],
        "We Distribute, Yet Things Multiply": [
            {"title": "NCERT Ganita Prakash Grade 8 — We Distribute Yet Things Multiply", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp106.pdf"},
        ],
        "Fractions in Disguise": [
            {"title": "NCERT Ganita Prakash Grade 8 Part 2 — Fractions in Disguise", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp201.pdf"},
        ],
        "The Baudhayana-Pythagoras Theorem": [
            {"title": "NCERT Ganita Prakash Grade 8 Part 2 — Baudhayana-Pythagoras Theorem", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp202.pdf"},
        ],
        "Proportional Reasoning-2": [
            {"title": "NCERT Ganita Prakash Grade 8 Part 2 — Proportional Reasoning", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hegp203.pdf"},
        ],
    },
    "Science": {
        "Exploring the Investigative World of Science": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 1", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu101.pdf"},
        ],
        "The Invisible Living World: Beyond Our Naked Eye": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 2", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu102.pdf"},
        ],
        "Health: the Ultimate Treasure": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 3", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu103.pdf"},
        ],
        "Electricity: Magnetic and Heating Effects": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 4", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu104.pdf"},
        ],
        "Exploring Forces": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 5", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu105.pdf"},
        ],
        "Pressure, Winds, Storms, and Cyclones": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 6", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu106.pdf"},
        ],
        "Reaching the Age of Adolescence": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 7", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu107.pdf"},
        ],
        "Our Changing Earth": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 8", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu108.pdf"},
        ],
        "Chemical Reactions and Equations": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 9", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu109.pdf"},
        ],
        "Stars and the Solar System": [
            {"title": "NCERT Curiosity Science Grade 8 — Chapter 10", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/hecu110.pdf"},
        ],
    },
    "English": {
        "Grammar": list(GRAMMAR_RESOURCES),
        "Writing Skills": GRAMMAR_TOPIC_RESOURCES.get("Writing Skills", []),
        "Tenses": GRAMMAR_TOPIC_RESOURCES.get("Tenses", []),
        "Active and Passive Voice": GRAMMAR_TOPIC_RESOURCES.get("Active and Passive Voice", []),
        "Reported Speech": GRAMMAR_TOPIC_RESOURCES.get("Reported Speech", []),
        "Modals": GRAMMAR_TOPIC_RESOURCES.get("Modals", []),
    },
}

# ── Grade 10 resources ────────────────────────────────────────────────────────
GRADE_10_RESOURCES: dict[str, dict[str, list]] = {
    "Maths": {
        "Real Numbers": [
            {"title": "NCERT Mathematics Grade 10 — Real Numbers", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh101.pdf"},
        ],
        "Polynomials": [
            {"title": "NCERT Mathematics Grade 10 — Polynomials", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh102.pdf"},
        ],
        "Pair of Linear Equations in Two Variables": [
            {"title": "NCERT Mathematics Grade 10 — Pair of Linear Equations", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh103.pdf"},
        ],
        "Quadratic Equations": [
            {"title": "NCERT Mathematics Grade 10 — Quadratic Equations", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh104.pdf"},
        ],
        "Arithmetic Progressions": [
            {"title": "NCERT Mathematics Grade 10 — Arithmetic Progressions", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh105.pdf"},
        ],
        "Triangles": [
            {"title": "NCERT Mathematics Grade 10 — Triangles", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh106.pdf"},
        ],
        "Coordinate Geometry": [
            {"title": "NCERT Mathematics Grade 10 — Coordinate Geometry", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh107.pdf"},
        ],
        "Introduction to Trigonometry": [
            {"title": "NCERT Mathematics Grade 10 — Introduction to Trigonometry", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh108.pdf"},
        ],
        "Circles": [
            {"title": "NCERT Mathematics Grade 10 — Circles", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh110.pdf"},
        ],
        "Statistics": [
            {"title": "NCERT Mathematics Grade 10 — Statistics", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh113.pdf"},
        ],
        "Probability": [
            {"title": "NCERT Mathematics Grade 10 — Probability", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jemh114.pdf"},
        ],
    },
    "Science": {
        "Chemical Reactions and Equations": [
            {"title": "NCERT Science Grade 10 — Chemical Reactions", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc101.pdf"},
        ],
        "Acids, Bases and Salts": [
            {"title": "NCERT Science Grade 10 — Acids, Bases and Salts", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc102.pdf"},
        ],
        "Metals and Non-metals": [
            {"title": "NCERT Science Grade 10 — Metals and Non-metals", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc103.pdf"},
        ],
        "Life Processes": [
            {"title": "NCERT Science Grade 10 — Life Processes", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc105.pdf"},
        ],
        "Control and Coordination": [
            {"title": "NCERT Science Grade 10 — Control and Coordination", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc106.pdf"},
        ],
        "Heredity": [
            {"title": "NCERT Science Grade 10 — Heredity", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc108.pdf"},
        ],
        "Light – Reflection and Refraction": [
            {"title": "NCERT Science Grade 10 — Light Reflection and Refraction", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc109.pdf"},
        ],
        "Electricity": [
            {"title": "NCERT Science Grade 10 — Electricity", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc111.pdf"},
        ],
        "Our Environment": [
            {"title": "NCERT Science Grade 10 — Our Environment", "type": "website",
             "url": "https://ncert.nic.in/textbook/pdf/jesc113.pdf"},
        ],
    },
    "English": {
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
}



# ── Grade 12 resources ────────────────────────────────────────────────────────────────────────
GRADE_12_RESOURCES: dict[str, dict[str, list]] = {
    "Physics": {
        "Electric Charges and Fields": [
            {"title": "CrashCourse Physics — Electric Charge (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=6BHbJ_gBOk0"},
            {"title": "Khan Academy — Electric Charge and Electric Force (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YG4_4n46Scc"},
        ],
        "Electrostatic Potential and Capacitance": [
            {"title": "CrashCourse Physics — Electric Potential (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=tuSC0ObB-qY"},
            {"title": "Khan Academy — Electric Potential Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=zqGvUbvVQXg"},
        ],
        "Current Electricity": [
            {"title": "CrashCourse Physics — Electric Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=4i1MUWJoI0U"},
            {"title": "Khan Academy — Introduction to Electric Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=YSX9-vkMhLY"},
        ],
        "Moving Charges and Magnetism": [
            {"title": "CrashCourse Physics — Magnetism (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TFlVWf8JX4A"},
            {"title": "Khan Academy — Magnetic Force on Moving Charge (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=uFqEXHECvO0"},
        ],
        "Magnetism and Matter": [
            {"title": "CrashCourse Physics — Magnetism (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=TFlVWf8JX4A"},
            {"title": "Khan Academy — Magnetic Force on Current Carrying Wire (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=qYkqXq9CZNY"},
        ],
        "Electromagnetic Induction": [
            {"title": "CrashCourse Physics — Electromagnetic Induction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=mdulzEfQXDE"},
            {"title": "Khan Academy — Introduction to Electromagnetic Induction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=LqFLmqMFKGM"},
        ],
        "Alternating Current": [
            {"title": "CrashCourse Physics — AC Circuits (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=ZrMltpK6iAw"},
            {"title": "Khan Academy — AC Circuits and Alternating Current (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=uoFB4kJsIko"},
        ],
        "Electromagnetic Waves": [
            {"title": "CrashCourse Physics — Electromagnetic Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=HXOok3mfMLM"},
            {"title": "Khan Academy — Introduction to Electromagnetic Waves (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=FMVD-D65-l8"},
        ],
        "Ray Optics and Optical Instruments": [
            {"title": "CrashCourse Physics — Geometric Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=g-wjP1otQWI"},
            {"title": "Khan Academy — Reflection and Refraction of Light (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=DveX84Rszjo"},
        ],
        "Wave Optics": [
            {"title": "CrashCourse Physics — Wave Optics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=s94suB5uLWw"},
            {"title": "Khan Academy — Young Double Slit Experiment (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Iuv6hY6zsd0"},
        ],
        "Dual Nature of Radiation and Matter": [
            {"title": "CrashCourse Physics — Quantum Mechanics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=7kb1VT0J3DE"},
            {"title": "Khan Academy — Photoelectric Effect (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=v-1zjsqaAoE"},
        ],
        "Atoms": [
            {"title": "CrashCourse Physics — Nuclear Physics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=K40lNL3KsJ4"},
            {"title": "Khan Academy — Bohr Model of Hydrogen (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=GD1NJ7HFO6s"},
        ],
        "Nuclei": [
            {"title": "CrashCourse Physics — Radioactivity (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lUhJL7o6_cA"},
            {"title": "Khan Academy — Nuclear Binding Energy (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=LLBZ3Ec_Sro"},
        ],
        "Semiconductor Electronics: Materials, Devices and Simple Circuits": [
            {"title": "CrashCourse Physics — Quantum Mechanics (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=qO_W70VegbQ"},
            {"title": "Khan Academy — Semiconductors Introduction (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=DvkE48qW6iY"},
        ],
    },
    "Chemistry": {
        "The Solid State": [
            {"title": "CrashCourse Chemistry — Solids (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=LS67vS10O5Y"},
            {"title": "Khan Academy — Solids Liquids and Gases (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=pKvo0XWZtjo"},
        ],
        "Solutions": [
            {"title": "CrashCourse Chemistry — Solutions (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=JbqtqCunYzA"},
            {"title": "Khan Academy — Solutions and Mixtures (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=3ROWXs3jtBU"},
        ],
        "Electrochemistry": [
            {"title": "CrashCourse Chemistry — Electrochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=a8LF7JEb0IA"},
            {"title": "Khan Academy — Introduction to Electrochemistry (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=lQ6FBA1HM3s"},
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
            {"title": "Khan Academy — Introduction to Matrices (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=kqWCgIVDRBo"},
        ],
        "Determinants": [
            {"title": "3Blue1Brown — Determinant of a Matrix (International)", "type": "youtube", "url": "https://www.youtube.com/watch?v=Ip3X9LOh2iI"},
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
}

# ── Grade-aware resource lookup ───────────────────────────────────────────────
GRADE_RESOURCES_MAP = {
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


def get_learning_resources(subject: str, chapter: str, grade: str = "Grade 9"):
    """Return curated resources if present; otherwise return free fallback links.

    Lookup priority:
    1. Grade-specific resource map (Grade 8, Grade 10)
    2. Legacy LEARNING_RESOURCES (Grade 9 + generic)
    3. Grammar topic resources (English, any grade)
    4. Fallback YouTube search
    All results include the NCERT Exemplar link for Maths/Science (Grade 8-10).
    """
    cleaned_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()

    # Priority 1: Grade-specific resources
    grade_map = GRADE_RESOURCES_MAP.get(grade, {})
    resources = grade_map.get(subject, {}).get(cleaned_chapter, [])

    # Priority 1b: Fuzzy match for chapter name variants (e.g. plural/singular, extra words)
    if not resources and grade_map.get(subject):
        import difflib as _dl
        subject_map = grade_map[subject]
        close = _dl.get_close_matches(cleaned_chapter, subject_map.keys(), n=1, cutoff=0.82)
        if close:
            resources = subject_map[close[0]]

    # Priority 2: Legacy Grade 9 / shared resources
    if not resources:
        resources = LEARNING_RESOURCES.get(subject, {}).get(cleaned_chapter, [])

    # Priority 3: Grammar topic match for English
    if not resources and subject == "English":
        resources = GRAMMAR_TOPIC_RESOURCES.get(cleaned_chapter, [])

    # Build final list
    if resources:
        # Grade 11: Indian + International only — no NCERT link injected
        result = list(resources) if grade == "Grade 11" else add_ncert_link(list(resources))
    else:
        grade_query = grade.lower().replace("grade", "class")
        query = quote_plus(f"{grade_query} {subject} {cleaned_chapter} free lecture")
        result = [
            {
                "title": f"YouTube Search - {subject}: {chapter}",
                "type": "website",
                "url": f"https://www.youtube.com/results?search_query={query}",
            },
        ]
        if grade != "Grade 11":
            result.append(NCERT_RESOURCE)

    # Append NCERT Exemplar link for Maths/Science (Grade 8-10)
    if subject in ("Maths", "Science") and grade in EXEMPLAR_GRADE_RESOURCES:
        exemplar = EXEMPLAR_GRADE_RESOURCES[grade].get(subject)
        if exemplar:
            result = [r for r in result if r.get("url") != exemplar["url"]]
            result.append({
                "title": exemplar["title"],
                "type": "website",
                "url": exemplar["url"],
            })
        # Always add the browse-all page
        if not any(r.get("url") == EXEMPLAR_PAGE["url"] for r in result):
            result.append(EXEMPLAR_PAGE)

    return result
