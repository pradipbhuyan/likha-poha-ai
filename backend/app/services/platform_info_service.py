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
    text directly so students, parents, and teachers receive the same facts.
    """
    text = str(question or "").lower()

    if "akshita" in text or "daughter" in text:
        answer = (
            "Likha Poha AI was initially developed by Pradip Bhuyan to help his "
            "daughter, Akshita, with her studies. That personal need shaped the "
            "platform into a patient AI learning companion for CBSE and SOF "
            "Olympiad preparation."
        )
    elif "founder" in text or "who created" in text or "who made" in text:
        answer = (
            "Likha Poha AI was created by Pradip Bhuyan. It began as a way to "
            "help his daughter Akshita study with step-by-step explanations, "
            "doubt solving, practice, and progress visibility."
        )
    else:
        answer = (
            "Likha Poha AI is an independent AI learning companion created by "
            "Pradip Bhuyan for Class 1 to Class 10 students. It supports CBSE "
            "learning and SOF Science, Maths, and English Olympiad preparation "
            "using lessons, doubt solving, mock tests, uploaded textbook or "
            "workbook RAG content, and parent/teacher progress tracking. It was "
            "initially developed to help the founder's daughter, Akshita, with "
            "her studies."
        )

    answer += (
        "\n\nIt is not an official CBSE or SOF product, and it is not meant to "
        "replace teachers or parents. It is designed to support revision, "
        "practice, confidence building, and personalized learning."
    )

    return {
        "answer": answer,
        "source_type": "PLATFORM_RAG",
        "sources": [build_platform_source()],
        "mentor_suggestions": [],
    }
