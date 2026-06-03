"""
Free learning resources for Grade 9 CBSE + SOF Olympiad tutor app.

Use get_learning_resources(subject, chapter) in app.py so every chapter shows
curated links when available and safe fallback links otherwise.
"""
from urllib.parse import quote_plus

FREE_COMMON_RESOURCES = [
    {
        "title": "NCERT Official Textbooks",
        "type": "website",
        "url": "https://ncert.nic.in/textbook.php",
    },
    {
        "title": "Khan Academy",
        "type": "website",
        "url": "https://www.khanacademy.org/",
    },
    {
        "title": "PhET Free Science and Maths Simulations",
        "type": "website",
        "url": "https://phet.colorado.edu/",
    },
]

LEARNING_RESOURCES = {
    "Science": {
        "Matter in Our Surroundings": [
            {"title": "Khan Academy - Matter in our surroundings", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Amatter-in-our-surroundings"},
            {"title": "YouTube Search - Class 9 Matter in Our Surroundings", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+matter+in+our+surroundings+full+chapter"},
        ],
        "Is Matter Around Us Pure": [
            {"title": "Khan Academy - Is matter around us pure", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Ais-matter-around-us-pure"},
            {"title": "YouTube Search - Is Matter Around Us Pure", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+is+matter+around+us+pure+full+chapter"},
        ],
        "Atoms and Molecules": [
            {"title": "Khan Academy - Atoms and molecules", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Aatoms-and-molecules"},
            {"title": "YouTube Search - Atoms and Molecules", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+atoms+and+molecules+full+chapter"},
        ],
        "Structure of the Atom": [
            {"title": "Khan Academy - Structure of the atom", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Astructure-of-the-atom"},
            {"title": "PhET - Build an Atom Simulation", "type": "website", "url": "https://phet.colorado.edu/en/simulation/build-an-atom"},
            {"title": "YouTube Search - Structure of the Atom", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+structure+of+the+atom+full+chapter"},
        ],
        "The Fundamental Unit of Life": [
            {"title": "Khan Academy - Introduction to cells", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Aintroduction-to-cells"},
            {"title": "YouTube Search - Fundamental Unit of Life", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+fundamental+unit+of+life+full+chapter"},
        ],
        "Tissues": [
            {"title": "Khan Academy - Tissues", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Atissues"},
            {"title": "YouTube Search - Tissues", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+tissues+full+chapter"},
        ],
        "Motion": [
            {"title": "Khan Academy - Motion", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Amotion"},
            {"title": "PhET - Moving Man Simulation", "type": "website", "url": "https://phet.colorado.edu/en/simulation/moving-man"},
            {"title": "YouTube Search - Motion Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+motion+full+chapter"},
        ],
        "Force and Laws of Motion": [
            {"title": "Khan Academy - Force and laws of motion", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Aforce-laws-of-motion"},
            {"title": "PhET - Forces and Motion Basics", "type": "website", "url": "https://phet.colorado.edu/en/simulation/forces-and-motion-basics"},
            {"title": "YouTube Search - Force and Laws of Motion", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+force+and+laws+of+motion+full+chapter"},
        ],
        "Gravitation": [
            {"title": "Khan Academy - Gravity", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Agravity"},
            {"title": "PhET - Gravity Force Lab", "type": "website", "url": "https://phet.colorado.edu/en/simulation/gravity-force-lab"},
            {"title": "YouTube Search - Gravitation Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+gravitation+full+chapter"},
        ],
        "Work and Energy": [
            {"title": "Khan Academy - Work and Energy", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Awork-energy"},
            {"title": "PhET - Energy Skate Park", "type": "website", "url": "https://phet.colorado.edu/en/simulation/energy-skate-park"},
            {"title": "YouTube Search - Work and Energy Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+work+and+energy+full+chapter"},
        ],
        "Sound": [
            {"title": "Khan Academy - Sound", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Asound"},
            {"title": "PhET - Wave Interference", "type": "website", "url": "https://phet.colorado.edu/en/simulation/wave-interference"},
            {"title": "YouTube Search - Sound Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+sound+full+chapter"},
        ],
        "Improvement in Food Resources": [
            {"title": "Khan Academy - Improvement in food resources", "type": "website", "url": "https://www.khanacademy.org/science/ncert-class-9-science/x7e8d66f732d28ce4%3Aimprovement-in-food-resources"},
            {"title": "YouTube Search - Improvement in Food Resources", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+science+improvement+in+food+resources+full+chapter"},
        ],
    },
    "Maths": {
        "Number Systems": [{"title": "Khan Academy - Class 9 Maths", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Number Systems Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+number+systems+full+chapter"}],
        "Polynomials": [{"title": "Khan Academy - Class 9 Maths Polynomials", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Polynomials Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+polynomials+full+chapter"}],
        "Coordinate Geometry": [{"title": "Khan Academy - Coordinate Geometry", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Coordinate Geometry Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+coordinate+geometry+full+chapter"}],
        "Linear Equations in Two Variables": [{"title": "Khan Academy - Linear Equations", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Linear Equations in Two Variables", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+linear+equations+in+two+variables+full+chapter"}],
        "Introduction to Euclid Geometry": [{"title": "Khan Academy - Euclid Geometry", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Euclid Geometry Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+introduction+to+euclid+geometry+full+chapter"}],
        "Lines and Angles": [{"title": "Khan Academy - Lines and Angles", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Lines and Angles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+lines+and+angles+full+chapter"}],
        "Triangles": [{"title": "Khan Academy - Triangles", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Triangles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+triangles+full+chapter"}],
        "Quadrilaterals": [{"title": "Khan Academy - Quadrilaterals", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Quadrilaterals Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+quadrilaterals+full+chapter"}],
        "Areas of Parallelograms and Triangles": [{"title": "YouTube Search - Areas of Parallelograms and Triangles", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+areas+of+parallelograms+and+triangles+full+chapter"}],
        "Circles": [{"title": "Khan Academy - Circles", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Circles Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+circles+full+chapter"}],
        "Herons Formula": [{"title": "Khan Academy - Heron's Formula", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Heron's Formula Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+herons+formula+full+chapter"}],
        "Surface Areas and Volumes": [{"title": "Khan Academy - Surface Area and Volumes", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Surface Areas and Volumes", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+surface+areas+and+volumes+full+chapter"}],
        "Statistics": [{"title": "Khan Academy - Statistics", "type": "website", "url": "https://www.khanacademy.org/math/in-in-grade-9-ncert"}, {"title": "YouTube Search - Statistics Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+statistics+full+chapter"}],
        "Probability": [{"title": "Khan Academy - Probability", "type": "website", "url": "https://www.khanacademy.org/math/statistics-probability/probability-library"}, {"title": "YouTube Search - Probability Class 9", "type": "website", "url": "https://www.youtube.com/results?search_query=class+9+maths+probability+full+chapter"}],
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
        LEARNING_RESOURCES[_subject].setdefault(_chapter, [
            {"title": f"YouTube Search - {_chapter}", "type": "website", "url": f"https://www.youtube.com/results?search_query={q}"},
            {"title": "NCERT Official Textbooks", "type": "website", "url": "https://ncert.nic.in/textbook.php"},
        ])


def get_learning_resources(subject: str, chapter: str, grade: str = "Grade 9"):
    """Return curated resources if present; otherwise return free fallback links."""
    resources = LEARNING_RESOURCES.get(subject, {}).get(chapter, [])
    if resources:
        return resources

    grade_query = grade.lower().replace("grade", "class")
    query = quote_plus(f"{grade_query} {subject} {chapter} free lecture")
    return [
        {
            "title": f"YouTube Search - {subject}: {chapter}",
            "type": "website",
            "url": f"https://www.youtube.com/results?search_query={query}",
        },
        {
            "title": "NCERT Official Textbooks",
            "type": "website",
            "url": "https://ncert.nic.in/textbook.php",
        },
        {
            "title": "Khan Academy",
            "type": "website",
            "url": "https://www.khanacademy.org/",
        },
    ]
