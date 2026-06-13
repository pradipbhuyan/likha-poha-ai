import json

import pytest

import app.services.mock_test_service as mock_test_service


def make_rag_item(text, title, subject="Science Olympiad", chapter="Force"):
    return {
        "chunk_text": text,
        "document": {
            "title": title,
            "subject": subject,
            "chapter": chapter,
        },
    }


def test_sof_mock_test_requires_uploaded_rag_content(monkeypatch):
    monkeypatch.setattr(
        mock_test_service,
        "search_textbook_content",
        lambda **kwargs: [],
    )

    with pytest.raises(ValueError) as error:
        mock_test_service.generate_olympiad_mock_test(
            olympiad="Science Olympiad",
            chapter="Force",
            grade="Grade 9",
            num_questions=3,
            difficulty="Medium",
        )

    assert "No RAG content found for Science Olympiad - Force" in str(error.value)


def test_sof_mock_test_prompt_uses_chapter_exercise_and_model_paper_rag(monkeypatch):
    captured_prompt = {}

    # Ensure bank is empty so the test always falls through to LLM generation
    monkeypatch.setattr(
        mock_test_service,
        "get_questions_from_bank",
        lambda **kwargs: [],
    )

    def fake_search_textbook_content(query, grade, subject, chapter, match_count):
        if "exercise practice questions" in query:
            return [
                make_rag_item(
                    "Exercise question about force and acceleration.",
                    "Force - Exercise",
                    chapter=chapter,
                )
            ]

        if "model mock test paper" in query:
            return [
                make_rag_item(
                    "Model paper asks application based force questions.",
                    "SOF-ISO Model Test Paper-1",
                    chapter=chapter,
                )
            ]

        return [
            make_rag_item(
                "Force changes the state of motion of an object.",
                "Force - Chapter",
                chapter=chapter,
            )
        ]

    def fake_ask_llm(system_prompt, user_prompt, username, feature, model=None):
        captured_prompt["system_prompt"] = system_prompt
        captured_prompt["user_prompt"] = user_prompt
        captured_prompt["username"] = username
        captured_prompt["feature"] = feature
        captured_prompt["model"] = model

        return json.dumps(
            {
                "questions": [
                    {
                        "id": 1,
                        "section": "Science",
                        "question": "A force acts on a moving object. What can change?",
                        "options": {
                            "A": "Only mass",
                            "B": "Only color",
                            "C": "State of motion",
                            "D": "Only temperature",
                        },
                        "answer": "C",
                        "explanation": "RAG states that force changes motion; more broadly it can change speed or direction.",
                        "marks": 1,
                    }
                ]
            }
        )

    monkeypatch.setattr(
        mock_test_service,
        "search_textbook_content",
        fake_search_textbook_content,
    )
    monkeypatch.setattr(mock_test_service, "ask_llm", fake_ask_llm)
    monkeypatch.setattr(
        mock_test_service,
        "create_generation_variant",
        lambda username="admin": "test_user-2026-06-03-fixed",
    )

    questions = mock_test_service.generate_olympiad_mock_test(
        olympiad="Science Olympiad",
        chapter="Force",
        grade="Grade 9",
        num_questions=1,
        difficulty="Hard",
        username="test_user",
    )

    prompt = captured_prompt["user_prompt"]

    assert len(questions) == 1
    assert captured_prompt["feature"] == "sof_mock_test"
    assert captured_prompt["model"] == mock_test_service.DEFAULT_TEXT_MODEL
    assert "RAG Section: SOF chapter content" in prompt
    assert "RAG Section: SOF chapter exercises" in prompt
    assert "RAG Section: SOF uploaded mock or model test papers" in prompt
    assert "Generation variation seed: test_user-2026-06-03-fixed" in prompt
    assert "Every question must be based on a concept" in prompt
    assert "Explanations must first use the uploaded RAG concept" in prompt
    assert "wider conceptual clarification" in prompt
