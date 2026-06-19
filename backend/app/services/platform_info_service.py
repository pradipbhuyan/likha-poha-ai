from app.data.platform_info import (
    LIKHA_POHA_FOUNDER_STORY,
    LIKHA_POHA_FOUNDER_STORY_TITLE,
    LIKHA_POHA_PLATFORM_CHAPTER,
    LIKHA_POHA_PLATFORM_GRADE,
    LIKHA_POHA_PLATFORM_SUBJECT,
)


PLATFORM_QUERY_TERMS = [
    "likha poha",
    "likhapoha",
    "this app",
    "this platform",
    "your platform",
    "who made",
    "who created",
    "who founded",
    "founder",
    "akshita",
    "pradip",
    "company",
    "mission",
    "why was it created",
]


def is_platform_info_question(question: str) -> bool:
    """
    Detect questions about Likha Poha AI itself.

    These should use controlled platform knowledge instead of general LLM
    knowledge, because brand/founder details must stay accurate.
    """
    text = str(question or "").lower()

    return any(term in text for term in PLATFORM_QUERY_TERMS)


def build_platform_source():
    """Return source metadata shaped like normal RAG results for the frontend."""
    return {
        "document": {
            "title": LIKHA_POHA_FOUNDER_STORY_TITLE,
            "grade": LIKHA_POHA_PLATFORM_GRADE,
            "subject": LIKHA_POHA_PLATFORM_SUBJECT,
            "chapter": LIKHA_POHA_PLATFORM_CHAPTER,
        },
        "chunk_text": LIKHA_POHA_FOUNDER_STORY,
        "similarity": 1.0,
    }


def answer_platform_info(question: str):
    """
    Answer app/founder questions from curated platform content.

    The answer intentionally does not call the LLM. It uses the approved story
    text from platform_info.py so all responses are consistent and controllable.
    To update what the AI says about LikhaPoha, edit platform_info.py only.
    """
    # Always use the canonical story from platform_info.py — never hardcode here.
    answer = LIKHA_POHA_FOUNDER_STORY

    return {
        "answer": answer,
        "source_type": "PLATFORM_RAG",
        "sources": [build_platform_source()],
        "mentor_suggestions": [],
    }
