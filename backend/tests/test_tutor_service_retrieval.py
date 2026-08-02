"""
Retrieval-only Ask Doubt pipeline tests.

answer_doubt() and answer_lesson_follow_up() must never call an LLM — every
answer comes from the Doubt Knowledge Base (DKB) cache, an extractive RAG
textbook excerpt, or a warm NCERT-reference fallback. These tests mock the
retrieval layer directly (DKB/RAG live as local imports inside the service
functions, so they must be patched on their source modules, not on
tutor_service) and assert ask_llm is never reached.
"""

import pytest

import app.services.tutor_service as tutor_service
import app.services.doubt_kb_service as doubt_kb_service


def _explode_if_llm_called(monkeypatch):
    """Fail loudly if any code path still tries to call the LLM."""
    def _boom(*args, **kwargs):
        raise AssertionError("ask_llm must never be called by the retrieval-only doubt pipeline")
    monkeypatch.setattr(tutor_service, "ask_llm", _boom)


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    _explode_if_llm_called(monkeypatch)
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


# ---------------------------------------------------------------------------
# answer_doubt()
# ---------------------------------------------------------------------------

def test_answer_doubt_dkb_hit(monkeypatch):
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


def test_answer_doubt_rag_excerpt_when_chunks_are_relevant(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Matter is anything with mass and volume.", "similarity": 0.8}],
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
    assert "Matter is anything with mass and volume." in result["answer"]
    assert stored.get("source") == "retrieval"
    assert stored.get("question") == "What is matter?"


def test_answer_doubt_fallback_when_no_relevant_chunks(monkeypatch):
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


# ---------------------------------------------------------------------------
# answer_lesson_follow_up()
# ---------------------------------------------------------------------------

def test_answer_lesson_follow_up_dkb_hit(monkeypatch):
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


def test_answer_lesson_follow_up_stores_new_excerpt_in_dkb(monkeypatch):
    """Regression test: store_in_doubt_kb was previously imported but never
    called in this function — a fresh excerpt answer must now be cached."""
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        tutor_service,
        "search_textbook_content",
        lambda **kwargs: [{"chunk_text": "Particles are tiny units of matter.", "similarity": 0.7}],
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
    assert stored.get("source") == "retrieval"
    assert stored.get("question") == "What are particles?"


def test_answer_lesson_follow_up_fallback_when_no_relevant_chunks(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(tutor_service, "search_textbook_content", lambda **kwargs: [])

    result = tutor_service.answer_lesson_follow_up(
        grade="Grade 9", mode="CBSE", subject="Science", chapter="Matter",
        step_title="Intro", lesson="Matter has mass.", question="Unrelated nonsense question?",
        username="test_user", board="CBSE",
    )

    assert result["source_type"] == "NO_MATCH_FALLBACK"
    assert result["textbook_visuals"] == []
