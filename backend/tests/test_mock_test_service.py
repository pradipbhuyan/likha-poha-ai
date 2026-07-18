"""
Mock-test serving is bank-only: no LLM call may ever happen at serving time.

The question bank is populated offline by the admin prewarm pipeline
(cache panel / build scripts). At serving time the service either returns
bank questions or raises a user-facing ValueError explaining the shortfall
(chapter still being prepared / chapter too small for the requested count).
"""

import pytest

import app.services.mock_test_service as mock_test_service


def _bank_question(index):
    return {
        "id": index,
        "db_id": str(1000 + index),
        "section": "MCQ",
        "question": f"Bank question {index}: which option is correct?",
        "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
        "answer": "A",
        "explanation": "Option A is correct because the bank says so clearly.",
        "marks": 1,
    }


def _forbid_llm(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("Mock-test serving must never call the LLM")

    monkeypatch.setattr(mock_test_service, "ask_llm", _fail)


def test_cbse_mock_test_serves_from_bank_without_llm(monkeypatch):
    _forbid_llm(monkeypatch)
    monkeypatch.setattr(
        mock_test_service,
        "get_questions_from_bank",
        lambda **kwargs: [_bank_question(i) for i in range(1, 11)],
    )

    questions = mock_test_service.generate_cbse_mock_test(
        grade="Grade 9",
        subject="Science",
        chapter="Matter in Our Surroundings",
        exam_type="Class Test",
        num_questions=10,
        difficulty="Medium",
    )

    assert len(questions) == 10


def test_cbse_mock_test_reports_preparing_when_bank_empty(monkeypatch):
    _forbid_llm(monkeypatch)
    monkeypatch.setattr(
        mock_test_service, "get_questions_from_bank", lambda **kwargs: []
    )
    monkeypatch.setattr(
        mock_test_service, "get_bank_capacity", lambda *args, **kwargs: 0
    )

    with pytest.raises(ValueError) as error:
        mock_test_service.generate_cbse_mock_test(
            grade="Grade 7",
            subject="Science",
            chapter="Heat",
            exam_type="Class Test",
            num_questions=10,
            difficulty="Medium",
        )

    assert "still being prepared" in str(error.value)


def test_bank_shortfall_message_chapter_too_small():
    message = mock_test_service.bank_shortfall_message(12, 50, "Small Chapter")

    assert "Small Chapter" in message
    assert "12" in message
    assert "50-question" in message
    assert "12 or fewer" in message
