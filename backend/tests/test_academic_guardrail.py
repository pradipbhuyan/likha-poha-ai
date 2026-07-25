"""
test_academic_guardrail.py
──────────────────────────
Unit tests for the academic guardrail service.

Verifies that:
  - Political / current-affairs questions are blocked.
  - CBSE curriculum questions (civics, history, science) pass through.
  - The allow-list takes precedence over the block-list.
"""

import pytest

from app.services.academic_guardrail_service import (
    is_non_academic_question,
    build_non_academic_response,
    NON_ACADEMIC_SOURCE_TYPE,
)


# ── Questions that SHOULD be blocked ─────────────────────────────────────────

BLOCKED_QUESTIONS = [
    "who is president of USA",
    "Who is the President of America?",
    "who is the current president of india",
    "who is pm of india",
    "Who is the Chief Minister of Assam?",
    "who is cm of assam",
    "CM of Gujarat",
    "who won the IPL",
    "ipl winner 2024",
    "who won the election",
    "election results today",
    "latest news india",
    "today's news",
    "breaking news",
    "what is the current government",
    "score of the match",
    "live cricket score",
    "ipl score today",
    "nifty today",
    "sensex today",
    "bitcoin price",
    "stock market today",
    "who is the richest person in the world",
    "Who is the ruling party in India?",
    "who is BJp president",
    "who won world cup",
    "current president of usa",
    # Sports team leadership — bug ac003dfb-b926-4b52-818b-84ef5626b71a
    "who is the captain of the Indian cricket team",
    "who is captain of Indian cricket team",
    "who is the current captain of the Indian cricket team",
    "who is the vice captain of the Indian cricket team",
    "who is the coach of the Indian cricket team",
    "who is the captain of India",
    "india's cricket captain",
    "current cricket captain",
]

# ── Questions that SHOULD pass through (academic / CBSE curriculum) ───────────

ALLOWED_QUESTIONS = [
    # History — not current affairs
    "Who was the first President of India?",
    "who was the former prime minister before Modi",
    "explain the role of the President of India",
    "what are the powers of the Prime Minister",
    "describe the functions of the governor",
    # CBSE Civics / Political Science
    "what is democracy",
    "explain federalism",
    "what is the constitution of India",
    "what are fundamental rights",
    "explain the preamble of the Indian constitution",
    "what is separation of powers",
    # History — Indian freedom fighters
    "who was Mahatma Gandhi",
    "explain the role of Nehru in independence",
    "who was Ambedkar",
    "explain Bhagat Singh's contribution",
    # Science / invention questions
    "who invented the telephone",
    "who discovered gravity",
    "who wrote the Ramcharitmanas",
    "who founded the Indian National Congress",
    # Normal science / maths doubts
    "what is photosynthesis",
    "explain Newton's second law",
    "what is the quadratic formula",
    "how do plants make food",
    "explain the water cycle",
    "what is the difference between speed and velocity",
]


@pytest.mark.parametrize("question", BLOCKED_QUESTIONS)
def test_blocked_non_academic_questions(question):
    """Non-academic questions must be detected as non-academic."""
    assert is_non_academic_question(question), (
        f"Expected '{question}' to be blocked as non-academic."
    )


@pytest.mark.parametrize("question", ALLOWED_QUESTIONS)
def test_allowed_academic_questions(question):
    """CBSE curriculum questions must NOT be blocked."""
    assert not is_non_academic_question(question), (
        f"Expected '{question}' to pass through as academic."
    )


def test_build_non_academic_response_structure():
    """The guardrail response must carry the correct source_type and a non-empty answer."""
    result = build_non_academic_response()
    assert result["source_type"] == NON_ACADEMIC_SOURCE_TYPE
    assert "I'm focused on your studies" in result["answer"]
    assert result["sources"] == []
    assert result["mentor_suggestions"] == []


def test_empty_question_is_not_blocked():
    """Empty input must never trigger the guardrail."""
    assert not is_non_academic_question("")
    assert not is_non_academic_question(None)
    assert not is_non_academic_question("   ")
