from difflib import get_close_matches
import re

from app.data.syllabus import SOF_9


SOF_SUBJECT_CODES = {
    "Science Olympiad": "ISO",
    "Maths Olympiad": "IMO",
    "English Olympiad": "IEO",
}

SOF_SUBJECT_ALIASES = {
    "science": "Science Olympiad",
    "science olympiad": "Science Olympiad",
    "national science olympiad": "Science Olympiad",
    "iso": "Science Olympiad",
    "sof iso": "Science Olympiad",
    "sof-iso": "Science Olympiad",
    "nso": "Science Olympiad",
    "sof nso": "Science Olympiad",
    "sof national science olympiad": "Science Olympiad",
    "math": "Maths Olympiad",
    "maths": "Maths Olympiad",
    "mathematics": "Maths Olympiad",
    "international mathematics olympiad": "Maths Olympiad",
    "maths olympiad": "Maths Olympiad",
    "mathematics olympiad": "Maths Olympiad",
    "imo": "Maths Olympiad",
    "sof imo": "Maths Olympiad",
    "sof-imo": "Maths Olympiad",
    "sof international mathematics olympiad": "Maths Olympiad",
    "english": "English Olympiad",
    "english olympiad": "English Olympiad",
    "international english olympiad": "English Olympiad",
    "ieo": "English Olympiad",
    "sof ieo": "English Olympiad",
    "sof-ieo": "English Olympiad",
    "sof international english olympiad": "English Olympiad",
}


def normalize_lookup_text(value):
    text = str(value or "").strip().lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("&", " and ")
    text = re.sub(r"sof\s*-\s*", "sof-", text)
    text = re.sub(r"word\s+power\s*-\s*", "word power-", text)
    text = re.sub(r"paper\s*-\s*", "paper-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_sof_subjects():
    return list(SOF_9.keys())


def canonical_sof_subject(value, text_hint=""):
    candidates = [value, text_hint]

    for candidate in candidates:
        normalized = normalize_lookup_text(candidate)
        if not normalized:
            continue

        if normalized in SOF_SUBJECT_ALIASES:
            return SOF_SUBJECT_ALIASES[normalized]

        for alias, subject in SOF_SUBJECT_ALIASES.items():
            if alias in normalized:
                return subject

    subject_names = {
        normalize_lookup_text(subject): subject
        for subject in get_sof_subjects()
    }

    matches = get_close_matches(
        normalize_lookup_text(value),
        subject_names.keys(),
        n=1,
        cutoff=0.65,
    )
    if matches:
        return subject_names[matches[0]]

    return None


def canonical_sof_chapter(subject, value, text_hint=""):
    if subject not in SOF_9:
        return None

    chapters = SOF_9[subject]
    chapter_map = {
        normalize_lookup_text(chapter): chapter
        for chapter in chapters
    }

    for candidate in [value, text_hint]:
        normalized = normalize_lookup_text(candidate)
        if not normalized:
            continue

        if normalized in chapter_map:
            return chapter_map[normalized]

        for normalized_chapter, chapter in chapter_map.items():
            if normalized_chapter in normalized:
                return chapter

        matches = get_close_matches(
            normalized,
            chapter_map.keys(),
            n=1,
            cutoff=0.72,
        )
        if matches:
            return chapter_map[matches[0]]

    return None


def is_sof_model_paper(chapter):
    return "model test paper" in normalize_lookup_text(chapter)


def is_sof_exam_paper(chapter):
    normalized = normalize_lookup_text(chapter)
    return is_sof_model_paper(chapter) or "olympiad 2025" in normalized


def is_sof_support_section(chapter):
    normalized = normalize_lookup_text(chapter)
    return normalized in [
        "hints and explanations",
        "answer keys",
    ]


def get_sof_exam_paper_chapters(subject):
    return [
        chapter
        for chapter in SOF_9.get(subject, [])
        if is_sof_exam_paper(chapter)
    ]


def get_sof_support_chapters(subject):
    return [
        chapter
        for chapter in SOF_9.get(subject, [])
        if is_sof_support_section(chapter)
    ]


def infer_sof_content_type(chapter, text):
    normalized_text = normalize_lookup_text(text)

    if is_sof_exam_paper(chapter):
        return "Mock Test Paper"

    if is_sof_support_section(chapter):
        return "Answer Explanations"

    exercise_markers = [
        "exercise",
        "worksheet",
        "practice questions",
        "question bank",
        "sample paper",
        "mock test",
        "answers",
    ]
    if any(marker in normalized_text for marker in exercise_markers):
        return "Exercise"

    return "Chapter Content"


def build_sof_document_title(subject, chapter, content_type):
    if is_sof_exam_paper(chapter) or is_sof_support_section(chapter):
        return chapter

    subject_code = SOF_SUBJECT_CODES.get(subject, "SOF")
    return f"SOF-{subject_code} Grade 9 - {chapter} - {content_type}"


def build_sof_catalog_prompt():
    lines = ["Canonical Grade 9 SOF TOC. Use these exact subject and chapter names:"]

    for subject, chapters in SOF_9.items():
        lines.append(f"{subject}:")
        for index, chapter in enumerate(chapters, start=1):
            lines.append(f"{index}. {chapter}")

    return "\n".join(lines)


def normalize_sof_group(group, fallback_grade="Grade 9"):
    if not isinstance(group, dict):
        group = {}

    combined_text = str(group.get("combined_text") or "").strip()
    subject_hint = " ".join(
        [
            str(group.get("subject") or ""),
            str(group.get("title") or ""),
            str(group.get("chapter") or ""),
            combined_text[:1200],
        ]
    )
    subject = canonical_sof_subject(group.get("subject"), subject_hint)

    if not subject:
        return {
            **group,
            "grade": group.get("grade") or fallback_grade,
            "combined_text": combined_text,
            "normalization_warning": "Could not match SOF subject to canonical TOC.",
        }

    chapter_hint = " ".join(
        [
            str(group.get("chapter") or ""),
            str(group.get("title") or ""),
            combined_text[:1600],
        ]
    )
    chapter = canonical_sof_chapter(subject, group.get("chapter"), chapter_hint)

    if not chapter:
        return {
            **group,
            "grade": group.get("grade") or fallback_grade,
            "subject": subject,
            "combined_text": combined_text,
            "normalization_warning": "Could not match SOF chapter to canonical TOC.",
        }

    content_type = infer_sof_content_type(chapter, combined_text)

    return {
        **group,
        "grade": group.get("grade") or fallback_grade,
        "subject": subject,
        "chapter": chapter,
        "title": build_sof_document_title(subject, chapter, content_type),
        "combined_text": combined_text,
        "content_type": content_type,
    }
