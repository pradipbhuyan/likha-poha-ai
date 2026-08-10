"""
Tests for app/services/lesson_plan_lecture_script.py — the deterministic
extractor that turns an authored lesson_plan_bank markdown handout into a
spoken teacher-lecture script (no LLM call), used by the
POST /api/teacher/lesson-plan/lecture-audio endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.lesson_plan_lecture_script import build_lecture_script

BANK_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "lesson_plan_bank"

SAMPLE_PLAN = """## Lesson Overview
- **Topic:** Sample Chapter
- **Grade:** Grade 7
- **Subject:** Science
- **Duration:** 40-45 minutes
- **CBSE Unit:** Chapter 3

## Learning Objectives
By the end of this lesson, students will be able to:
1. Describe the sample concept.
2. Explain the sample process.

## Prerequisites
Students should already know:
- Some prior fact.

## Materials & Resources
- NCERT Textbook Grade 7 Science
- Blackboard / Whiteboard

## Lesson Plan (Step-by-Step)

### Introduction & Hook (5 minutes)
- Ask: "What do you notice about X?"
- Connect to prior knowledge.

### Direct Instruction (15 minutes)
- Chunk 1: explain the sample concept with an example.
- Chunk 2: ask a question, take answers, clarify.

### Guided Practice (10 minutes)
- Work through one example together on the board.

### Student Activity (10 minutes)
- In pairs, students classify three items.

### Assessment & Closure (5 minutes)
- Quick oral question: "What did we learn today?"
- Exit ticket: one question testing the core objective.

## Homework Assignment
- Complete one practice question at home.

## Differentiation Strategies
- **For students needing additional support:** provide a word bank.
- **For students ready for extension:** ask a harder question.

## Common Misconceptions to Address
1. A common misconception about the topic.

## NCERT Alignment
- Chapter 3, covers the sample concept and process.
"""


class TestBuildLectureScript:
    def test_includes_all_spoken_stages(self):
        script = build_lecture_script(SAMPLE_PLAN)
        assert "What do you notice about X?" in script
        assert "explain the sample concept with an example" in script
        assert "Work through one example together" in script
        assert "students classify three items" in script
        assert "What did we learn today?" in script
        assert "Complete one practice question at home." in script

    def test_excludes_teacher_only_sections(self):
        script = build_lecture_script(SAMPLE_PLAN)
        assert "Differentiation" not in script
        assert "additional support" not in script
        assert "ready for extension" not in script
        assert "Misconceptions" not in script
        assert "misconception about the topic" not in script
        assert "NCERT Alignment" not in script
        assert "Prerequisites" not in script
        assert "prior fact" not in script
        assert "Materials & Resources" not in script
        assert "Blackboard" not in script
        assert "Learning Objectives" not in script

    def test_drops_timing_suffix_from_headings(self):
        script = build_lecture_script(SAMPLE_PLAN)
        assert "(5 minutes)" not in script
        assert "(15 minutes)" not in script
        assert "## Introduction & Hook" in script

    def test_empty_plan_returns_empty_script(self):
        assert build_lecture_script("") == ""
        assert build_lecture_script(None) == ""

    def test_plan_missing_a_stage_is_handled_gracefully(self):
        partial = SAMPLE_PLAN.replace(
            '### Student Activity (10 minutes)\n- In pairs, students classify three items.\n\n',
            "",
        )
        script = build_lecture_script(partial)
        assert "classify three items" not in script
        # Everything else should still be present.
        assert "What do you notice about X?" in script
        assert "Complete one practice question at home." in script


class TestFrogRegressionExample:
    """Sanity check against the real, re-authored Grade 5 'The Frog' handout."""

    @pytest.fixture
    def frog_markdown(self):
        path = BANK_ROOT / "grade_5" / "english" / "5_the_frog.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["lesson_plan_markdown"]

    def test_includes_hook_and_direct_instruction(self, frog_markdown):
        script = build_lecture_script(frog_markdown)
        assert "frog" in script.lower()
        assert "Chunk 1" in script or "sticky tongue" in script

    def test_excludes_differentiation_and_misconceptions(self, frog_markdown):
        script = build_lecture_script(frog_markdown)
        assert "students needing additional support" not in script.lower()
        assert "Common Misconceptions" not in script
        assert "NCERT Alignment" not in script


class TestHindiContentPreserved:
    """Devanagari script must pass through the extractor untouched."""

    @pytest.fixture
    def hindi_markdown(self):
        path = BANK_ROOT / "grade_5" / "hindi" / "1_करन.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["lesson_plan_markdown"]

    def test_hindi_script_extracted_and_readable(self, hindi_markdown):
        script = build_lecture_script(hindi_markdown)
        assert len(script) > 100
        # Devanagari block present (U+0900–U+097F)
        assert any("ऀ" <= ch <= "ॿ" for ch in script)
        # English section headings still present as structural markers.
        assert "## Introduction & Hook" in script
