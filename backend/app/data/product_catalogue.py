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
        # ── Entrance exam prep — hidden until content + UI are ready ────────
        "JEE": {
            "visible": False,
            "full_name": "JEE Mains + Advanced",
            "subjects": ["Physics", "Chemistry", "Mathematics"],
            "description": "Engineering entrance — IITs, NITs, IIITs",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "NEET": {
            "visible": False,
            "full_name": "NEET UG",
            "subjects": ["Physics", "Chemistry", "Biology"],
            "description": "Medical entrance — MBBS, BDS admissions",
            "target_grades": ["Grade 11", "Grade 12"],
        },
        "CUET": {
            "visible": False,
            "full_name": "CUET UG",
            "subjects": [
                "Physics", "Chemistry", "Mathematics", "Biology",
                "Accountancy", "Economics", "Business Studies",
                "History", "Geography", "Political Science", "English",
            ],
            "description": "Central Universities common entrance test",
            "target_grades": ["Grade 12"],
        },
    },
}

# All grade keys including hidden ones — used for backend validation
ALL_GRADES_INCLUDING_HIDDEN: list[str] = list(
    DEFAULT_PRODUCT_CATALOGUE["grades"].keys()
)

# Only grades visible to students (dynamic — overridden by DB at runtime)
def get_visible_grades(catalogue: dict | None = None) -> list[str]:
    """Return grades currently visible to students."""
    cat = catalogue or DEFAULT_PRODUCT_CATALOGUE
    return [g for g, v in cat["grades"].items() if v.get("visible", False)]


def get_visible_coaching_programs(catalogue: dict | None = None) -> list[str]:
    """Return coaching program keys currently visible to students."""
    cat = catalogue or DEFAULT_PRODUCT_CATALOGUE
    return [k for k, v in cat["coaching_programs"].items() if v.get("visible", False)]
