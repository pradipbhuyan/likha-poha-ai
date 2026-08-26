"""
Product Catalogue — canonical definition of all grades, boards, and coaching
programs the platform supports.

`visible: False`  → feature exists in code but is hidden from all students /
                    parents until an admin toggles it on via the Product
                    Catalogue admin page.

This dict is the *source of truth* that is stored in (and can be overridden
by) the `admin_settings` Supabase table under key "product_catalogue".
When no DB row exists the hardcoded defaults below are used.
"""

DEFAULT_PRODUCT_CATALOGUE: dict = {
    "grades": {
        # ── Currently live ─────────────────────────────────────────────────
        "Grade 1":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 2":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 3":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 4":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 5":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 6":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 7":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 8":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 9":  {"visible": True,  "boards": ["CBSE"], "streams": []},
        "Grade 10": {"visible": True,  "boards": ["CBSE"], "streams": []},
        # ── Ready in code, hidden until content is uploaded ─────────────────
        "Grade 11": {
            "visible": True,
            "boards": ["CBSE"],
            "streams": ["Science (PCM)", "Science (PCB)", "Science (PCMB)", "Commerce", "Arts / Humanities"],
        },
        "Grade 12": {
            "visible": True,
            "boards": ["CBSE"],
            "streams": ["Science (PCM)", "Science (PCB)", "Science (PCMB)", "Commerce", "Arts / Humanities"],
        },
    },
    "coaching_programs": {
        # ── Entrance exam prep — Exam Prep Center. Live since 2026-07 (bundled
        # ── Exam Prep Center plan, ₹1,999/yr — see 03_SUBSCRIPTIONS.md); all
        # ── six visible:True below matches that current reality. Keys match
        # ── exam_prep.py's /status and exam_prep_service.py's EXAM_SUBJECTS_MAP
        # ── exactly — keep them in sync if either changes.
        "jee_main": {
            "visible": True,
            "full_name": "JEE Mains + Advanced",
            "subjects": ["Physics", "Chemistry", "Mathematics"],
            "description": "Engineering entrance — IITs, NITs, IIITs",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "neet_ug": {
            "visible": True,
            "full_name": "NEET UG",
            "subjects": ["Physics", "Chemistry", "Biology"],
            "description": "Medical entrance — MBBS, BDS admissions",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "cuet_ug": {
            "visible": True,
            "full_name": "CUET UG",
            "subjects": [
                "Physics", "Chemistry", "Mathematics", "Biology",
                "Accountancy", "Economics", "Business Studies",
                "History", "Geography", "Political Science", "English",
            ],
            "description": "Central Universities common entrance test",
            "target_grades": ["Grade 12"],
        },
        "sat": {
            "visible": True,
            "full_name": "SAT (Scholastic Assessment Test)",
            "subjects": ["Reading & Writing", "Mathematics"],
            "description": "US/international undergraduate admissions test",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "ielts": {
            "visible": True,
            "full_name": "IELTS (Academic)",
            "subjects": ["Listening", "Reading", "Vocabulary & Grammar"],
            "description": "English proficiency test for study or immigration abroad",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "toefl_ibt": {
            "visible": True,
            "full_name": "TOEFL iBT",
            "subjects": ["Reading", "Listening", "Integrated Skills"],
            "description": "English proficiency test for US/international university admission",
            "target_grades": ["Grade 11", "Grade 12"],
        },
    },
}

# All grade keys including hidden ones — used for backend validation
ALL_GRADES_INCLUDING_HIDDEN: list[str] = list(
    DEFAULT_PRODUCT_CATALOGUE["grades"].keys()
)

# Grades a teacher may assign to a student they add/invite, or edit a
# student into. Teachers work with middle/senior school (Grade 5-12) —
# Grade 1-4 students are managed by parents only, never by a teacher.
TEACHER_ALLOWED_GRADES: list[str] = [
    g for g in ALL_GRADES_INCLUDING_HIDDEN
    if g not in ("Grade 1", "Grade 2", "Grade 3", "Grade 4")
]

# Only grades visible to students (dynamic — overridden by DB at runtime)
def get_visible_grades(catalogue: dict | None = None) -> list[str]:
    """Return grades currently visible to students."""
    cat = catalogue or DEFAULT_PRODUCT_CATALOGUE
    return [g for g, v in cat["grades"].items() if v.get("visible", False)]


def get_visible_coaching_programs(catalogue: dict | None = None) -> list[str]:
    """
    Return coaching program keys currently visible to students.

    Iterates the CANONICAL key list (this module's own coaching_programs),
    not whatever happens to be in `catalogue` — and a canonical key absent
    from `catalogue["coaching_programs"]` defaults to visible rather than
    hidden. This matters concretely, not just defensively: a real
    `admin_settings` DB row already exists (saved before the 2026-08-26
    rename from "JEE"/"NEET"/"CUET" to "jee_main"/"neet_ug"/"cuet_ug", and
    before "sat"/"ielts"/"toefl_ibt" existed at all) that contains none of
    the six current keys. Treating "absent" the same as "admin explicitly
    hid this" would have silently deactivated all six exams for every
    student the moment this function's caller shipped (see TECH_DEBT.md
    TD-14) — "not yet migrated" must default to on, not off.
    """
    cat = catalogue or DEFAULT_PRODUCT_CATALOGUE
    programs = cat.get("coaching_programs", {})
    return [
        key for key in DEFAULT_PRODUCT_CATALOGUE["coaching_programs"]
        if programs.get(key, {"visible": True}).get("visible", True)
    ]
