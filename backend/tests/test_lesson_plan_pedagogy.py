"""
Tests for app/services/lesson_plan_pedagogy.py — the grade/subject-adaptive
lesson-plan authoring prompt builder used by
scripts/prepare_gpt55_lesson_plan_prompts.py.

These tests exercise the prompt builder (not a live LLM call — this pipeline
authors lesson plans offline; see docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md)
across the grade/subject combinations called out in the lesson-plan quality
requirements, verifying the prompt adapts automatically rather than being
hard-coded to any one grade or subject.
"""
import pytest

from app.services.lesson_plan_pedagogy import (
    DURATION_MAX_MINUTES,
    DURATION_MIN_MINUTES,
    GRADE_BAND_PEDAGOGY,
    GRADE_BAND_TEACHER_TALK_CAP_MINUTES,
    SUBJECT_PEDAGOGY,
    build_lesson_plan_prompt,
    grade_band,
    grade_number,
    subject_category,
)


# ── grade_number / grade_band ────────────────────────────────────────────────

class TestGradeBand:
    @pytest.mark.parametrize("grade,expected_number", [
        ("Grade 1", 1), ("Grade 5", 5), ("Grade 9", 9), ("Grade 12", 12),
    ])
    def test_grade_number_parses_the_digit(self, grade, expected_number):
        assert grade_number(grade) == expected_number

    @pytest.mark.parametrize("grade,expected_band", [
        ("Grade 1", "1-2"), ("Grade 2", "1-2"),
        ("Grade 3", "3-5"), ("Grade 4", "3-5"), ("Grade 5", "3-5"),
        ("Grade 6", "6-8"), ("Grade 7", "6-8"), ("Grade 8", "6-8"),
        ("Grade 9", "9-12"), ("Grade 10", "9-12"), ("Grade 11", "9-12"), ("Grade 12", "9-12"),
    ])
    def test_band_boundaries(self, grade, expected_band):
        assert grade_band(grade) == expected_band

    def test_unparseable_grade_falls_back_safely(self):
        # Should not raise, and should land in a real band.
        assert grade_band("Kindergarten") in GRADE_BAND_PEDAGOGY


# ── subject_category ─────────────────────────────────────────────────────────

class TestSubjectCategory:
    @pytest.mark.parametrize("subject,expected_category", [
        ("English", "languages"),
        ("Hindi", "languages"),
        ("Mathematics", "mathematics"),
        ("Maths Standard", "mathematics"),
        ("Science", "science"),
        ("Physics", "science"),
        ("EVS", "science"),
        ("Social Science", "social_science"),
        ("History", "social_science"),
        ("Geography", "social_science"),
        ("Computer Science", "computer_science"),
        ("Art", "skill_subject"),
        ("Physical Education", "skill_subject"),
    ])
    def test_known_subjects_route_correctly(self, subject, expected_category):
        assert subject_category(subject) == expected_category

    def test_unknown_subject_falls_back_to_general_academic(self):
        assert subject_category("Some Future Elective") == "general_academic"
        assert "general_academic" in SUBJECT_PEDAGOGY


# ── build_lesson_plan_prompt: the required grade/subject scenarios ──────────

REQUIRED_SCENARIOS = [
    ("Grade 1", "English"),
    ("Grade 3", "Mathematics"),
    ("Grade 5", "English"),
    ("Grade 5", "Science"),
    ("Grade 7", "Social Science"),
    ("Grade 8", "Mathematics"),
    ("Grade 10", "Science"),
    ("Grade 10", "English"),
    ("Grade 12", "Mathematics"),
    ("Grade 12", "Physics"),
]


class TestBuildLessonPlanPrompt:
    @pytest.mark.parametrize("grade,subject", REQUIRED_SCENARIOS)
    def test_prompt_embeds_matching_grade_band_and_subject_pedagogy(self, grade, subject):
        prompt = build_lesson_plan_prompt(
            grade=grade, subject=subject, chapter="Test Chapter",
            chapter_lesson_text="Some grounded chapter content about the topic. " * 10,
        )
        band = grade_band(grade)
        category = subject_category(subject)

        # The exact grade-band and subject-pedagogy blocks must be present —
        # this is the "adapts automatically" contract, not per-call text.
        assert GRADE_BAND_PEDAGOGY[band] in prompt
        assert SUBJECT_PEDAGOGY[category] in prompt

        # Core binding rules present in every prompt regardless of grade/subject.
        assert "2-4 core learning objectives" in prompt
        assert "DEPTH OVER BREADTH" in prompt
        assert f"{DURATION_MIN_MINUTES}" in prompt and f"{DURATION_MAX_MINUTES}" in prompt
        # The banned labels are named explicitly so the model knows to avoid them,
        # but only inside a prohibition — never as the instructed bullet label itself.
        assert 'Never use the labels "slow learners"' in prompt
        assert "students needing additional support" in prompt.lower()
        assert "students ready for extension" in prompt.lower()
        assert "never invent" in prompt.lower()

        # Chapter/grade/subject are threaded through, not hard-coded.
        assert "Test Chapter" in prompt
        assert grade in prompt
        assert subject in prompt

    def test_different_grade_bands_get_different_teacher_talk_caps(self):
        young = build_lesson_plan_prompt("Grade 1", "English", "Ch", "text " * 20)
        senior = build_lesson_plan_prompt("Grade 11", "Physics", "Ch", "text " * 20)
        young_cap = GRADE_BAND_TEACHER_TALK_CAP_MINUTES[grade_band("Grade 1")]
        senior_cap = GRADE_BAND_TEACHER_TALK_CAP_MINUTES[grade_band("Grade 11")]
        assert young_cap < senior_cap
        assert str(young_cap) in young
        assert str(senior_cap) in senior

    def test_no_hard_coded_frog_or_grade_5_content(self):
        """The prompt builder must not special-case any one chapter/grade —
        e.g. the historical Grade 5 'The Frog' example must not leak into a
        prompt for an unrelated grade/subject/chapter."""
        prompt = build_lesson_plan_prompt(
            "Grade 9", "Mathematics", "Quadratic Equations", "Algebra content. " * 10
        )
        assert "frog" not in prompt.lower()
        assert "the frog" not in prompt.lower()

    def test_mathematics_and_science_get_distinct_pedagogy_blocks(self):
        math_prompt = build_lesson_plan_prompt("Grade 8", "Mathematics", "Ch", "text " * 20)
        science_prompt = build_lesson_plan_prompt("Grade 8", "Science", "Ch", "text " * 20)
        assert SUBJECT_PEDAGOGY["mathematics"] in math_prompt
        assert SUBJECT_PEDAGOGY["mathematics"] not in science_prompt
        assert SUBJECT_PEDAGOGY["science"] in science_prompt
        assert SUBJECT_PEDAGOGY["science"] not in math_prompt
