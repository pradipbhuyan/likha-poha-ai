"""
rag_book_title_inference.py
─────────────────────────────────────────────────────────────────────────────
Chapter/section title inference for full-book and bulk-book RAG uploads.

Extracted from app/routes/rag.py (previously ~600 lines embedded in a
2,000+ line route file) — this is pure text-processing logic with no routes
and no side effects, used by app/routes/rag_bulk_book_upload.py's
/analyze-book-set, /bulk-book-upload, and /book-set-upload handlers.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from pydantic import BaseModel

from app.services.openai_service import GPT5_TEXT_MODEL, ask_llm


class BulkBookMetadata(BaseModel):
    board: str = "CBSE"
    grade: str
    subject: str
    title: str
    chapter: str = "Uploaded Book Content"


def parse_bulk_book_metadata(metadata_json: str, file_count: int) -> List[BulkBookMetadata]:
    """
    Validate the per-file book metadata supplied by the admin bulk upload UI.

    Each uploaded book must have an explicit grade, subject, and title so the
    resulting RAG documents can be filtered correctly for Class 1-10 students.
    """
    try:
        raw_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Book metadata must be valid JSON.") from exc

    if not isinstance(raw_metadata, list):
        raise ValueError("Book metadata must be a list.")

    if len(raw_metadata) != file_count:
        raise ValueError("Book metadata count must match uploaded file count.")

    metadata = [BulkBookMetadata(**item) for item in raw_metadata]

    for index, item in enumerate(metadata, start=1):
        if not item.grade.strip():
            raise ValueError(f"Book {index} is missing a grade.")
        if not item.subject.strip():
            raise ValueError(f"Book {index} is missing a subject.")
        if not item.title.strip():
            raise ValueError(f"Book {index} is missing a title.")

    return metadata


def parse_book_section_titles(section_titles: str, files: list) -> list[str]:
    """
    Resolve one TOC/chapter label per uploaded book-section file.

    Admins can paste one title per line. Commas are preserved because textbook
    chapters often include comma-separated titles such as "Pressure, Winds,
    Storms, and Cyclones". If a label is missing, readable file names are used
    so a multi-file book can still be indexed safely.
    """
    titles = [
        title.strip()
        for title in section_titles.splitlines()
        if title.strip()
    ]

    resolved_titles = []

    for index, file in enumerate(files):
        fallback_title = (
            Path(file.filename or f"Section {index + 1}").stem
            .replace("_", " ")
            .replace("-", " ")
            .strip()
            or f"Section {index + 1}"
        )
        resolved_titles.append(titles[index] if index < len(titles) else fallback_title)

    return resolved_titles


def readable_title_from_filename(filename: str, index: int) -> str:
    """Convert a raw file name into a readable fallback section title."""
    return (
        Path(filename or f"Section {index + 1}").stem
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        or f"Section {index + 1}"
    )


def clean_pdf_label_text(text: str) -> str:
    """Remove PDF/export artifacts before chapter-label extraction."""
    cleaned = re.sub(r"\b[\w-]+\.indd\b", " ", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:AM|PM)\b", " ", cleaned, flags=re.IGNORECASE)
    # Remove U+25CC (dotted circle) — PyMuPDF/pypdf placeholder for
    # orphaned Devanagari matras from NCERT Hindi PDFs with embedded fonts
    cleaned = cleaned.replace("◌", "")
    # Remove other common Unicode replacement placeholders
    cleaned = cleaned.replace("�", "")
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def contains_devanagari(text: str) -> bool:
    """Return true when text includes Hindi/Devanagari characters."""
    return bool(re.search(r"[ऀ-ॿ]", text or ""))


def normalize_hindi_section_title(prefix: str, number: str, title: str) -> str:
    """Format Hindi chapter labels while preserving the original script."""
    clean_title = clean_pdf_label_text(title).strip(" :-–—।")
    clean_title = re.sub(r"\s+", " ", clean_title)

    if clean_title:
        return f"{prefix} {number}: {clean_title}"

    return f"{prefix} {number}"


def infer_chapter_number_from_filename(filename: str) -> str:
    """
    Infer common textbook chapter numbers from filenames like hecu106.pdf.

    NCERT split PDFs often encode chapter 1 as 101, chapter 6 as 106, etc.
    This is only a fallback when OCR text does not expose a clean heading.
    """
    match = re.search(r"(\d{3})(?=\D*$)", Path(filename or "").stem)

    if not match:
        return ""

    number = int(match.group(1))

    if 101 <= number <= 130:
        return str(number - 100)

    return ""


def normalize_suggested_section_title(title: str, filename: str, preview: str = "") -> str:
    """Keep AI/local labels readable and strip publishing metadata artifacts."""
    cleaned = clean_pdf_label_text(title)
    cleaned = re.sub(r"\s*[:.-]?\s*z\s+why\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[:.-]?\s+why\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[:.-]?\s+probe\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-–—")

    chapter_with_bad_tail = re.match(
        r"^chapter\s+(\d{1,2})\b(?:\s+\d+)?(?:\s+chapter\s+\1\b)?\s*(.*)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if chapter_with_bad_tail:
        chapter_number = chapter_with_bad_tail.group(1)
        # Strip leading colon/space but preserve dashes inside the title
        title_tail = chapter_with_bad_tail.group(2).lstrip(" :").rstrip(" ")

        if title_tail and not re.search(r"\d{1,2}/\d{1,2}/\d{4}|\.indd", title_tail, flags=re.IGNORECASE):
            return f"Chapter {chapter_number}: {title_tail}"

        clean_preview_title = infer_title_from_grade_heading(preview)
        if clean_preview_title:
            return clean_preview_title

        return f"Chapter {chapter_number}"

    if ".indd" in (title or "").lower():
        clean_preview_title = infer_title_from_grade_heading(preview)
        if clean_preview_title:
            return clean_preview_title

    return cleaned or readable_title_from_filename(filename, 0)


def infer_hindi_section_title(extracted_text: str) -> str:
    """Extract Hindi chapter labels without translating them to English."""
    raw_lines = [
        line.strip()
        for line in (extracted_text or "").splitlines()
        if line.strip()
    ]
    lines = []

    for raw_line in raw_lines:
        cleaned_line = clean_pdf_label_text(raw_line).strip(" \t:-–—।")

        if cleaned_line:
            lines.append(cleaned_line)

    for line in lines[:16]:
        if re.search(r"विषय\s*सूची|अनुक्रमणिका|सामग्री", line):
            return "विषय सूची"

    for line in lines[:36]:
        # Pattern 1: "पाठ N: title" or "अध्याय N: title"
        chapter_match = re.match(
            r"^(पाठ|अध्याय)\s*([०-९0-9]+)\s*[:：.\-–—]?\s+(.{2,90})$",
            line,
        )
        if chapter_match:
            return normalize_hindi_section_title(
                chapter_match.group(1),
                chapter_match.group(2),
                chapter_match.group(3),
            )

        # Pattern 2: "title पाठ N" (title followed by chapter keyword + number)
        title_before_chapter = re.match(
            r"^(.{2,90}?)\s+(पाठ|अध्याय)\s*([०-९0-9]+)\b",
            line,
        )
        if title_before_chapter and contains_devanagari(title_before_chapter.group(1)):
            return normalize_hindi_section_title(
                title_before_chapter.group(2),
                title_before_chapter.group(3),
                title_before_chapter.group(1),
            )

        # Pattern 3: "N title" (number followed by title)
        numbered_title = re.match(r"^([०-९0-9]+)\s+(.{2,90})$", line)
        if numbered_title and contains_devanagari(numbered_title.group(2)):
            return normalize_hindi_section_title(
                "पाठ",
                numbered_title.group(1),
                numbered_title.group(2),
            )

        # Pattern 4: "title N" (NCERT ghml style — title then chapter number)
        # e.g., "माँ, कह एक कहानी1" or "माँ, कह एक कहानी 1"
        title_then_number = re.match(
            r"^(.{3,80}?[^\s\d])\s*([0-9]+)\s*$",
            line,
        )
        if title_then_number and contains_devanagari(title_then_number.group(1)):
            title_part = title_then_number.group(1).strip(" :-–—।")
            num_part = title_then_number.group(2)
            # Only treat as chapter title if title has meaningful Hindi content
            if len(title_part) >= 3 and re.search(r"[ऀ-ॿ]{2,}", title_part):
                return normalize_hindi_section_title("पाठ", num_part, title_part)

        # Pattern 5: Standalone Hindi title line (no number) — first clean Hindi line
        # Use as last resort: any line with enough Devanagari and 2+ words
        if (
            contains_devanagari(line)
            and len(line.split()) >= 2
            and len(line) >= 4
            and len(line) <= 80
            and not re.search(r"[A-Za-z]{3,}", line)  # exclude mostly-Latin lines
        ):
            # Only pick up if no better match found yet — defer by continuing loop
            # We will fall through to this as a final fallback below
            pass

    # Fallback: first clean standalone Hindi line in the first 12 lines
    for line in lines[:12]:
        if (
            contains_devanagari(line)
            and len(line.split()) >= 2
            and len(line) >= 4
            and len(line) <= 80
            and not re.search(r"[A-Za-z]{3,}", line)
            and not re.search(r"^\d", line)  # not starting with a number
        ):
            # Verify it looks like a title (not a sentence with full stops mid-way)
            if line.count("।") <= 1:
                return line.strip(" :-–—।")

    return ""


def infer_title_from_grade_heading(extracted_text: str) -> str:
    """
    Extract chapter labels from single-line NCERT PDF text.

    Some PDFs flatten the first page into one long line like:
    "Curiosity Textbook of Science for Grade 8 Pressure, Winds... 6 z Why..."
    This recovers the chapter title before the exercise/opening question text.
    """
    normalized_text = clean_pdf_label_text(extracted_text)
    match = re.search(
        (
            r"\bgrade\s+\d+\s+"
            r"(?P<title>[A-Z][A-Za-z0-9,()'’&/\- ]{4,110}?)"
            r"\s+(?P<number>\d{1,2})\s+"
            r"(?=z\b|why\b|probe\b|chapter\b|let\b|in\b)"
        ),
        normalized_text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    title = match.group("title").strip(" :-–—")
    chapter_number = match.group("number")
    title = re.sub(r"\s+", " ", title)

    if len(title.split()) < 2:
        return ""

    return f"Chapter {chapter_number}: {title}"


def infer_book_section_title(filename: str, extracted_text: str, index: int) -> str:
    """
    Suggest a TOC/chapter label from extracted file text before RAG upload.

    The heuristic intentionally stays simple and predictable: it detects table
    of contents pages and common chapter-heading lines, then falls back to the
    original file name for admin review.
    """
    fallback = readable_title_from_filename(filename, index)
    raw_lines = [
        line.strip()
        for line in (extracted_text or "").splitlines()
        if line.strip()
    ]
    lines = []

    for raw_line in raw_lines:
        if re.search(r"\.indd\b|\d{1,2}/\d{1,2}/\d{4}", raw_line, flags=re.IGNORECASE):
            continue

        cleaned_line = clean_pdf_label_text(raw_line).strip(" \t:-–—")

        if cleaned_line:
            lines.append(cleaned_line)

    for line in lines[:12]:
        lower_line = line.lower()
        if "contents" in lower_line or "table of contents" in lower_line:
            return "Table of Contents"

    # Only call Hindi extraction when the FIRST meaningful lines are primarily Devanagari.
    # Skip it for books like fecu (Curiosity Science) that open with Sanskrit subhashitas
    # but have an English chapter title on the very first line.
    if contains_devanagari(extracted_text):
        first_lines = [l.strip() for l in (extracted_text or "").splitlines() if l.strip()][:5]
        first_text  = " ".join(first_lines[:3])
        deva_chars  = len(re.findall(r"[ऀ-ॿ]", first_text))
        latin_chars = len(re.findall(r"[A-Za-z]", first_text))
        # Only use Hindi heuristic when Devanagari dominates the first 3 lines
        if deva_chars > latin_chars:
            hindi_title = infer_hindi_section_title(extracted_text)
            if hindi_title:
                return hindi_title

    grade_heading_title = infer_title_from_grade_heading(extracted_text)

    if grade_heading_title:
        return grade_heading_title

    for line_index, line in enumerate(lines[:24]):
        words = line.split()
        lower_line = line.lower()

        # ---- NCERT Curiosity Science (fecu) / mixed-case title + digit + Chapter ----
        # Pattern C1: "Title Case Title1Chapter text"
        # e.g. "The Wonderful World of Science1Chapter As human beings..."
        ncert_mixed_c1 = re.match(
            r"^([A-Z][A-Za-z\s,:'&/()\-]{3,80}?[a-zA-Z])\s*(\d{1,2})\s*[Cc]hapter\b",
            line,
        )
        if ncert_mixed_c1:
            return f"Chapter {ncert_mixed_c1.group(2)}: {ncert_mixed_c1.group(1).strip()}"

        # Pattern C2: "TitleImmediatelyDigit content" (NO space before digit — fecu format)
        # e.g. "Diversity in the Living World2 छायामनयसय..."
        # e.g. "Mindful Eating: A Path to a Healthy Body3 Chapter..."
        # Must NOT match "Science 1 In..." (space before digit = not a title heading)
        ncert_mixed_c2 = re.match(
            r"^([A-Z][A-Za-z\s,:'&/()\-]{3,80}?[a-zA-Z])(\d{1,2})\s+[A-Zऀ-ॿ]",
            line,
        )
        if ncert_mixed_c2 and not re.search(
            r"\bchapter\b", ncert_mixed_c2.group(1), re.IGNORECASE
        ):
            return f"Chapter {ncert_mixed_c2.group(2)}: {ncert_mixed_c2.group(1).strip()}"

        # ---- NCERT Ganita Prakash / new-gen series (ALL CAPS) ----
        ncert_caps_a = re.match(
            r"^([A-Z][A-Z\s,''&/:()-]{2,60}?)\s*(\d{1,2})\s+(?:\d+\.\d+|\d{1,2}\s+[A-Z])",
            line,
        )
        if ncert_caps_a:
            return f"Chapter {ncert_caps_a.group(2)}: {ncert_caps_a.group(1).strip().title()}"

        # Pattern B: "TITLE_DIRECTLY_FOLLOWEDBY_DIGIT text"  e.g. "NUMBER PLAY3 Numbers..."
        # Title ends with a capital letter, digit immediately after (no space), then space + text
        ncert_caps_b = re.match(
            r"^([A-Z][A-Z\s,''&/:()-]{2,60}[A-Z])(\d{1,2})\s+[A-Za-z]",
            line,
        )
        if ncert_caps_b:
            return f"Chapter {ncert_caps_b.group(2)}: {ncert_caps_b.group(1).strip().title()}"

        # ---- Chapter N: Title patterns ----
        # Handles both "chapter N" (with space) and "CHAPTERN" (no space — NCERT gees style)
        title_before_chapter = re.match(
            r"^(.{4,90}?)\s+chapter\s*(\d{1,2})\b",
            line,
            flags=re.IGNORECASE,
        )
        if title_before_chapter:
            title = title_before_chapter.group(1).strip(" :-–—")
            chapter_number = title_before_chapter.group(2)
            return f"Chapter {chapter_number}: {title}"

        chapter_with_title = re.match(
            r"^chapter\s*(\d{1,2})\s*[:.-]?\s+(.{4,90})",
            line,
            flags=re.IGNORECASE,
        )
        if chapter_with_title:
            chapter_number = chapter_with_title.group(1)
            title = chapter_with_title.group(2).strip(" :-–—")
            return f"Chapter {chapter_number}: {title}"

        # ---- Unit N: Title patterns (textbooks that use Units instead of Chapters) ----
        title_before_unit = re.match(
            r"^(.{4,90}?)\s+unit\s+(\d{1,2})\b",
            line,
            flags=re.IGNORECASE,
        )
        if title_before_unit:
            title = title_before_unit.group(1).strip(" :-–—")
            unit_number = title_before_unit.group(2)
            return f"Unit {unit_number}: {title}"

        unit_with_title = re.match(
            r"^unit\s+(\d{1,2})\s*[:.-]?\s+(.{4,90})",
            line,
            flags=re.IGNORECASE,
        )
        if unit_with_title:
            unit_number = unit_with_title.group(1)
            title = unit_with_title.group(2).strip(" :-–—")
            return f"Unit {unit_number}: {title}"

        # ---- Bare "Chapter N" or "Unit N" — peek at the next line for the title ----
        # Handle both "Chapter 1" (with space) and "CHAPTER1" (without space)
        chapter_bare = re.match(r"^chapter\s*(\d{1,2})\s*$", line, flags=re.IGNORECASE)
        if chapter_bare and len(words) <= 2:
            chapter_number = chapter_bare.group(1)
            next_lines = lines[line_index + 1 : line_index + 3]
            for next_line in next_lines:
                next_clean = next_line.strip(" :-–—")
                if (
                    2 <= len(next_clean.split()) <= 12
                    and not re.search(
                        r"^\d+$|let us|activities|listen|read|watch|look|do these",
                        next_clean,
                        flags=re.IGNORECASE,
                    )
                ):
                    return f"Chapter {chapter_number}: {next_clean}"
            return f"Chapter {chapter_number}"

        unit_bare = re.match(r"^unit\s*(\d{1,2})\s*$", line, flags=re.IGNORECASE)
        if unit_bare and len(words) <= 2:
            unit_number = unit_bare.group(1)
            next_lines = lines[line_index + 1 : line_index + 3]
            for next_line in next_lines:
                next_clean = next_line.strip(" :-–—")
                if (
                    2 <= len(next_clean.split()) <= 12
                    and not re.search(
                        r"^\d+$|let us|activities|listen|read|watch|look|do these",
                        next_clean,
                        flags=re.IGNORECASE,
                    )
                ):
                    return f"Unit {unit_number}: {next_clean}"
            return f"Unit {unit_number}"

    chapter_number = infer_chapter_number_from_filename(filename)

    if chapter_number:
        return f"Chapter {chapter_number}"

    return fallback


def is_weak_section_title(title: str, filename: str) -> bool:
    """Identify labels that need AI help before admin confirmation."""
    normalized_title = (title or "").strip().lower()
    filename_title = readable_title_from_filename(filename, 0).strip().lower()

    return (
        not normalized_title
        or normalized_title == "chapter"
        or normalized_title == "unit"
        # Bare "Chapter N" or "Unit N" — AI can extract actual title from preview
        or bool(re.fullmatch(r"chapter\s*\d{1,2}", normalized_title))
        or bool(re.fullmatch(r"unit\s*\d{1,2}", normalized_title))
        or normalized_title == filename_title
        or bool(re.fullmatch(r"[a-z]{2,}\d+", normalized_title))
    )


def parse_ai_section_labels(raw_response: str) -> list[dict]:
    """Parse AI-suggested section labels from JSON, tolerating code fences."""
    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    parsed = json.loads(cleaned)

    if isinstance(parsed, dict):
        return parsed.get("sections", [])

    if isinstance(parsed, list):
        return parsed

    return []


def improve_book_section_labels_with_ai(sections: list[dict]) -> list[dict]:
    """
    Use a lightweight AI pass when local chapter-label heuristics are weak.

    The AI receives only short previews and returns one label per filename; the
    admin still reviews and confirms before anything is stored in RAG.
    """
    weak_sections = [
        section for section in sections
        if is_weak_section_title(
            section.get("suggested_title", ""),
            section.get("filename", ""),
        )
    ]

    if not weak_sections:
        return sections

    section_payload = [
        {
            "filename": section.get("filename", ""),
            "current_label": normalize_suggested_section_title(
                section.get("suggested_title", ""),
                section.get("filename", ""),
                section.get("preview", ""),
            ),
            "preview": clean_pdf_label_text(section.get("preview", ""))[:700],
        }
        for section in sections
    ]

    system_prompt = """
You label school textbook PDF files before RAG upload.
Return only valid JSON. Do not explain.
"""

    user_prompt = f"""
For each file, infer the clearest chapter/section label from filename and preview.

Rules:
- Prefer format "Chapter N: Title" when a chapter number is visible.
- If the preview is in Hindi/Devanagari, preserve Hindi script and prefer "पाठ N: शीर्षक" or "अध्याय N: शीर्षक".
- Do not translate Indian-language chapter titles to English.
- Use "Table of Contents" for contents pages.
- Do not return raw filenames like iesc101.
- Keep labels short and readable for an admin to confirm.
- Return exactly this JSON shape:
{{"sections":[{{"filename":"","suggested_title":""}}]}}

Files:
{json.dumps(section_payload, ensure_ascii=False)}
"""

    try:
        ai_response = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            username="admin",
            feature="rag_book_label_analysis",
            model=GPT5_TEXT_MODEL,
        )
        ai_sections = parse_ai_section_labels(ai_response)
        ai_title_by_filename = {
            item.get("filename"): item.get("suggested_title", "").strip()
            for item in ai_sections
            if isinstance(item, dict)
        }
    except Exception:
        return sections

    improved_sections = []

    for section in sections:
        ai_title = ai_title_by_filename.get(section.get("filename", ""))
        if ai_title:
            section = {
                **section,
                "suggested_title": normalize_suggested_section_title(
                    ai_title,
                    section.get("filename", ""),
                    section.get("preview", ""),
                ),
            }
        else:
            section = {
                **section,
                "suggested_title": normalize_suggested_section_title(
                    section.get("suggested_title", ""),
                    section.get("filename", ""),
                    section.get("preview", ""),
                ),
            }
        improved_sections.append(section)

    return improved_sections
