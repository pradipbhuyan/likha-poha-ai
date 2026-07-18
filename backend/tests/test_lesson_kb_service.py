"""
test_lesson_kb_service.py — Anti-hallucination guard for LKB chip generation.

Bug context (Defect e12251ed-e6c6-4262-9862-94982582ecdb):
Grade 11 English / "5. The Frog" / "What We Learn" showed 5 hallucinated
Biology questions about real frogs (respiration, digestion, eggs,
metamorphosis) plus a leaked "Not relevant to the lesson." aside.

Root cause: "5. The Frog" is a Grade 5 English poem with zero RAG content
under Grade 11/English. lesson_kb_service._generate_chips() had NO
anti-hallucination guard — when RAG returned nothing, it explicitly told the
LLM "generate generic but educationally sound questions for this topic"
anyway. With no grounding, the LLM defaulted to its strongest prior for
"Grade 11" + "Frog" (the well-known CBSE Class 11 Biology Rana tigrina
chapter) instead of refusing to answer.

Widened (2026-07-17) after an audit found ALL existing LKB chips, in every
subject, were generated during a period when RAG lookup was silently broken
(search_rag didn't exist — see _get_rag_context's docstring). The guard now
fires on zero RAG grounding for ANY subject, not just STORY_DEPENDENT_SUBJECTS
— refusing to guess is strictly better than serving plausible-but-ungrounded
content, and that failure mode isn't unique to language/literature chapters.

Also added: chip count now scales with how much RAG content came back
(_target_chip_count) instead of always demanding 5 — a thin chapter only
supports a couple of distinct, well-grounded questions, and forcing 5 just
pressures the model to pad with repetitive or weakly-grounded filler.
"""
from app.services.lesson_kb_service import _generate_chips, _target_chip_count
import app.services.lesson_kb_service as lesson_kb_service


def _fail_if_called(*args, **kwargs):
    raise AssertionError("ask_llm must not be called when there is no RAG grounding")


class TestHallucinationGuard:
    def test_rejects_ungrounded_story_subject_exact_bug_scenario(self, monkeypatch):
        """Regression test for defect e12251ed-e6c6-4262-9862-94982582ecdb."""
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "")
        monkeypatch.setattr(lesson_kb_service, "ask_llm", _fail_if_called)

        chips = _generate_chips("Grade 11", "English", "5. The Frog", "What We Learn")

        assert chips == []

    def test_rejects_ungrounded_hindi_and_social_science_too(self, monkeypatch):
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "")
        monkeypatch.setattr(lesson_kb_service, "ask_llm", _fail_if_called)

        assert _generate_chips("Grade 10", "Hindi", "Some Unmapped Chapter", "Concept introduction") == []
        assert _generate_chips("Grade 9", "Social Science", "Some Unmapped Chapter", "Core explanation") == []

    def test_rejects_ungrounded_non_story_subject_too(self, monkeypatch):
        """Widened guard: Science/Maths with zero RAG grounding must also
        refuse to guess now, rather than falling back to generic questions."""
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "")
        monkeypatch.setattr(lesson_kb_service, "ask_llm", _fail_if_called)

        assert _generate_chips("Grade 9", "Science", "Some Unmapped Chapter", "Core explanation") == []
        assert _generate_chips("Grade 11", "Mathematics", "Some Unmapped Chapter", "Worked examples") == []

    def test_story_dependent_subject_with_rag_generates_chips_normally(self, monkeypatch):
        """The guard must only fire on zero RAG grounding — grounded story
        chapters (the normal case) must keep working exactly as before."""
        monkeypatch.setattr(
            lesson_kb_service, "_get_rag_context",
            lambda *a, **kw: "The Frog by Norman Gale satirises human manners.",
        )
        monkeypatch.setattr(
            lesson_kb_service, "ask_llm",
            lambda *a, **kw: '[{"question": "What does the poet satirise?", "answer": "- Human manners\\n- Social snobbery"}]',
        )

        chips = _generate_chips("Grade 5", "English", "5. The Frog", "What We Learn")

        assert len(chips) == 1
        assert "satirise" in chips[0]["question"]


class TestGraduatedChipCount:
    def test_target_chip_count_scales_with_rag_word_count(self):
        assert _target_chip_count("word " * 10) == 1     # very thin match
        assert _target_chip_count("word " * 100) == 2
        assert _target_chip_count("word " * 200) == 3
        assert _target_chip_count("word " * 400) == 4
        assert _target_chip_count("word " * 600) == 5    # full CHIPS_PER_STEP

    def test_generate_chips_caps_output_to_target_for_thin_rag(self, monkeypatch):
        """A thin RAG match (~10 words) should only ever keep 1 chip, even if
        the LLM (ignoring instructions) returns more than that."""
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "word " * 10)
        monkeypatch.setattr(
            lesson_kb_service, "ask_llm",
            lambda *a, **kw: (
                '[{"question": "Q1", "answer": "- a\\n- b"},'
                ' {"question": "Q2", "answer": "- c\\n- d"}]'
            ),
        )

        chips = _generate_chips("Grade 9", "Science", "Short Chapter", "Core explanation")

        assert len(chips) == 1
        assert chips[0]["question"] == "Q1"

    def test_generate_chips_allows_full_count_for_rich_rag(self, monkeypatch):
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "word " * 600)
        five_chips = ", ".join(
            f'{{"question": "Q{i}", "answer": "- a\\n- b"}}' for i in range(5)
        )
        monkeypatch.setattr(lesson_kb_service, "ask_llm", lambda *a, **kw: f"[{five_chips}]")

        chips = _generate_chips("Grade 9", "Science", "Rich Chapter", "Core explanation")

        assert len(chips) == 5
