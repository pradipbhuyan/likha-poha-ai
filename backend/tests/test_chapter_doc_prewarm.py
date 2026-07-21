"""
Tests for prewarm v2 native chapter-doc generation (Phase 3).
All LLM and RAG calls are monkeypatched — zero tokens, zero network.
"""

import json

import pytest
from pydantic import ValidationError

import app.services.chapter_doc_prewarm_service as prewarm
from app.models.lesson_blocks import ChapterDoc, ExamQABlock


OUTLINE_JSON = json.dumps({"milestones": ["What is matter?", "States of matter", "Change of state"]})

BLOCKS_JSON = json.dumps({"blocks": [
    {"type": "concept", "title": "Particles", "body_md": "Matter is made of particles.", "key_terms": []},
    {"type": "quickcheck", "format": "mcq", "question": "Which state flows?",
     "options": ["Solid", "Liquid", "Rock", "Wood"], "answer_index": 1, "explanation": "Liquids flow."},
]})

RECAP_EXAM_JSON = json.dumps({
    "recap": {"type": "recap", "body_md": "- Matter has three states.\n\nMove to the next chapter."},
    "exam": [
        {"type": "exam_qa", "marks": 3, "year": "", "question": "Define matter with two examples.",
         "model_answer_md": "Matter occupies space and has mass. Examples: air, water."},
    ],
})


def _patch_llm(monkeypatch, responses):
    """Feed canned responses to _ask_json's underlying ask_llm call, in call order."""
    calls = {"n": 0}

    def fake_ask_llm(system, prompt, **kwargs):
        index = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        response = responses[index]
        return response(prompt) if callable(response) else response

    monkeypatch.setattr(prewarm, "ask_llm", fake_ask_llm)
    return calls


class TestSchemaExamQA:
    def test_exam_qa_valid(self):
        block = ExamQABlock(marks=5, question="Q?", model_answer_md="A.")
        assert block.type == "exam_qa"

    def test_exam_qa_rejects_bad_marks(self):
        with pytest.raises(ValidationError):
            ExamQABlock(marks=0, question="Q?", model_answer_md="A.")

    def test_chapter_doc_accepts_exam_list(self):
        doc = ChapterDoc(
            board="CBSE", grade="Grade 10", subject="Science", chapter="Ch 11",
            milestones=[{"title": "M", "blocks": [{"type": "concept", "body_md": "x"}]}],
            exam=[{"type": "exam_qa", "marks": 3, "question": "Q?", "model_answer_md": "A."}],
        )
        assert len(doc.exam) == 1


class TestJsonParsing:
    def test_plain_json(self):
        assert prewarm._parse_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert prewarm._parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_repairs_literal_newline_in_string(self):
        broken = '{"body_md": "Line one.\nLine two."}'
        assert prewarm._parse_json(broken) == {"body_md": "Line one.\nLine two."}

    def test_repairs_invalid_latex_backslash_escape(self):
        # \frac and \sqrt are common LaTeX the model emits without escaping
        # the backslash — invalid JSON, but recoverable.
        broken = r'{"body_md": "Use $\frac{a}{b}$ and $\sqrt{x}$."}'
        result = prewarm._parse_json(broken)
        assert result["body_md"] == r"Use $\frac{a}{b}$ and $\sqrt{x}$."

    def test_valid_escapes_untouched(self):
        clean = '{"body_md": "Tab:\\there. Quote: \\"hi\\"."}'
        result = prewarm._parse_json(clean)
        assert result["body_md"] == 'Tab:\there. Quote: "hi".'

    def test_ask_json_retries_once_then_succeeds(self, monkeypatch):
        calls = _patch_llm(monkeypatch, ["not json at all", '{"ok": true}'])
        result = prewarm._ask_json("prompt", "tester", "test", "model-x")
        assert result == {"ok": True}
        assert calls["n"] == 2

    def test_ask_json_raises_after_two_failures(self, monkeypatch):
        _patch_llm(monkeypatch, ["garbage", "still garbage"])
        with pytest.raises(json.JSONDecodeError):
            prewarm._ask_json("prompt", "tester", "test", "model-x")


class TestGenerateChapterDocV2:
    def _patch_rag(self, monkeypatch, context="Textbook says matter has particles."):
        monkeypatch.setattr(prewarm, "_fetch_rag_context", lambda *a, **k: context)

    def test_generates_full_senior_doc(self, monkeypatch):
        self._patch_rag(monkeypatch)
        # 1 outline + 3 milestones + 1 recap/exam = 5 calls
        _patch_llm(monkeypatch, [OUTLINE_JSON, BLOCKS_JSON, BLOCKS_JSON, BLOCKS_JSON, RECAP_EXAM_JSON])
        doc = prewarm.generate_chapter_doc_v2("CBSE", "Grade 10", "Science", "Matter")
        assert doc is not None
        assert doc.source == "prewarm_v2"
        assert [m.title for m in doc.milestones] == ["What is matter?", "States of matter", "Change of state"]
        assert doc.recap is not None
        assert len(doc.exam) == 1
        assert doc.exam[0].marks == 3

    def test_junior_doc_has_no_exam(self, monkeypatch):
        self._patch_rag(monkeypatch)
        junior_recap = json.dumps({"recap": {"type": "recap", "body_md": "- Points."}, "exam": []})
        _patch_llm(monkeypatch, [OUTLINE_JSON, BLOCKS_JSON, BLOCKS_JSON, BLOCKS_JSON, junior_recap])
        doc = prewarm.generate_chapter_doc_v2("CBSE", "Grade 6", "Science", "Matter")
        assert doc is not None
        assert doc.exam == []

    def test_refuses_story_subject_without_rag(self, monkeypatch):
        self._patch_rag(monkeypatch, context="")
        _patch_llm(monkeypatch, [OUTLINE_JSON])
        doc = prewarm.generate_chapter_doc_v2("CBSE", "Grade 6", "English", "Unit 2: Friendship")
        assert doc is None

    def test_returns_none_on_invalid_blocks(self, monkeypatch):
        self._patch_rag(monkeypatch)
        bad_blocks = json.dumps({"blocks": [
            {"type": "quickcheck", "format": "mcq", "question": "Q?",
             "options": ["only one"], "answer_index": 0, "explanation": ""},
        ]})
        # Invalid blocks are returned on BOTH attempts (retry also fails validation
        # is not retried — validation errors fail fast by design)
        _patch_llm(monkeypatch, [OUTLINE_JSON, bad_blocks])
        doc = prewarm.generate_chapter_doc_v2("CBSE", "Grade 10", "Science", "Matter")
        assert doc is None

    def test_returns_none_on_bad_outline_count(self, monkeypatch):
        self._patch_rag(monkeypatch)
        _patch_llm(monkeypatch, [json.dumps({"milestones": ["only one"]})])
        doc = prewarm.generate_chapter_doc_v2("CBSE", "Grade 10", "Science", "Matter")
        assert doc is None
