"""
Tests for app/services/lesson_plan_quality_checks.py — the deterministic
pedagogy quality-control pass run by scripts/ingest_gpt55_lesson_plan_output.py
on every GPT-5.5 authored lesson-plan handout before it's written into
app/data/lesson_plan_bank/.

Includes a regression test against the real, checked-in Grade 5 "The Frog"
handout (app/data/lesson_plan_bank/grade_5/english/5_the_frog.json), which
used to be a textbook example of everything the new rules forbid — too many
crammed objectives, an uninterrupted 15-minute lecture, two substantial
activities squeezed into 10 minutes, an exit ticket testing a side-topic,
"slow learners" labelling, conjunction practice deleted for support students,
and an unrelated Ganges river dolphin extension. It has since been
re-authored to follow the new rules; this test locks that in.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.lesson_plan_quality_checks import check_lesson_plan_markdown, has_errors

BANK_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "lesson_plan_bank"


def wrap(objectives_block: str, lesson_flow: str, differentiation: str,
         misconceptions: str = "1. A misconception.\n2. Another misconception.") -> str:
    """Build a minimal-but-complete lesson-plan markdown around the pieces a
    test wants to vary, keeping every other required section present so
    only the piece under test can trigger an issue."""
    return f"""## Lesson Overview
- **Topic:** Local Self-Government
- **Grade:** Grade 7
- **Subject:** Social Science
- **Duration:** 40-45 minutes
- **CBSE Unit:** Chapter 3

## Learning Objectives
By the end of this lesson, students will be able to:
{objectives_block}

## Prerequisites
Students should already know:
- What a village panchayat is.

## Materials & Resources
- NCERT Textbook Grade 7 Social Science
- Blackboard / Whiteboard

## Lesson Plan (Step-by-Step)

{lesson_flow}

## Homework Assignment
- Answer NCERT in-text question 2 about local self-government.

## Differentiation Strategies
{differentiation}

## Common Misconceptions to Address
{misconceptions}

## NCERT Alignment
- Chapter 3: Local self-government.
"""


GOOD_OBJECTIVES = (
    "1. Identify the three tiers of local self-government.\n"
    "2. Explain why local self-government brings decision-making closer to citizens.\n"
    "3. Compare the powers of a Gram Panchayat and a Municipal Corporation.\n\n"
    "Success criteria:\n"
    "- I can name the three tiers of local self-government.\n"
    "- I can explain why decisions made locally can be closer to citizens.\n"
    "- I can compare one power of a Gram Panchayat with one power of a Municipal Corporation."
)

GOOD_FLOW = """### Introduction & Hook (5 minutes)
- Ask: "Who fixes a broken street light in your area?" Take quick answers.

### Direct Instruction (15 minutes)
- Explain the three tiers (Gram Panchayat, Block, Zilla Parishad). Ask: "Which tier is closest to a village?" Take answers, then clarify.
- Explain urban local bodies (Municipal Corporation, Municipality). Ask: "Why might a city need a bigger body than a village?" Take answers, then clarify.

### Guided Practice (8 minutes)
- Sort function cards (roads, water supply, primary school) into "rural body" or "urban body" together on the board.

### Student Activity (7 minutes)
- In pairs, students list two powers of their local Gram Panchayat/Municipality from the textbook.

### Assessment & Closure (5 minutes)
- Quick oral question: "Name one power of a Gram Panchayat."
- Exit ticket: Name the three tiers of local self-government in order.
"""

GOOD_DIFFERENTIATION = (
    '- **For students needing additional support:** Provide a word bank of the three tiers '
    "and a partially filled comparison table.\n"
    '- **For students ready for extension:** Ask them to research one power their own local '
    "body exercises and justify why it sits at that tier."
)


class TestGoodPlanPassesCleanly:
    def test_no_errors_or_warnings(self):
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, grade="Grade 7", subject="Social Science")
        assert issues == []
        assert not has_errors(issues)


class TestObjectiveCount:
    def test_too_few_objectives_is_an_error(self):
        markdown = wrap("1. Identify the three tiers of local self-government.", GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)
        assert any("2-4" in i.message for i in issues)

    def test_too_many_objectives_is_an_error(self):
        objectives = "\n".join(f"{i}. Objective number {i}." for i in range(1, 6))
        markdown = wrap(objectives, GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)

    def test_vague_objective_verb_is_a_warning(self):
        objectives = GOOD_OBJECTIVES + "\n4. Learn about local government in general."
        markdown = wrap(objectives, GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert any(i.severity == "warning" and "vague" in i.message.lower() for i in issues)


class TestTiming:
    def test_stage_minutes_far_outside_duration_is_an_error(self):
        short_flow = GOOD_FLOW.replace("(15 minutes)", "(2 minutes)").replace("(8 minutes)", "(1 minutes)")
        markdown = wrap(GOOD_OBJECTIVES, short_flow, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)
        assert any("sum to" in i.message for i in issues)

    def test_uninterrupted_lecture_over_grade_band_cap_is_flagged(self):
        """Grade 5 (band 3-5) should not accept ~15 minutes of unbroken Direct
        Instruction unless the total is compensated — this is the exact
        anti-pattern the old Grade 5 'The Frog' plan had."""
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 5", "English")
        assert any("Direct Instruction" in i.message for i in issues)

    def test_direct_instruction_within_cap_for_secondary_grade_is_fine(self):
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 10", "Social Science")
        assert not any("Direct Instruction" in i.message for i in issues)

    def test_practice_time_less_than_direct_instruction_is_a_warning(self):
        lopsided_flow = GOOD_FLOW.replace("(8 minutes)", "(3 minutes)").replace("(7 minutes)", "(2 minutes)").replace(
            "(5 minutes)\n- Quick oral", "(10 minutes)\n- Quick oral"
        )
        markdown = wrap(GOOD_OBJECTIVES, lopsided_flow, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert any("at least as much time" in i.message for i in issues)


class TestDifferentiation:
    def test_slow_learners_label_is_an_error(self):
        bad_diff = (
            "- **For slow learners:** Skip the comparison task.\n"
            "- **For students ready for extension:** Research a related topic."
        )
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, bad_diff)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)
        assert any("banned label" in i.message for i in issues)

    def test_missing_extension_bullet_is_an_error(self):
        bad_diff = "- **For students needing additional support:** Provide a word bank."
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, bad_diff)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)

    def test_removing_core_content_for_support_students_is_a_warning(self):
        bad_diff = (
            "- **For students needing additional support:** Skip the tier-comparison "
            "activity entirely and only cover the hook.\n"
            "- **For students ready for extension:** Research a related topic."
        )
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, bad_diff)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert any("removes core content" in i.message for i in issues)


class TestMisconceptions:
    def test_too_many_misconceptions_is_a_warning(self):
        misconceptions = "\n".join(f"{i}. Misconception number {i}." for i in range(1, 6))
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, GOOD_DIFFERENTIATION, misconceptions=misconceptions)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert any("misconceptions listed" in i.message for i in issues)


class TestRequiredStructure:
    def test_missing_required_heading_is_an_error(self):
        markdown = wrap(GOOD_OBJECTIVES, GOOD_FLOW, GOOD_DIFFERENTIATION).replace("## Prerequisites\n", "")
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert has_errors(issues)
        assert any("Prerequisites" in i.message for i in issues)


class TestAssessmentAlignment:
    def test_exit_ticket_on_a_side_topic_is_a_warning(self):
        off_topic_flow = GOOD_FLOW.replace(
            '- Quick oral question: "Name one power of a Gram Panchayat."',
            '- Quick oral question: "Name a river that flows through your state."',
        ).replace(
            'Exit ticket: Name the three tiers of local self-government in order.',
            'Exit ticket: Name one river that flows through your state.',
        )
        markdown = wrap(GOOD_OBJECTIVES, off_topic_flow, GOOD_DIFFERENTIATION)
        issues = check_lesson_plan_markdown(markdown, "Grade 7", "Social Science")
        assert any("no significant keywords" in i.message for i in issues)


# ── Regression: the real Grade 5 "The Frog" handout ──────────────────────────

class TestFrogRegressionExample:
    """The Grade 5 English 'The Frog' handout was the literal bad example this
    quality pass exists to catch (see module docstring). It has been
    re-authored; this test proves the checked-in file now follows the rules
    and stays that way."""

    @pytest.fixture
    def frog_plan(self):
        path = BANK_ROOT / "grade_5" / "english" / "5_the_frog.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    def test_passes_the_quality_control_pass_with_no_errors(self, frog_plan):
        issues = check_lesson_plan_markdown(
            frog_plan["lesson_plan_markdown"], frog_plan["grade"], frog_plan["subject"]
        )
        assert not has_errors(issues), [str(i) for i in issues]

    def test_objective_count_is_reasonable(self, frog_plan):
        markdown = frog_plan["lesson_plan_markdown"]
        objectives_section = markdown.split("## Learning Objectives")[1].split("## Prerequisites")[0]
        numbered = [line for line in objectives_section.splitlines() if line.strip()[:2].rstrip(".").isdigit()]
        assert 2 <= len(numbered) <= 4

    def test_no_slow_learners_label(self, frog_plan):
        assert "slow learner" not in frog_plan["lesson_plan_markdown"].lower()
        assert "for students needing additional support" in frog_plan["lesson_plan_markdown"].lower()

    def test_conjunction_practice_is_kept_for_support_students_not_deleted(self, frog_plan):
        markdown = frog_plan["lesson_plan_markdown"]
        support_bullet = markdown.split("For students needing additional support:")[1].split("\n-")[0]
        assert "conjunction" in support_bullet.lower()
        assert "skip" not in support_bullet.lower()

    def test_no_unrelated_ganges_dolphin_extension(self, frog_plan):
        assert "ganges" not in frog_plan["lesson_plan_markdown"].lower()
        assert "dolphin" not in frog_plan["lesson_plan_markdown"].lower()

    def test_exit_ticket_assesses_core_objectives_not_frog_vs_toad(self, frog_plan):
        markdown = frog_plan["lesson_plan_markdown"]
        exit_ticket_line = next(l for l in markdown.splitlines() if l.strip().startswith("- Exit ticket"))
        assert "toad" not in exit_ticket_line.lower()
        assert "rhym" in exit_ticket_line.lower() or "conjunction" in exit_ticket_line.lower() or "because" in exit_ticket_line.lower()

    def test_student_activity_stage_has_one_primary_task_not_two(self, frog_plan):
        markdown = frog_plan["lesson_plan_markdown"]
        activity_section = markdown.split("### Student Activity")[1].split("### Assessment")[0]
        # The old version had two substantial tasks (draw a scene, AND compare
        # frog vs toad) inside one 10-minute window; the toad comparison must
        # not appear as a required part of the main activity anymore.
        assert "toad" not in activity_section.lower()

    def test_direct_instruction_is_not_a_single_uninterrupted_block(self, frog_plan):
        markdown = frog_plan["lesson_plan_markdown"]
        instruction_section = markdown.split("### Direct Instruction")[1].split("### Guided Practice")[0]
        # Broken into chunks means multiple bullet points with embedded questions.
        assert instruction_section.count("Ask:") + instruction_section.count("Ask \"") >= 2
