from app.data.syllabus import SYLLABUS
from app.routes import syllabus as syllabus_route


def test_syllabus_supports_class_5_to_class_10_without_losing_grade_9():
    """
    Ensure the product exposes Class 5-10 selectors while preserving the
    existing Grade 9 CBSE catalog that current students use.

    Grades 1-4 and SOF (Olympiad) are not supported on the platform.
    """
    for grade_number in range(5, 11):
        grade = f"Grade {grade_number}"

        assert grade in SYLLABUS
        assert "CBSE" in SYLLABUS[grade]
        assert "SOF" not in SYLLABUS[grade]
        assert SYLLABUS[grade]["CBSE"]

    for grade_number in range(1, 5):
        assert f"Grade {grade_number}" not in SYLLABUS

    assert "Science" in SYLLABUS["Grade 9"]["CBSE"]
    assert "Cell: The Building Block of Life" in SYLLABUS["Grade 9"]["CBSE"]["Science"]


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


def test_multi_book_english_labels_show_source_prefixes():
    """English Text Book and Supplementary Reader chapters should be distinct."""
    chapters = syllabus_route.sort_uploaded_chapters(
        ["Uploaded Book Content"],
        [
            {
                "chapter": "Chapter 1: A Triumph of Surgery",
                "title": (
                    "Grade 10 CBSE English Supplementary Reader - "
                    "Chapter 1: A Triumph of Surgery"
                ),
            },
            {
                "chapter": "Chapter 1: A Letter to God",
                "title": "Grade 10 CBSE English Text Book - Chapter 1: A Letter to God",
            },
            {
                "chapter": "Chapter 2: Nelson Mandela: Long Walk to Freedom",
                "title": (
                    "Grade 10 CBSE English Text Book - "
                    "Chapter 2: Nelson Mandela: Long Walk to Freedom"
                ),
            },
        ],
    )

    assert chapters == [
        "Text Book - Chapter 1: A Letter to God",
        "Text Book - Chapter 2: Nelson Mandela: Long Walk to Freedom",
        "Supplementary Reader - Chapter 1: A Triumph of Surgery",
    ]


def test_social_science_book_sources_show_source_prefixes():
    """Social Science Text Book and Geography chapters should stay distinct."""
    chapters = syllabus_route.sort_uploaded_chapters(
        ["Uploaded Book Content"],
        [
            {
                "chapter": "Chapter 1: Resources and Development",
                "title": (
                    "Grade 10 CBSE Social Science Geography - "
                    "Chapter 1: Resources and Development"
                ),
            },
            {
                "chapter": "Chapter 1: Development",
                "title": (
                    "Grade 10 CBSE Social Science Text Book - "
                    "Chapter 1: Development"
                ),
            },
            {
                "chapter": "Chapter 2: Forest and Wildlife Resources",
                "title": (
                    "Grade 10 CBSE Social Science Geography - "
                    "Chapter 2: Forest and Wildlife Resources"
                ),
            },
        ],
    )

    assert chapters == [
        "Text Book - Chapter 1: Development",
        "Geography - Chapter 1: Resources and Development",
        "Geography - Chapter 2: Forest and Wildlife Resources",
    ]


def test_content_status_matches_source_prefixed_dropdown_labels():
    """Display-only source prefixes should not break RAG linked status."""
    syllabus_tree = {
        "Grade 10": {
            "CBSE": {
                "English": [
                    "Text Book - Chapter 1: A Letter to God",
                    "Supplementary Reader - Chapter 1: A Triumph of Surgery",
                ],
                "Social Science": [
                    "Text Book - Chapter 1: Development",
                    "Geography - Chapter 1: Resources and Development",
                ],
            },
        },
    }
    rag_counts = {
        (
            "Grade 10",
            "CBSE",
            "English",
            syllabus_route.normalize_rag_chapter_lookup("Chapter 1: A Letter to God"),
        ): 1,
        (
            "Grade 10",
            "CBSE",
            "English",
            syllabus_route.normalize_rag_chapter_lookup("Chapter 1: A Triumph of Surgery"),
        ): 1,
        (
            "Grade 10",
            "CBSE",
            "Social Science",
            syllabus_route.normalize_rag_chapter_lookup("Chapter 1: Development"),
        ): 1,
        (
            "Grade 10",
            "CBSE",
            "Social Science",
            syllabus_route.normalize_rag_chapter_lookup(
                "Chapter 1: Resources and Development"
            ),
        ): 1,
    }

    status = syllabus_route.build_chapter_content_status(syllabus_tree, rag_counts)

    assert [item["has_content"] for item in status] == [True, True, True, True]


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


def test_syllabus_override_preserves_matching_review_order_and_appends_live_rag():
    """Saved admin reviews should keep matching order but not hide new live RAG."""
    merged = {
        "Grade 8": {
            "CBSE": {
                "Maths": [
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


def test_syllabus_override_drops_stale_cross_grade_chapters():
    """Reviewed chapters from another grade must not survive against live RAG."""
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


def test_stale_override_is_replaced_by_live_rag_for_same_grade_subject():
    """Fresh reuploads should reappear even if an older override exists."""
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


def test_reviewed_chapter_merge_uses_placeholder_when_no_live_rag():
    """Without live RAG content, reviewed chapters should not stay selectable."""
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


def test_reviewed_chapter_merge_keeps_matching_labels_and_appends_new_live_rag():
    """Admin-approved labels stay stable only when matching live content exists."""
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
        "Chapter 1: A Square and A Cube",
        "Part 2 - Chapter 1: Fractions in Disguise",
    ]


def test_reviewed_chapter_merge_groups_multi_book_chapters_by_source():
    """A stale admin review that interleaved four books' chapter numbers
    (Text Book Ch1, History Ch1, Geography Ch1, Political Science Ch1,
    Text Book Ch2, ...) must self-heal into source-grouped, chapter-ordered
    output — confirmed live for Grade 10 Social Science's dropdown, where
    the chronological self-heal in merge_reviewed_and_live_chapters()
    previously sorted by chapter number alone and interleaved every book's
    same-numbered chapter together."""
    result = syllabus_route.merge_reviewed_and_live_chapters(
        [
            "Text Book - Chapter 1: Development",
            "History - Chapter 1: The Rise of Nationalism in Europe",
            "Geography - Chapter 1: Resources and Development",
            "Political Science - Chapter 1: Power-sharing",
            "Text Book - Chapter 2: Sectors of the Indian Economy",
            "History - Chapter 2: Nationalism in India",
        ],
        [
            "Text Book - Chapter 1: Development",
            "History - Chapter 1: The Rise of Nationalism in Europe",
            "Geography - Chapter 1: Resources and Development",
            "Political Science - Chapter 1: Power-sharing",
            "Text Book - Chapter 2: Sectors of the Indian Economy",
            "History - Chapter 2: Nationalism in India",
        ],
    )

    assert result == [
        "Text Book - Chapter 1: Development",
        "Text Book - Chapter 2: Sectors of the Indian Economy",
        "History - Chapter 1: The Rise of Nationalism in Europe",
        "History - Chapter 2: Nationalism in India",
        "Geography - Chapter 1: Resources and Development",
        "Political Science - Chapter 1: Power-sharing",
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


def test_subject_override_keeps_new_live_rag_subjects_visible():
    """Newly uploaded subjects should not be hidden by an older subject review."""
    merged = {
        "Grade 10": {
            "CBSE": {
                "English": ["Chapter 1: A Letter to God"],
                "Maths": ["Chapter 1: Real Numbers"],
                "Social Science": ["Chapter 1: Development"],
                "Computer Science": ["Uploaded Book Content"],
            },
        },
    }

    result = syllabus_route.apply_subject_overrides(
        merged,
        {
            ("Grade 10", "CBSE"): {
                "subjects": ["English", "Maths"],
            },
        },
    )

    assert list(result["Grade 10"]["CBSE"].keys()) == [
        "English",
        "Maths",
        "Social Science",
    ]
    assert result["Grade 10"]["CBSE"]["Social Science"] == [
        "Chapter 1: Development",
    ]
    assert "Computer Science" not in result["Grade 10"]["CBSE"]


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
