from app.data.syllabus import SYLLABUS
from app.routes import syllabus as syllabus_route


def test_syllabus_supports_class_1_to_class_10_without_losing_grade_9():
    """
    Ensure the product can expose Class 1-10 selectors while preserving the
    existing Grade 9 CBSE and SOF catalogs that current students use.
    """
    for grade_number in range(1, 11):
        grade = f"Grade {grade_number}"

        assert grade in SYLLABUS
        assert "CBSE" in SYLLABUS[grade]
        assert "SOF" in SYLLABUS[grade]
        assert SYLLABUS[grade]["CBSE"]

    assert "Science" in SYLLABUS["Grade 9"]["CBSE"]
    assert "Science Olympiad" in SYLLABUS["Grade 9"]["SOF"]
    assert "Cell: The Building Block of Life" in SYLLABUS["Grade 9"]["CBSE"]["Science"]
    assert "Force and Laws of Motion" in SYLLABUS["Grade 9"]["SOF"]["Science Olympiad"]


class FakeSyllabusQuery:
    """Tiny Supabase query stub for syllabus merge tests."""

    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class FakeSyllabusSupabase:
    """Fake Supabase client that returns prepared rag_documents rows."""

    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        assert table_name == "rag_documents"
        return FakeSyllabusQuery(self.rows)


def test_uploaded_rag_chapters_replace_placeholder_and_sort_by_book_order(monkeypatch):
    """
    Uploaded lower-grade book chapters should appear as a clean chapter dropdown.

    This protects Class 8 Maths where multiple book parts exist and upload order
    may be newest-first rather than chapter order.
    """
    monkeypatch.setattr(
        syllabus_route,
        "supabase",
        FakeSyllabusSupabase([
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Chapter 7: Proportional Reasoning",
                "title": "Grade 8 Maths Part I - Chapter 7: Proportional Reasoning",
                "created_at": "2026-06-05T02:00:00Z",
            },
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Chapter 1: Percentages",
                "title": "Grade 8 Maths Part I - Chapter 1: Percentages",
                "created_at": "2026-06-05T02:01:00Z",
            },
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Front Matter (Part II)",
                "title": "Grade 8 Maths Part II - Front Matter",
                "created_at": "2026-06-05T02:02:00Z",
            },
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Chapter 1 - A SQUARE AND A CUBE",
                "title": "Grade 8 Maths Part II - Chapter 1 - A SQUARE AND A CUBE",
                "created_at": "2026-06-05T02:03:00Z",
            },
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Front Matter",
                "title": "Grade 8 Maths Part I - Front Matter",
                "created_at": "2026-06-05T02:04:00Z",
            },
        ]),
    )

    merged = syllabus_route.merge_uploaded_rag_chapters(SYLLABUS)
    chapters = merged["Grade 8"]["CBSE"]["Maths"]

    assert "Uploaded Book Content" not in chapters
    assert chapters[:5] == [
        "Part 1 - Front Matter",
        "Part 1 - Chapter 1: Percentages",
        "Part 1 - Chapter 7: Proportional Reasoning",
        "Part 2 - Front Matter",
        "Part 2 - Chapter 1 - A SQUARE AND A CUBE",
    ]


def test_static_default_chapters_do_not_surface_without_rag(monkeypatch):
    """Grade chapter dropdowns must use live RAG, not hardcoded defaults."""
    monkeypatch.setattr(syllabus_route, "supabase", FakeSyllabusSupabase([]))

    merged = syllabus_route.merge_uploaded_rag_chapters(SYLLABUS)

    assert merged["Grade 9"]["CBSE"]["Science"] == ["Uploaded Book Content"]
    assert "Cell: The Building Block of Life" not in merged["Grade 9"]["CBSE"]["Science"]


def test_rag_chapters_are_isolated_by_grade(monkeypatch):
    """A matching subject in another grade must not leak into this grade."""
    monkeypatch.setattr(
        syllabus_route,
        "supabase",
        FakeSyllabusSupabase([
            {
                "grade": "Grade 8",
                "subject": "Maths",
                "chapter": "Chapter 1: A Square and A Cube",
                "title": "Grade 8 CBSE Maths Text Book Part 1 - Chapter 1",
                "board": "CBSE",
                "created_at": "2026-06-05T02:00:00Z",
            },
            {
                "grade": "Grade 10",
                "subject": "Maths",
                "chapter": "Chapter 1: Real Numbers",
                "title": "Grade 10 CBSE Maths Text Book - Chapter 1",
                "board": "CBSE",
                "created_at": "2026-06-05T02:00:00Z",
            },
        ]),
    )

    merged = syllabus_route.merge_uploaded_rag_chapters(SYLLABUS)

    assert merged["Grade 8"]["CBSE"]["Maths"] == [
        "Chapter 1: A Square and A Cube",
    ]
    assert merged["Grade 10"]["CBSE"]["Maths"] == [
        "Chapter 1: Real Numbers",
    ]


def test_multi_part_maths_labels_stay_distinct_for_dropdowns():
    """Two Maths books should show clear Part 1 / Part 2 dropdown labels."""
    chapters = syllabus_route.sort_uploaded_chapters(
        ["Uploaded Book Content"],
        [
            {
                "chapter": "Chapter 1: Fractions in Disguise",
                "title": "Maths Text Book Part 2 - Chapter 1: Fractions in Disguise",
            },
            {
                "chapter": "Chapter 1: A Square and A Cube",
                "title": "Maths Text Book Part 1 - Chapter 1: A Square and A Cube",
            },
        ],
    )

    assert chapters == [
        "Part 1 - Chapter 1: A Square and A Cube",
        "Part 2 - Chapter 1: Fractions in Disguise",
    ]


def test_uploaded_rag_chapter_labels_preserve_admin_confirmed_text(monkeypatch):
    """The syllabus dropdown must not rewrite labels confirmed during RAG upload."""
    confirmed_label = "Chapter 13: Our Home: Earth"

    monkeypatch.setattr(
        syllabus_route,
        "supabase",
        FakeSyllabusSupabase([
            {
                "grade": "Grade 8",
                "subject": "Science",
                "chapter": confirmed_label,
                "title": f"Grade 8 Science - {confirmed_label}",
                "created_at": "2026-06-05T02:00:00Z",
            },
        ]),
    )

    merged = syllabus_route.merge_uploaded_rag_chapters(SYLLABUS)

    assert merged["Grade 8"]["CBSE"]["Science"] == [confirmed_label]


def test_syllabus_override_is_authoritative_after_admin_review():
    """Saved admin reviews should stay aligned to live labels after refresh."""
    merged = {
        "Grade 8": {
            "CBSE": {
                "Maths": [
                    "Uploaded Book Content",
                    "Chapter 1: Reviewed",
                    "Chapter 3: Newly Reuploaded",
                ],
            },
        },
    }

    result = syllabus_route.apply_syllabus_overrides(
        merged,
        {
            ("Grade 8", "CBSE", "Maths"): {
                "chapters": [
                    "Chapter 1: Reviewed",
                    "Chapter 2: Reviewed",
                ],
            },
        },
    )

    assert result["Grade 8"]["CBSE"]["Maths"] == [
        "Chapter 1: Reviewed",
        "Chapter 3: Newly Reuploaded",
    ]


def test_mixed_grade_override_keeps_only_matching_live_chapters():
    """A contaminated review should not mix Class 8 and Class 10 Maths labels."""
    merged = {
        "Grade 10": {
            "CBSE": {
                "Maths": [
                    "Chapter 1: Real Numbers",
                    "Chapter 2: Polynomials",
                    "Chapter 3: Pair of Linear Equations in Two Variables",
                ],
            },
        },
    }

    result = syllabus_route.apply_syllabus_overrides(
        merged,
        {
            ("Grade 10", "CBSE", "Maths"): {
                "chapters": [
                    "Chapter 1: Real Numbers",
                    "Part 1 - Chapter 1: A Square and A Cube",
                    "Chapter 2: Polynomials",
                    "Part 2 - Chapter 1: Fractions in Disguise",
                ],
            },
        },
    )

    assert result["Grade 10"]["CBSE"]["Maths"] == [
        "Chapter 1: Real Numbers",
        "Chapter 2: Polynomials",
        "Chapter 3: Pair of Linear Equations in Two Variables",
    ]


def test_stale_override_does_not_hide_live_rag_chapters():
    """Old reviewed lists should yield when none of their labels match live RAG."""
    merged = {
        "Grade 8": {
            "CBSE": {
                "Maths": [
                    "Part 1 - Chapter 1: A Square and A Cube",
                    "Part 1 - Chapter 2: Power Play",
                    "Part 2 - Chapter 1: Fractions in Disguise",
                ],
            },
        },
    }

    result = syllabus_route.apply_syllabus_overrides(
        merged,
        {
            ("Grade 8", "CBSE", "Maths"): {
                "chapters": [
                    "Chapter 1: Real Numbers",
                    "Chapter 2: Polynomials",
                ],
            },
        },
    )

    assert result["Grade 8"]["CBSE"]["Maths"] == [
        "Part 1 - Chapter 1: A Square and A Cube",
        "Part 1 - Chapter 2: Power Play",
        "Part 2 - Chapter 1: Fractions in Disguise",
    ]


def test_no_live_rag_mixed_part_review_keeps_consistent_series():
    """A saved review without live RAG should not recreate stale chapters."""
    result = syllabus_route.merge_reviewed_and_live_chapters(
        [
            "Chapter 1: Real Numbers",
            "Part 1 - Chapter 1: A Square and A Cube",
            "Chapter 2: Polynomials",
            "Part 2 - Chapter 1: Fractions in Disguise",
        ],
        ["Uploaded Book Content"],
    )

    assert result == ["Uploaded Book Content"]


def test_override_merge_upgrades_old_flat_labels_to_part_labels():
    """Existing reviewed Maths labels should adopt clearer live book-part labels."""
    result = syllabus_route.merge_reviewed_and_live_chapters(
        [
            "Chapter 1: A Square and A Cube",
            "Chapter 2: Reviewed Only",
        ],
        [
            "Part 1 - Chapter 1: A Square and A Cube",
            "Part 2 - Chapter 1: Fractions in Disguise",
        ],
    )

    assert result == [
        "Part 1 - Chapter 1: A Square and A Cube",
        "Part 2 - Chapter 1: Fractions in Disguise",
    ]


def test_subject_override_controls_visible_subjects():
    """Admin-reviewed subject lists should hide removed subjects and add new ones."""
    merged = {
        "Grade 8": {
            "CBSE": {
                "Maths": ["Chapter 1: Percentages"],
                "Computer Science": ["Uploaded Book Content"],
            },
        },
    }

    result = syllabus_route.apply_subject_overrides(
        merged,
        {
            ("Grade 8", "CBSE"): {
                "subjects": ["Maths", "Marathi"],
            },
        },
    )

    assert list(result["Grade 8"]["CBSE"].keys()) == ["Maths", "Marathi"]
    assert "Computer Science" not in result["Grade 8"]["CBSE"]
    assert result["Grade 8"]["CBSE"]["Marathi"] == ["Uploaded Book Content"]


def test_chapter_content_status_flags_missing_override_content():
    """
    Reviewed dropdown labels can outlive deleted RAG documents.

    The admin review API should expose that mismatch so admins know which
    dropdown entries need reuploading or relabeling before students use them.
    """
    syllabus_tree = {
        "Grade 8": {
            "CBSE": {
                "Science": [
                    "Chapter 6: Pressure, Winds, Storms, and Cyclones",
                    "Chapter 7: Particulate Nature of Matter",
                ],
            },
        },
    }
    rag_counts = {
        (
            "Grade 8",
            "CBSE",
            "Science",
            syllabus_route.normalize_rag_chapter_lookup(
                "Chapter 6: Pressure, Winds, Storms, and Cyclones"
            ),
        ): 1,
    }

    status = syllabus_route.build_chapter_content_status(syllabus_tree, rag_counts)

    assert status[0]["has_content"] is True
    assert status[0]["document_count"] == 1
    assert status[1]["has_content"] is False
    assert status[1]["document_count"] == 0
