from app.data.syllabus import SYLLABUS


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
