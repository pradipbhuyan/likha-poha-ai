from app.services.platform_info_service import (
    answer_platform_info,
    is_platform_info_question,
)


def test_platform_info_question_detection():
    """Founder and app questions should route to controlled platform knowledge."""
    assert is_platform_info_question("Who founded Likha Poha AI?")
    assert is_platform_info_question("Why was this app created?")
    assert is_platform_info_question("Tell me about Akshita")
    assert not is_platform_info_question("What is rational number?")


def test_platform_info_answer_uses_founder_story():
    """The curated answer should use the approved platform story from platform_info.py.
    Personal names must not appear in the answer — the story is anonymous.
    """
    result = answer_platform_info("Who created Likha Poha AI?")

    assert result["source_type"] == "PLATFORM_RAG"
    # Personal names must NOT appear — privacy requirement
    assert "Pradip Bhuyan" not in result["answer"]
    assert "Akshita" not in result["answer"]
    # Anonymous origin story keywords must be present
    assert "parent-engineer" in result["answer"] or "Bangalore" in result["answer"]
    # Must identify as independent (not official CBSE)
    assert "not an official CBSE product" in result["answer"]
    assert result["sources"][0]["document"]["title"] == "Likha Poha AI Founder Story"
