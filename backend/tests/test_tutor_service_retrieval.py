"""
Ask Doubt pipeline tests.

answer_doubt() and answer_lesson_follow_up() are DKB-first: a cache hit, or a
true no-match ("NO_MATCH_FALLBACK"), must still cost zero LLM calls. On a RAG
chunk match, the pipeline synthesizes a direct answer via one cheap LLM call
(build_synthesized_doubt_answer / ask_llm) instead of pasting the raw chunk
text -- build_textbook_excerpt_answer is kept only as a fallback if that call
fails. DKB/RAG live as local imports inside the service functions, so they
must be patched on their source modules, not on tutor_service.

allow_llm gates whether a DKB miss may reach RAG/LLM at all: free tier calls
with allow_llm=False and must NEVER touch RAG/LLM on a miss -- it gets the
standard upgrade prompt (offer_access_service.build_offer_gate_response)
instead. Paid tier calls with allow_llm=True (the default) and can fall back
to LLM synthesis as a last resort, as tested above.
"""

import pytest

import app.services.tutor_service as tutor_service
import app.services.doubt_kb_service as doubt_kb_service


def _explode_if_llm_called(monkeypatch):
    """Fail loudly if a code path expected to be LLM-free calls ask_llm."""
    def _boom(*args, **kwargs):
        raise AssertionError("ask_llm must not be called on this path")
    monkeypatch.setattr(tutor_service, "ask_llm", _boom)


@pytest.fixture(autouse=True)
def _quiet_side_effects(monkeypatch):
    # Keep answers out of DKB/analytics tables by default; individual tests
    # override these when they want to assert on the call.
    monkeypatch.setattr(doubt_kb_service, "store_in_doubt_kb", lambda **kwargs: None, raising=False)
    monkeypatch.setattr(tutor_service, "save_mentor_memory", lambda **kwargs: None, raising=False)
    monkeypatch.setattr(tutor_service, "find_visual_assets_for_question", lambda **kwargs: [], raising=False)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

def test_filter_relevant_chunks_drops_weak_matches():
    chunks = [
        {"chunk_text": "strong match", "similarity": 0.9},
        {"chunk_text": "weak match", "similarity": 0.1},
        {"chunk_text": "borderline", "similarity": tutor_service.RAG_ANSWER_THRESHOLD},
    ]
    result = tutor_service._filter_relevant_chunks(chunks)
    assert [c["chunk_text"] for c in result] == ["strong match", "borderline"]


def test_filter_relevant_chunks_handles_missing_similarity():
    assert tutor_service._filter_relevant_chunks([{"chunk_text": "no score"}]) == []
    assert tutor_service._filter_relevant_chunks(None) == []


def test_build_textbook_excerpt_answer_joins_top_chunks():
    chunks = [
        {"chunk_text": "First chunk."},
        {"chunk_text": "Second chunk."},
        {"chunk_text": "Third chunk (should be dropped by max_chunks)."},
    ]
    answer = tutor_service.build_textbook_excerpt_answer(chunks, max_chunks=2)
    assert "First chunk." in answer
    assert "Second chunk." in answer
    assert "Third chunk" not in answer
    assert answer.startswith("Here's what your textbook says about this:")


def test_build_ncert_fallback_answer_never_mentions_internals():
    answer = tutor_service.build_ncert_fallback_answer("Grade 9", "Science", "Matter in Our Surroundings")
    lowered = answer.lower()
    for forbidden in ["rag", "vector", "similarity", "embedding"]:
        assert forbidden not in lowered
    assert "ncert" in lowered
    assert "Grade 9" in answer
    assert "Science" in answer


def test_build_synthesized_doubt_answer_grounds_llm_call_in_chunks(monkeypatch):
    captured = {}

    def _fake_ask_llm(system_prompt, user_prompt, **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["kwargs"] = kwargs
        return "Synthesized answer."

    monkeypatch.setattr(tutor_service, "ask_llm", _fake_ask_llm)

    answer = tutor_service.build_synthesized_doubt_answer(
        question="What is matter?",
        chunks=[{"chunk_text": "Matter is anything with mass and volume."}],
        grade="Grade 9", subject="Science", chapter="Matter",
    )

    assert answer == "Synthesized answer."
    assert "What is matter?" in captured["user_prompt"]
    assert "Matter is anything with mass and volume." in captured["user_prompt"]
    assert captured["kwargs"]["model"] == tutor_service.DEFAULT_TEXT_MODEL
    assert captured["kwargs"]["feature"] == "doubt_answer_live_synthesis"


# ---------------------------------------------------------------------------
# answer_doubt()
# ---------------------------------------------------------------------------

def test_answer_doubt_dkb_hit(monkeypatch):
    _explode_if_llm_called(monkeypatch)  # cache hit must cost zero LLM calls
    monkeypatch.setattr(
        doubt_kb_service,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached answer", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is matter?", username="test_user", board="CBSE",
    )

    assert result["source_type"] == "DOUBT_KB"
    assert result["answer"] == "Cached answer"
    assert result["sources"] == []


def test_answer_doubt_synthesizes_answer_when_chunks_are_relevant(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Matter is anything with mass and volume.", "similarity": 0.8}],
    )
    monkeypatch.setattr(
        tutor_service, "ask_llm",
        lambda *a, **k: "Matter is anything that has mass and takes up space.",
    )

    stored = {}
    monkeypatch.setattr(
        doubt_kb_service,
        "store_in_doubt_kb",
        lambda **kwargs: stored.update(kwargs),
    )

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is matter?", username="test_user", board="CBSE",
    )

    assert result["source_type"] == "TEXTBOOK_EXCERPT"
    assert result["answer"] == "Matter is anything that has mass and takes up space."
    assert stored.get("source") == "retrieval"
    assert stored.get("answer") == result["answer"]


def test_answer_doubt_falls_back_to_extractive_excerpt_when_synthesis_fails(monkeypatch):
    """LLM synthesis failing (e.g. API disabled) must never break doubt delivery."""
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Matter is anything with mass and volume.", "similarity": 0.8}],
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("LLM unavailable")
    monkeypatch.setattr(tutor_service, "ask_llm", _boom)

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is matter?", username="test_user", board="CBSE",
    )

    assert result["source_type"] == "TEXTBOOK_EXCERPT"
    assert "Matter is anything with mass and volume." in result["answer"]


def test_answer_doubt_fallback_when_no_relevant_chunks(monkeypatch):
    _explode_if_llm_called(monkeypatch)  # a true miss must cost zero LLM calls
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(tutor_service, "search_textbook_content", lambda **kwargs: [])

    stored = {"called": False}
    monkeypatch.setattr(
        doubt_kb_service,
        "store_in_doubt_kb",
        lambda **kwargs: stored.update(called=True),
    )

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is the capital of Mars?", username="test_user", board="CBSE",
    )

    assert result["source_type"] == "NO_MATCH_FALLBACK"
    assert "NCERT" in result["answer"] or "ncert" in result["answer"].lower()
    assert stored["called"] is False, "A fallback answer must never be cached in the DKB"
    assert result["textbook_visuals"] == []


def test_answer_doubt_ignores_weak_rag_matches(monkeypatch):
    """A low-similarity chunk must not be shown as if it were a real answer."""
    _explode_if_llm_called(monkeypatch)
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Unrelated passage.", "similarity": 0.05}],
    )

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is matter?", username="test_user", board="CBSE",
    )

    assert result["source_type"] == "NO_MATCH_FALLBACK"
    assert "Unrelated passage." not in result["answer"]


def test_answer_doubt_free_tier_never_touches_rag_or_llm_on_dkb_miss(monkeypatch):
    """allow_llm=False (free tier) on a DKB miss must show the standard
    upgrade prompt and never call search_textbook_content or ask_llm."""
    _explode_if_llm_called(monkeypatch)
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)

    def _boom_rag(*args, **kwargs):
        raise AssertionError("search_textbook_content must not be called for free tier")
    monkeypatch.setattr(tutor_service, "search_textbook_content", _boom_rag)

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="Some question with no DKB match", username="test_user",
        board="CBSE", allow_llm=False,
    )

    assert result["source_type"] == "OFFER_GATE"
    assert "upgrade" in result["answer"].lower() or "subscription" in result["answer"].lower()
    assert result["sources"] == []
    assert result["textbook_visuals"] == []


def test_answer_doubt_free_tier_still_gets_dkb_hits(monkeypatch):
    """allow_llm=False must not affect the DKB-hit path — only gates misses."""
    _explode_if_llm_called(monkeypatch)
    monkeypatch.setattr(
        doubt_kb_service,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached answer", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    result = tutor_service.answer_doubt(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        question="What is matter?", username="test_user", board="CBSE",
        allow_llm=False,
    )

    assert result["source_type"] == "DOUBT_KB"
    assert result["answer"] == "Cached answer"


# ---------------------------------------------------------------------------
# answer_lesson_follow_up()
# ---------------------------------------------------------------------------

def test_answer_lesson_follow_up_dkb_hit(monkeypatch):
    _explode_if_llm_called(monkeypatch)  # cache hit must cost zero LLM calls
    monkeypatch.setattr(
        doubt_kb_service,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached follow-up answer", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="What is matter?",
        username="test_user", board="CBSE",
    )

    assert result["source_type"] == "DOUBT_KB"
    assert result["answer"] == "Cached follow-up answer"


def test_answer_lesson_follow_up_synthesizes_and_stores_new_answer_in_dkb(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Particles are tiny units of matter.", "similarity": 0.7}],
    )
    monkeypatch.setattr(
        tutor_service, "ask_llm",
        lambda *a, **k: "Particles are the tiny building blocks that make up all matter.",
    )

    stored = {}
    monkeypatch.setattr(
        doubt_kb_service,
        "store_in_doubt_kb",
        lambda **kwargs: stored.update(kwargs),
    )

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="What are particles?",
        username="test_user", board="CBSE",
    )

    assert result["source_type"] == "TEXTBOOK_EXCERPT"
    assert result["answer"] == "Particles are the tiny building blocks that make up all matter."
    assert stored.get("source") == "retrieval"
    assert stored.get("question") == "What are particles?"
    assert stored.get("answer") == result["answer"]


def test_answer_lesson_follow_up_falls_back_to_extractive_excerpt_when_synthesis_fails(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Particles are tiny units of matter.", "similarity": 0.7}],
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("LLM unavailable")
    monkeypatch.setattr(tutor_service, "ask_llm", _boom)

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="What are particles?",
        username="test_user", board="CBSE",
    )

    assert result["source_type"] == "TEXTBOOK_EXCERPT"
    assert "Particles are tiny units of matter." in result["answer"]


def test_answer_lesson_follow_up_fallback_when_no_relevant_chunks(monkeypatch):
    _explode_if_llm_called(monkeypatch)  # a true miss must cost zero LLM calls
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(tutor_service, "search_textbook_content", lambda **kwargs: [])

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="Unrelated nonsense question?",
        username="test_user", board="CBSE",
    )

    assert result["source_type"] == "NO_MATCH_FALLBACK"
    assert result["textbook_visuals"] == []


def test_answer_lesson_follow_up_free_tier_never_touches_rag_or_llm_on_dkb_miss(monkeypatch):
    """allow_llm=False (free tier) on a DKB miss must show the standard
    upgrade prompt and never call search_textbook_content or ask_llm."""
    _explode_if_llm_called(monkeypatch)
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)

    def _boom_rag(*args, **kwargs):
        raise AssertionError("search_textbook_content must not be called for free tier")
    monkeypatch.setattr(tutor_service, "search_textbook_content", _boom_rag)

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.",
        question="Some question with no DKB match", username="test_user",
        board="CBSE", allow_llm=False,
    )

    assert result["source_type"] == "OFFER_GATE"
    assert "upgrade" in result["answer"].lower() or "subscription" in result["answer"].lower()
    assert result["textbook_visuals"] == []


def test_answer_lesson_follow_up_free_tier_still_gets_dkb_hits(monkeypatch):
    """allow_llm=False must not affect the DKB-hit path — only gates misses."""
    _explode_if_llm_called(monkeypatch)
    monkeypatch.setattr(
        doubt_kb_service,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached follow-up answer", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="What is matter?",
        username="test_user", board="CBSE", allow_llm=False,
    )

    assert result["source_type"] == "DOUBT_KB"
    assert result["answer"] == "Cached follow-up answer"
