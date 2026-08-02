CBSE_9 = {
    "Science": [
        "Exploration: Entering the World of Secondary Science",
        "Cell: The Building Block of Life",
        "Tissues in Action",
        "Describing Motion Around Us",
        "Exploring Mixtures and their Separation",
        "How Forces Affect Motion",
        "Work, Energy, and Simple Machines",
        "Journey Inside the Atom",
        "Atomic Foundations of Matter",
        "Sound Waves: Characteristics and Applications",
        "Reproduction: How Life Continues",
        "Patterns in Life: Diversity and Classification",
        "Earth as a System: Energy, Matter, and Life",
    ],
    "Maths": [
        "Orienting Yourself: The Use of Coordinates",
        "Introduction to Linear Polynomials",
        "The World of Numbers",
        "Exploring Algebraic Identities",
        "I’m Up and Down, and Round and Round",
        "Measuring Space: Perimeter and Area",
        "The Mathematics of Maybe: Introduction to Probability",
        "Predicting What Comes Next: Exploring Sequences and Progressions",
    ],
    "English": [
        "How I Taught My Grandmother to Read",
        "The Pot Maker",
        "Winds of Change",
        "Vitamin-M",
        "The World of Limitless Possibilities",
        "Twin Melodies",
        "Carrier of Words",
        "Follow That Dream",
        "Grammar",
        "Writing Skills",
        "Reading Comprehension",
    ],
    # NCF-SE 2023 / NEP 2020 textbook "Understanding Society: India and
    # Beyond" (first edition June 2026) — replaces the pre-2023 syllabus.
    "Social Science": [
        "Understanding Social Science",
        "Shaping of the Earth's Surface",
        "Atmosphere and Climate",
        "Early Humans and Beginning of Civilisation",
        "State and Society up to 1000 CE",
        "Democracy",
        "Elections",
        "Building Blocks in Economics: The Problem of Choice",
        "The Price Puzzle: What Drives the Market",
    ],
    "Hindi": [
        "दो बैलों की कथा",
        "क्या लिखूँ?",
        "संवादहीन",
        "ऐसी भी बातें होती हैं (लता मंगेशकर से साक्षात्कार)",
        "आखिरी चट्टान तक",
        "रीढ़ की हड्डी",
        "मैं और मेरा देश",
        "पद",
        "राम-लक्ष्मण-परशुराम संवाद",
        "भारति, जय, विजय करो!",
        "झाँसी की रानी",
        "घर की याद",
    ],
    "Sanskrit": [
        "प्रथमः पाठः — सत्यं शिवं सुन्दरं संस्कृतम्",
        "द्वितीयः पाठः — सुखस्य मूलं धर्मः धर्मस्य मूलम् अर्थः",
        "तृतीयः पाठः — आत्मवलस्य भूतिṣu यः पश्यति सः पण्डितः",
        "चतुर्थः पाठः — न खलु वयस तेजसो हेतुः",
        "पञ्चमः पाठः — एका सा कृतकबुद्धिः मानवबुद्धिः सहकरी",
        "षष्ठः पाठः — मनः पूतं समाचरेत्",
        "सप्तमः पाठः — उपायं चिन्तयेत् प्राज्ञः तथापायं च चिन्तयेत्",
        "अष्टमः पाठः — अनाद आनन्दं प्राति",
        "नवमः पाठः — कृतं प्रतिकृतं भूयादेष धर्मः सनातनः",
        "दशमः पाठः — गङ्गा अहितगणम्",
        "एकादशः पाठः — वर्णोच्चारण-शिक्षा",
    ],
    "Advanced Mathematics": [
        "Advanced - Sets",
        "Advanced - Logarithms",
        "Advanced - Relations and Functions",
        "Advanced - Coordinate Geometry",
        "Advanced - Combinatorics",
        "Advanced - Exploring some more Progressions",
    ],
    "Advanced Science": [
        "Advanced - Measurement: Foundation of Science",
        "Advanced - Understanding Motion through Experience",
        "Advanced - Newton's Laws of Motion",
        "Advanced - The Geometry of Power: Advanced Simple Machines",
        "Advanced - Work and Energy",
        "Advanced - Structure of Atom",
        "Advanced - Chemical Bonding",
        "Advanced - Mixtures and their Separation",
        "Advanced - Microscope and Microscopy",
        "Advanced - Engineering Life: Miracles in Biotechnology",
    ],
}


LESSON_STEPS = {

    "Science": {

        "Matter in Our Surroundings": [

            "Introduction to matter",
            "Physical nature of matter",
            "States of matter",
            "Properties of solids liquids and gases",
            "Change of state",
            "Evaporation",
            "Factors affecting evaporation",
            "Chapter recap and practice"
        ],

        "Motion": [

            "Rest and motion",
            "Distance and displacement",
            "Speed and velocity",
            "Acceleration",
            "Distance time graph",
            "Velocity time graph",
            "Equations of motion",
            "Numericals practice",
            "Chapter recap"
        ],

        "Force and Laws of Motion": [

            "Concept of force",
            "Balanced and unbalanced forces",
            "Newton first law",
            "Newton second law",
            "Momentum",
            "Newton third law",
            "Applications in daily life",
            "Numericals",
            "Chapter recap"
        ]
    },

    "Maths": {

        "Number Systems": [

            "Introduction to number systems",
            "Natural numbers",
            "Integers",
            "Rational numbers",
            "Irrational numbers",
            "Real numbers",
            "Representation on number line",
            "Operations on real numbers",
            "Chapter recap"
        ],

        "Triangles": [

            "Introduction to triangles",
            "Types of triangles",
            "Congruence rules",
            "Properties of triangles",
            "Inequalities in triangles",
            "Numerical problems",
            "Proof based questions",
            "Chapter recap"
        ]
    }
}
UPLOAD_READY_CBSE_SUBJECTS = {
    "English": ["Uploaded Book Content"],
    "Hindi": ["Uploaded Book Content"],
    "Maths": ["Uploaded Book Content"],
    "EVS": ["Uploaded Book Content"],
    "Science": ["Uploaded Book Content"],
    "Social Science": ["Uploaded Book Content"],
    "Computer Science": ["Uploaded Book Content"],
}


UPPER_PRIMARY_CBSE_SUBJECTS = {
    "English": ["Uploaded Book Content"],
    "Hindi": ["Uploaded Book Content"],
    "Maths": ["Uploaded Book Content"],
    "Science": ["Uploaded Book Content"],
    "Social Science": ["Uploaded Book Content"],
    "Computer Science": ["Uploaded Book Content"],
}


def build_upload_ready_cbse_catalog(grade_number):
    """
    Return a CBSE scaffold for grades whose exact chapters will come from RAG.

    The placeholders keep the product usable for bulk PDF upload before every
    class-wise chapter list has been curated in code. The syllabus API also
    merges uploaded RAG document metadata, so real chapters appear after upload.
    """
    if grade_number <= 5:
        return UPLOAD_READY_CBSE_SUBJECTS

    return UPPER_PRIMARY_CBSE_SUBJECTS


# ── Grade 11 & 12 subject scaffold ────────────────────────────────────────────
# Chapters come from RAG (rag_documents) after PDF upload.
# This scaffold lists the subjects so the Lessons dropdown shows them.
GRADE_11_CBSE_SUBJECTS = {
    "Physics":          ["Uploaded Chapter Content"],
    "Chemistry":        ["Uploaded Chapter Content"],
    "Mathematics":      ["Uploaded Chapter Content"],
    "Biology":          ["Uploaded Chapter Content"],
    "English":          ["Uploaded Chapter Content"],
    "Hindi":            ["Uploaded Chapter Content"],
    "Economics":        ["Uploaded Chapter Content"],
    "Business Studies": ["Uploaded Chapter Content"],
    "Accountancy":      ["Uploaded Chapter Content"],
    "History":          ["Uploaded Chapter Content"],
    "Geography":        ["Uploaded Chapter Content"],
    "Political Science":["Uploaded Chapter Content"],
    "Sociology":        ["Uploaded Chapter Content"],
    "Psychology":       ["Uploaded Chapter Content"],
}

GRADE_12_CBSE_SUBJECTS = {
    "Physics":          ["Uploaded Chapter Content"],
    "Chemistry":        ["Uploaded Chapter Content"],
    "Mathematics":      ["Uploaded Chapter Content"],
    "Biology":          ["Uploaded Chapter Content"],
    "English":          ["Uploaded Chapter Content"],
    "Hindi":            ["Uploaded Chapter Content"],
    "Economics":        ["Uploaded Chapter Content"],
    "Business Studies": ["Uploaded Chapter Content"],
    "Accountancy":      ["Uploaded Chapter Content"],
    "History":          ["Uploaded Chapter Content"],
    "Geography":        ["Uploaded Chapter Content"],
    "Political Science":["Uploaded Chapter Content"],
    "Sociology":        ["Uploaded Chapter Content"],
    "Psychology":       ["Uploaded Chapter Content"],
}

SYLLABUS = {
    **{
        f"Grade {grade_number}": {
            "CBSE": build_upload_ready_cbse_catalog(grade_number),
        }
        for grade_number in range(5, 11)
    },
    "Grade 9": {
        "CBSE": CBSE_9,
    },
    "Grade 11": {
        "CBSE": GRADE_11_CBSE_SUBJECTS,
    },
    "Grade 12": {
        "CBSE": GRADE_12_CBSE_SUBJECTS,
    },
}
