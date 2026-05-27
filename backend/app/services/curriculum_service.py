import re

from app.services.rag_service import search_textbook_content


def extract_section_headings(text: str):
    headings = []

    for line in text.split("\n"):
        cleaned = line.strip()

        if re.match(r"^\d+(\.\d+)*\s+.+", cleaned):
            headings.append(cleaned)

    return headings


def build_chapter_outline(
    grade: str,
    subject: str,
    chapter: str,
):
    rag_results = search_textbook_content(
        query=f"{chapter} full chapter headings sections activities summary questions",
        grade=grade,
        subject=subject,
        chapter=chapter,
        match_count=25,
    )

    chapter_text = "\n\n".join(
        item.get("chunk_text", "") for item in rag_results
    )

    headings = extract_section_headings(chapter_text)

    if not headings:
        headings = [
            "Introduction",
            "Core concepts",
            "Examples and activities",
            "Applications",
            "Revision and practice",
        ]

    return {
        "chapter": chapter,
        "headings": headings,
        "context": chapter_text[:12000],
        "sources": rag_results,
    }


def format_chapter_outline(outline: dict) -> str:
    headings = outline.get("headings", [])

    lines = [
        f"Textbook chapter outline for: {outline.get('chapter')}",
        "",
        "Major sections detected:",
    ]

    for index, heading in enumerate(headings, start=1):
        lines.append(f"{index}. {heading}")

    return "\n".join(lines)