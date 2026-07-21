"""
Tests for the Chapter Journey block schema and lesson_cache → ChapterDoc
converter (Phase 1). All tests are pure — DB access is monkeypatched.
"""

import pytest
from pydantic import ValidationError

import app.services.chapter_doc_service as cds
from app.models.lesson_blocks import (
    ChapterDoc,
    ConceptBlock,
    ExampleBlock,
    HookBlock,
    Milestone,
    QuickCheckBlock,
    RecapBlock,
    StudentsAskBlock,
    VocabBlock,
    WatchoutBlock,
)

CANONICAL_STEP_MD = """## 1. What you will learn
Matter is everywhere around us.

More context about the chapter here.

## Simple explanation
Solids keep shape. Liquids flow. Gases spread.

## Worked example
Question: A car travels 120 km in 2 hours. Find the speed.
Step 1: speed = distance/time
Step 2: 120 / 2 = 60
Answer: 60 km/h

## Common mistake
Students confuse mass with weight.

## Quick check question
Which state fills its container fully?

A) Solid
B) Liquid
C) Gas
D) None of these

Answer: C

Explanation: Gases expand to fill available space.

## Summary
Review these key points, then move to the next lesson step.
"""


# ─────────────────────────────────────────────────────────────── schema ──

class TestBlockSchema:
    def test_quickcheck_rejects_out_of_range_answer(self):
        with pytest.raises(ValidationError):
            QuickCheckBlock(question="Q?", options=["A", "B"], answer_index=5)

    def test_quickcheck_rejects_single_option(self):
        with pytest.raises(ValidationError):
            QuickCheckBlock(question="Q?", options=["only"], answer_index=0)

    def test_chapter_doc_rejects_empty_milestones(self):
        with pytest.raises(ValidationError):
            ChapterDoc(
                board="CBSE", grade="Grade 6", subject="Science",
                chapter="Ch 1", milestones=[],
            )

    def test_chapter_doc_roundtrips_through_json(self):
        doc = ChapterDoc(
            board="CBSE", grade="Grade 6", subject="Science", chapter="Ch 1",
            milestones=[Milestone(title="Intro", blocks=[
                HookBlock(text="Did you know?"),
                ConceptBlock(title="Idea", body_md="Body"),
            ])],
            recap=RecapBlock(body_md="Recap"),
        )
        restored = ChapterDoc.model_validate(doc.model_dump())
        assert restored.milestones[0].blocks[0].type == "hook"
        assert restored.recap.body_md == "Recap"


# ─────────────────────────────────────────────────────────────── parsing ──

class TestSectionParsing:
    def test_parses_all_canonical_sections(self):
        sections = cds.parse_sections(CANONICAL_STEP_MD)
        titles = [s["title"] for s in sections]
        assert "What you will learn" in titles
        assert "Worked example" in titles
        assert "Summary" in titles
        assert len(sections) == 6

    def test_solution_step_lines_do_not_split_sections(self):
        sections = cds.parse_sections(CANONICAL_STEP_MD)
        example = next(s for s in sections if s["title"] == "Worked example")
        assert "Step 1" in example["content"]
        assert "Step 2" in example["content"]

    def test_bold_heading_pattern(self):
        sections = cds.parse_sections("**Summary**\nAll done here.")
        assert sections[0]["title"] == "Summary"

    def test_numbered_bold_heading_pattern(self):
        sections = cds.parse_sections("**1. What You Will Learn**\nIntro text.")
        assert sections[0]["title"] == "What You Will Learn"

    def test_content_before_first_heading_becomes_introduction(self):
        sections = cds.parse_sections("Loose preamble text.\n\n## Summary\nDone.")
        assert sections[0]["title"] == "Introduction"

    def test_classify_section(self):
        assert cds.classify_section("What you will learn") == "intro"
        assert cds.classify_section("Common mistake") == "warning"
        assert cds.classify_section("Quick check question") == "check"
        assert cds.classify_section("Worked example") == "example"
        assert cds.classify_section("Revision and recap") == "summary"
        assert cds.classify_section("New Words") == "vocab"
        assert cds.classify_section("Anything else") == "concept"


class TestMcqParsing:
    def test_parses_canonical_mcq(self):
        mcq = cds.parse_mcq(
            "Which gas do plants absorb?\n\nA) Oxygen\nB) Carbon dioxide\n"
            "C) Nitrogen\nD) Helium\n\nAnswer: B\n\nExplanation: Photosynthesis uses CO2."
        )
        assert mcq is not None
        assert mcq.format == "mcq"
        assert mcq.answer_index == 1
        assert "Photosynthesis" in mcq.explanation

    def test_parses_true_false(self):
        mcq = cds.parse_mcq(
            "The sun rises in the west.\n\nA) True\nB) False\n\nAnswer: B\n\nExplanation: It rises in the east."
        )
        assert mcq is not None
        assert mcq.format == "truefalse"
        assert mcq.answer_index == 1

    def test_rejects_missing_answer_line(self):
        assert cds.parse_mcq("Q?\n\nA) x\nB) y") is None

    def test_rejects_free_text(self):
        assert cds.parse_mcq("Explain photosynthesis in your own words.") is None


class TestExampleAndVocabParsing:
    def test_parses_example(self):
        example = cds.parse_example(
            "Question: Find the area of a 3x4 rectangle.\nStep 1: A = l x b\nAnswer: 12"
        )
        assert example is not None
        assert example.question.startswith("Find the area")
        assert "Step 1" in example.body_md

    def test_example_requires_solution(self):
        assert cds.parse_example("Question: Think about it.") is None

    def test_parses_vocab_lines(self):
        vocab = cds.parse_vocab(
            "**spectacles** — glasses that help you see\n**misplaced** — put in the wrong place"
        )
        assert vocab is not None
        assert len(vocab.words) == 2
        assert vocab.words[0].term == "spectacles"


class TestQuestionDedupe:
    def test_near_duplicates_detected(self):
        assert cds.is_duplicate_question(
            "Which state of matter fills the container fully?",
            "Which state fills its container fully?",
        )

    def test_different_questions_pass(self):
        assert not cds.is_duplicate_question(
            "What is the boiling point of water?",
            "Name the three states of matter.",
        )


# ───────────────────────────────────────────────────────────── converter ──

class TestConvertChapter:
    def _patch(self, monkeypatch, step_rows, chips=None):
        monkeypatch.setattr(cds, "_fetch_step_rows", lambda *a, **k: step_rows)
        monkeypatch.setattr(cds, "_fetch_lkb_chips", lambda *a, **k: chips or [])
        monkeypatch.setattr(cds, "get_content_db", lambda grade: None)

    def test_converts_grade6_chapter(self, monkeypatch):
        steps = {
            "Concept introduction": CANONICAL_STEP_MD,
            "Core explanation": CANONICAL_STEP_MD,
            "Worked examples": CANONICAL_STEP_MD,
            "Revision and recap": CANONICAL_STEP_MD,
        }
        self._patch(monkeypatch, steps)
        doc = cds.convert_chapter("CBSE", "Grade 6", "Science", "Ch 1")
        assert doc is not None
        assert len(doc.milestones) == 4
        # Exactly one recap for the whole chapter, not one per step
        assert doc.recap is not None
        assert not any(
            b.type == "recap" for m in doc.milestones for b in m.blocks
        )

    def test_hook_only_on_first_milestone(self, monkeypatch):
        steps = {
            "Concept introduction": CANONICAL_STEP_MD,
            "Core explanation": CANONICAL_STEP_MD,
        }
        self._patch(monkeypatch, steps)
        doc = cds.convert_chapter("CBSE", "Grade 6", "Science", "Ch 1")
        first_types = [b.type for b in doc.milestones[0].blocks]
        second_types = [b.type for b in doc.milestones[1].blocks]
        assert first_types[0] == "hook"
        assert "hook" not in second_types

    def test_legacy_practice_questions_step_recovered(self, monkeypatch):
        steps = {
            "Concept introduction": CANONICAL_STEP_MD,
            "Practice questions": CANONICAL_STEP_MD,  # legacy title
        }
        self._patch(monkeypatch, steps)
        doc = cds.convert_chapter("CBSE", "Grade 9", "Science", "Ch 1")
        titles = [m.title for m in doc.milestones]
        assert "Exam-style problems" in titles

    def test_lkb_chips_attached_and_deduped(self, monkeypatch):
        steps = {"Concept introduction": CANONICAL_STEP_MD}
        chips = [
            # Near-duplicate of the in-lesson quickcheck — must be dropped
            {"question": "Which state fills its container fully then?", "answer": "Gas."},
            {"question": "Why do gases diffuse faster when heated?", "answer": "Particles move faster."},
        ]
        self._patch(monkeypatch, steps, chips)
        doc = cds.convert_chapter("CBSE", "Grade 6", "Science", "Ch 1")
        ask_blocks = [
            b for m in doc.milestones for b in m.blocks if b.type == "students_ask"
        ]
        assert len(ask_blocks) == 1
        assert "diffuse" in ask_blocks[0].question

    def test_returns_none_when_no_cache_rows(self, monkeypatch):
        self._patch(monkeypatch, {})
        assert cds.convert_chapter("CBSE", "Grade 6", "Science", "Ch 1") is None

    def test_no_content_rows_skipped(self, monkeypatch):
        # _fetch_step_rows already filters NO_CONTENT; empty result → None
        self._patch(monkeypatch, {})
        assert cds.convert_chapter("CBSE", "Grade 5", "English", "Ch 2") is None
