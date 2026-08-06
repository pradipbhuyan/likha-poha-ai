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
from app.services.lesson_kb_service import (
    _generate_chips,
    _is_ungrounded_answer,
    _target_chip_count,
)
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


class TestUngroundedAnswerGuard:
    """Third anti-hallucination guard. Regression coverage for the LKB
    "Not mentioned" bug: Grade 5 English / "Vocation" / a lesson step showed
    a "students also ask" card, "What vocations are the following people
    associated with?", with all five bullets reading "<Name>: Not mentioned".

    Root cause: that question was lifted verbatim from the chapter's "Let us
    Write" section — an open-ended research/writing prompt naming five real
    public figures (A.P.J. Abdul Kalam, M. Visvesvaraya, Janaki Ammal, M.S.
    Subbulakshmi, Salim Ali) whose vocations are never stated in the Tagore
    poem itself. The RAG-grounding guard didn't catch this because RAG
    grounding for the chapter WAS present (the question text itself is in
    the chapter) — the LLM just had no factual answer to give and, instead
    of skipping the question, filled every bullet with a placeholder.
    """

    def test_is_ungrounded_answer_detects_the_exact_bug_scenario(self):
        answer = (
            "- A.P.J. Abdul Kalam: Not mentioned\n"
            "- M. Visvesvaraya: Not mentioned\n"
            "- Janaki Ammal: Not mentioned\n"
            "- M.S. Subbulakshmi: Not mentioned\n"
            "- Salim Ali: Not mentioned"
        )
        assert _is_ungrounded_answer(answer) is True

    def test_is_ungrounded_answer_ignores_normal_case(self):
        answer = (
            "- The hawker sells bangles in the morning\n"
            "- The gardener digs the ground with his spade\n"
            "- The watchman walks up and down all night\n"
            "- The poet wishes he could do these vocations too"
        )
        assert _is_ungrounded_answer(answer) is False

    def test_is_ungrounded_answer_tolerates_a_single_stray_bullet(self):
        # A well-grounded answer with ONE bullet noting a minor gap should
        # not be discarded wholesale — only when it dominates the chip.
        answer = (
            "- The hawker sells bangles in the morning\n"
            "- The gardener digs the ground with his spade\n"
            "- The watchman walks up and down all night\n"
            "- His exact age is not mentioned in the poem"
        )
        assert _is_ungrounded_answer(answer) is False

    def test_is_ungrounded_answer_handles_empty_string(self):
        assert _is_ungrounded_answer("") is False

    def test_is_ungrounded_answer_detects_hedged_phrasing(self):
        # Seen live on the same chapter, a different lesson step: a single
        # bullet hedging with "not directly answerable" rather than the
        # blunter "Not mentioned".
        answer = (
            "- This question is not directly answerable from the given "
            "content. However, it is mentioned that the speaker observes "
            "people with different vocations on his way to school and back home."
        )
        assert _is_ungrounded_answer(answer) is True

    def test_generate_chips_drops_a_chip_whose_answer_is_mostly_ungrounded(self, monkeypatch):
        """Full regression: RAG grounding present (the writing-prompt text
        itself IS in the chapter), LLM still answers with all "Not
        mentioned" bullets — the chip must be dropped, not stored."""
        monkeypatch.setattr(
            lesson_kb_service, "_get_rag_context",
            lambda *a, **kw: "word " * 600,  # rich enough for full CHIPS_PER_STEP
        )
        bad_chip = (
            '{"question": "What vocations are the following people associated with?", '
            '"answer": "- A.P.J. Abdul Kalam: Not mentioned\\n'
            '- M. Visvesvaraya: Not mentioned\\n'
            '- Janaki Ammal: Not mentioned\\n'
            '- M.S. Subbulakshmi: Not mentioned\\n'
            '- Salim Ali: Not mentioned"}'
        )
        good_chip = (
            '{"question": "What does the hawker sell?", '
            '"answer": "- Bangles\\n- Other trinkets\\n- Goods carried in a basket"}'
        )
        monkeypatch.setattr(
            lesson_kb_service, "ask_llm",
            lambda *a, **kw: f"[{bad_chip}, {good_chip}]",
        )

        chips = _generate_chips("Grade 5", "English", "9. Vocation", "What We Learn")

        assert len(chips) == 1
        assert chips[0]["question"] == "What does the hawker sell?"
