"""
Free learning resources for Grade 9 CBSE + SOF Olympiad tutor app.

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
            {"title": "PhET - Gravity Force Lab", "type": "website", "url": "https://phet.colorado.edu/en/simulation/gravity-force-lab"},
            {"title": "YouTube Search - Gravitation Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+gravitation+full+chapter"},
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
    "Science Olympiad": {
        "Logical Reasoning": [{"title": "YouTube Search - Class 9 Science Olympiad Logical Reasoning", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+olympiad+logical+reasoning"}],
        "Physics": [{"title": "YouTube Search - Class 9 Science Olympiad Physics", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+olympiad+physics"}],
        "Chemistry": [{"title": "YouTube Search - Class 9 Science Olympiad Chemistry", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+olympiad+chemistry"}],
        "Biology": [{"title": "YouTube Search - Class 9 Science Olympiad Biology", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+olympiad+biology"}],
        "Achievers Section": [{"title": "YouTube Search - Class 9 NSO Achievers Section", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+nso+achievers+section"}],
        "Mock Tests": [{"title": "YouTube Search - Class 9 NSO Mock Test", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+nso+mock+test"}],
    },
    "Maths Olympiad": {
        "Logical Reasoning": [{"title": "YouTube Search - Class 9 IMO Logical Reasoning", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+logical+reasoning"}],
        "Mathematical Reasoning": [{"title": "YouTube Search - Class 9 IMO Mathematical Reasoning", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+mathematical+reasoning"}],
        "Everyday Mathematics": [{"title": "YouTube Search - Class 9 IMO Everyday Mathematics", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+everyday+mathematics"}],
        "Higher Order Thinking Skills": [{"title": "YouTube Search - Class 9 IMO HOTS", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+higher+order+thinking+skills"}],
        "Achievers Section": [{"title": "YouTube Search - Class 9 IMO Achievers Section", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+achievers+section"}],
        "Mock Tests": [{"title": "YouTube Search - Class 9 IMO Mock Test", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+imo+mock+test"}],
    },
    "English Olympiad": {
        "Word and Structure Knowledge": [{"title": "YouTube Search - Class 9 IEO Word and Structure Knowledge", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+ieo+word+and+structure+knowledge"}],
        "Reading": [{"title": "YouTube Search - Class 9 IEO Reading", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+ieo+reading+comprehension"}],
        "Spoken and Written Expression": [{"title": "YouTube Search - Class 9 IEO Spoken and Written Expression", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+ieo+spoken+and+written+expression"}],
        "Achievers Section": [{"title": "YouTube Search - Class 9 IEO Achievers Section", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+ieo+achievers+section"}],
        "Mock Tests": [{"title": "YouTube Search - Class 9 IEO Mock Test", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+ieo+mock+test"}],
    },
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

# ── Grade-aware resource lookup ───────────────────────────────────────────────
GRADE_RESOURCES_MAP = {
    "Grade 8": GRADE_8_RESOURCES,
    "Grade 10": GRADE_10_RESOURCES,
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

    # Priority 2: Legacy Grade 9 / shared resources
    if not resources:
        resources = LEARNING_RESOURCES.get(subject, {}).get(cleaned_chapter, [])

    # Priority 3: Grammar topic match for English
    if not resources and subject == "English":
        resources = GRAMMAR_TOPIC_RESOURCES.get(cleaned_chapter, [])

    # Build final list
    if resources:
        result = add_ncert_link(list(resources))
    else:
        grade_query = grade.lower().replace("grade", "class")
        query = quote_plus(f"{grade_query} {subject} {cleaned_chapter} free lecture")
        result = [
            {
                "title": f"YouTube Search - {subject}: {chapter}",
                "type": "website",
                "url": f"https://www.youtube.com/results?search_query={query}",
            },
            NCERT_RESOURCE,
        ]

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
