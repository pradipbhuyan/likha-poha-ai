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

Fix: reuse tutor_service.STORY_DEPENDENT_SUBJECTS (the same guard already
used by generate_step_lesson) inside _generate_chips — for English/Hindi/
Sanskrit/Social-Science-family subjects with zero RAG grounding, skip the
LLM call entirely and return no chips, rather than guessing.
"""
from app.services.lesson_kb_service import _generate_chips
import app.services.lesson_kb_service as lesson_kb_service


def _fail_if_called(*args, **kwargs):
    raise AssertionError("ask_llm must not be called when there is no RAG grounding for a story-dependent subject")


class TestStoryDependentHallucinationGuard:
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

    def test_non_story_subject_without_rag_still_generates_chips(self, monkeypatch):
        """Science/Maths are not passage-dependent — the pre-existing 'generate
        generic questions' fallback should still run for them."""
        monkeypatch.setattr(lesson_kb_service, "_get_rag_context", lambda *a, **kw: "")
        monkeypatch.setattr(
            lesson_kb_service, "ask_llm",
            lambda *a, **kw: '[{"question": "What is inertia?", "answer": "- Bullet one\\n- Bullet two"}]',
        )

        chips = _generate_chips("Grade 9", "Science", "Some Unmapped Chapter", "Core explanation")

        assert len(chips) == 1
        assert chips[0]["question"] == "What is inertia?"

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
