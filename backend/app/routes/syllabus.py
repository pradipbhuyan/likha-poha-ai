from copy import deepcopy
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.data.syllabus import SYLLABUS, LESSON_STEPS
from app.services.auth_service import admin_client, require_admin
from app.services.board_service import normalize_board
from app.services.supabase_client import supabase

router = APIRouter()


UPLOAD_PLACEHOLDER_CHAPTERS = {
    "Uploaded Book Content",
    "Uploaded SOF Chapter Content",
    "Uploaded SOF Exercises",
    "Uploaded SOF Model Test Papers",
    "Uploaded SOF Answer Keys and Explanations",
}


def is_uploaded_placeholder(chapter):
    """Return whether a syllabus chapter is only a pre-upload placeholder."""
    return chapter in UPLOAD_PLACEHOLDER_CHAPTERS


def roman_to_int(value):
    """Convert small roman numerals used in book-part labels into integers."""
    roman_values = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
    }

    return roman_values.get(str(value or "").upper(), 0)


def extract_part_number(text):
    """Find a book part marker from labels like Part II or Book 2."""
    normalized = str(text or "")

    roman_match = re.search(r"\bpart\s*[-:]?\s*(I{1,3}|IV|V)\b", normalized, re.I)
    if roman_match:
        return roman_to_int(roman_match.group(1))

    numeric_match = re.search(r"\b(?:part|book)\s*[-:]?\s*(\d{1,2})\b", normalized, re.I)
    if numeric_match:
        return int(numeric_match.group(1))

    return 1


def format_part_label(part_number):
    """Return the user-facing label for a textbook part number."""
    return f"Part {part_number}"


def extract_chapter_number(chapter):
    """Find the chapter number from labels such as Chapter 7: Fractions."""
    match = re.search(r"\bchapter\s*(\d{1,3})\b", str(chapter or ""), re.I)

    return int(match.group(1)) if match else None


def strip_part_prefix(chapter):
    """Remove a display-only part prefix from a chapter label."""
    return re.sub(
        r"^\s*part\s*\d+\s*[-:]\s*",
        "",
        str(chapter or ""),
        flags=re.IGNORECASE,
    ).strip()


def create_part_display_label(chapter, part_number, use_part_prefix):
    """
    Add a display-only book-part prefix when one subject has multiple books.

    The stored RAG document chapter remains unchanged; this label is for
    student/admin dropdown clarity.
    """
    chapter = str(chapter or "").strip()

    if not use_part_prefix or not chapter:
        return chapter

    normalized = chapter.lower()
    if re.match(r"^part\s*\d+\s*[-:]", normalized):
        return chapter

    front_matter_match = re.match(
        r"^front matter\s*(?:\((?:part\s*)?(?:i{1,3}|iv|v|\d+)\))?$",
        normalized,
        flags=re.IGNORECASE,
    )

    if front_matter_match:
        return f"{format_part_label(part_number)} - Front Matter"

    return f"{format_part_label(part_number)} - {chapter}"


def uploaded_chapter_sort_key(item):
    """
    Sort uploaded RAG chapters for student dropdowns.

    Confirmed chapter text is preserved, but the list is presented as a book:
    front matter first, then Chapter 1..N, grouped by Part I/II when present.
    """
    chapter = item["chapter"]
    title = item.get("title") or ""
    combined = f"{title} {chapter}"
    normalized = chapter.lower()
    part_number = extract_part_number(combined)
    chapter_number = extract_chapter_number(chapter)

    if any(token in normalized for token in ["front matter", "table of contents", "toc"]):
        section_rank = 0
        chapter_rank = 0
    elif chapter_number is not None:
        section_rank = 1
        chapter_rank = chapter_number
    else:
        section_rank = 2
        chapter_rank = 999

    return (
        part_number,
        section_rank,
        chapter_rank,
        chapter.lower(),
    )


def normalize_chapter_lookup(chapter):
    """Normalize chapter labels for duplicate detection without changing display text."""
    return re.sub(r"\s+", " ", str(chapter or "").strip()).casefold()


def normalize_rag_chapter_lookup(chapter):
    """Normalize display labels to the stored RAG chapter label for matching."""
    return re.sub(r"\s+", " ", strip_part_prefix(chapter).strip()).casefold()


def sort_uploaded_chapters(existing_chapters, uploaded_items):
    """Merge and sort uploaded chapters, hiding placeholders once real uploads exist."""
    static_chapters = [
        chapter
        for chapter in existing_chapters
        if not is_uploaded_placeholder(chapter)
    ]
    seen = {
        normalize_chapter_lookup(chapter)
        for chapter in static_chapters
    }
    sorted_uploaded = []
    part_numbers = {
        extract_part_number(f"{item.get('title') or ''} {item.get('chapter') or ''}")
        for item in uploaded_items
    }
    use_part_prefix = len(part_numbers) > 1

    for item in sorted(uploaded_items, key=uploaded_chapter_sort_key):
        chapter = item["chapter"].strip()
        part_number = extract_part_number(f"{item.get('title') or ''} {chapter}")
        display_chapter = create_part_display_label(
            chapter,
            part_number,
            use_part_prefix,
        )
        lookup_key = normalize_chapter_lookup(display_chapter)

        if not display_chapter or lookup_key in seen:
            continue

        sorted_uploaded.append(display_chapter)
        seen.add(lookup_key)

    if sorted_uploaded:
        return static_chapters + sorted_uploaded

    return existing_chapters


class SyllabusChapterOverrideItem(BaseModel):
    """One editable dropdown option from the admin syllabus-review page."""

    chapter: str
    original_chapter: str | None = None


class SyllabusChapterOverrideRequest(BaseModel):
    """Payload for saving one grade/mode/subject dropdown review."""

    grade: str
    mode: str
    subject: str
    items: list[SyllabusChapterOverrideItem]


class SyllabusSubjectOverrideRequest(BaseModel):
    """Payload for saving the visible subject list for one grade and mode."""

    grade: str
    mode: str
    subjects: list[str]


def clean_chapter_list(chapters):
    """Normalize an admin-edited chapter list while preserving display labels."""
    cleaned = []
    seen = set()

    for chapter in chapters:
        label = str(chapter or "").strip()
        lookup_key = normalize_chapter_lookup(label)

        if not label or is_uploaded_placeholder(label) or lookup_key in seen:
            continue

        cleaned.append(label)
        seen.add(lookup_key)

    return cleaned


def clean_subject_list(subjects):
    """Normalize an admin-edited subject list while preserving display labels."""
    cleaned = []
    seen = set()

    for subject in subjects:
        label = str(subject or "").strip()
        lookup_key = normalize_chapter_lookup(label)

        if not label or lookup_key in seen:
            continue

        cleaned.append(label)
        seen.add(lookup_key)

    return cleaned


def fetch_syllabus_overrides():
    """Load persisted admin-approved dropdown overrides, if the table exists."""
    try:
        response = (
            supabase
            .table("syllabus_chapter_overrides")
            .select("grade,mode,subject,chapters,updated_at")
            .execute()
        )
    except Exception:
        return {}

    overrides = {}

    for row in response.data or []:
        grade = row.get("grade")
        mode = row.get("mode")
        subject = row.get("subject")
        chapters = clean_chapter_list(row.get("chapters") or [])

        if grade and mode and subject and chapters:
            overrides[(grade, mode, subject)] = {
                "chapters": chapters,
                "updated_at": row.get("updated_at"),
            }

    return overrides


def fetch_subject_overrides():
    """Load persisted admin-approved subject lists, if the table exists."""
    try:
        response = (
            supabase
            .table("syllabus_subject_overrides")
            .select("grade,mode,subjects,updated_at")
            .execute()
        )
    except Exception:
        return {}

    overrides = {}

    for row in response.data or []:
        grade = row.get("grade")
        mode = row.get("mode")
        subjects = clean_subject_list(row.get("subjects") or [])

        if grade and mode and subjects:
            overrides[(grade, mode)] = {
                "subjects": subjects,
                "updated_at": row.get("updated_at"),
            }

    return overrides


def apply_subject_overrides(merged, subject_overrides):
    """Replace visible subject order/list for a grade and mode."""
    for (grade, mode), override in subject_overrides.items():
        subjects = override.get("subjects") or []

        if not subjects:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}, "SOF": {}})
        mode_data = grade_data.setdefault(mode, {})
        reviewed_mode_data = {}

        for subject in subjects:
            reviewed_mode_data[subject] = mode_data.get(
                subject,
                ["Uploaded Book Content"] if mode == "CBSE" else ["Uploaded SOF Chapter Content"],
            )

        grade_data[mode] = reviewed_mode_data

    return merged


def fetch_rag_chapter_counts():
    """Count live RAG documents by grade/mode/subject/chapter label."""
    try:
        response = (
            supabase
            .table("rag_documents")
            .select("grade,subject,chapter,board")
            .execute()
        )
    except Exception:
        try:
            response = (
                supabase
                .table("rag_documents")
                .select("grade,subject,chapter")
                .execute()
            )
        except Exception:
            return {}

    counts = {}

    for document in response.data or []:
        grade = document.get("grade")
        subject = document.get("subject")
        chapter = document.get("chapter")

        if not grade or not subject or not chapter:
            continue

        mode = "SOF" if "Olympiad" in subject else normalize_board(document.get("board"))
        key = (
            grade,
            mode,
            subject,
            normalize_rag_chapter_lookup(chapter),
        )
        counts[key] = counts.get(key, 0) + 1

    return counts


def build_chapter_content_status(syllabus_tree, rag_counts):
    """Report whether each effective dropdown option has matching RAG content."""
    status = []

    for grade, grade_data in (syllabus_tree or {}).items():
        for mode, mode_data in (grade_data or {}).items():
            for subject, chapters in (mode_data or {}).items():
                for chapter in chapters:
                    document_count = rag_counts.get((
                        grade,
                        mode,
                        subject,
                        normalize_rag_chapter_lookup(chapter),
                    ), 0)
                    status.append({
                        "grade": grade,
                        "mode": mode,
                        "subject": subject,
                        "chapter": chapter,
                        "document_count": document_count,
                        "has_content": document_count > 0,
                    })

    return status


def merge_reviewed_and_live_chapters(reviewed_chapters, live_chapters):
    """
    Keep reviewed dropdown order while preserving newly uploaded live chapters.

    Admin reviews are treated as curated ordering/renames, not as a permanent
    blocklist. If content is deleted and later reuploaded, the live RAG labels
    should reappear even when an older override exists.
    """
    live_by_lookup = {}

    for chapter in live_chapters or []:
        label = str(chapter or "").strip()

        if not label or is_uploaded_placeholder(label):
            continue

        live_by_lookup.setdefault(normalize_rag_chapter_lookup(label), []).append(label)

    merged_chapters = []
    used_live_labels = set()

    for chapter in clean_chapter_list(reviewed_chapters):
        live_matches = live_by_lookup.get(normalize_rag_chapter_lookup(chapter), [])
        upgraded_label = live_matches[0] if live_matches else chapter

        merged_chapters.append(upgraded_label)
        used_live_labels.add(normalize_chapter_lookup(upgraded_label))

    seen = {
        normalize_chapter_lookup(chapter)
        for chapter in merged_chapters
    }

    for chapter in live_chapters or []:
        label = str(chapter or "").strip()
        lookup_key = normalize_chapter_lookup(label)

        if (
            not label
            or is_uploaded_placeholder(label)
            or lookup_key in seen
            or lookup_key in used_live_labels
        ):
            continue

        merged_chapters.append(label)
        seen.add(lookup_key)

    return merged_chapters


def apply_syllabus_overrides(merged, overrides):
    """Apply admin-reviewed dropdowns as the student-facing source of truth."""
    for (grade, mode, subject), override in overrides.items():
        chapters = clean_chapter_list(override.get("chapters") or [])

        if not chapters:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}, "SOF": {}})
        mode_data = grade_data.setdefault(mode, {})
        mode_data[subject] = chapters

    return merged


def merge_uploaded_rag_chapters(syllabus):
    """
    Add uploaded RAG document chapters to the static syllabus tree.

    This lets Class 1-10 books become selectable after bulk upload without a code
    change for every new book or chapter. Failures are ignored so syllabus loading
    still works if Supabase is temporarily unavailable.
    """
    merged = deepcopy(syllabus)

    try:
        response = (
            supabase
            .table("rag_documents")
            .select("grade,subject,chapter,title,created_at,board")
            .execute()
        )
    except Exception:
        try:
            response = (
                supabase
                .table("rag_documents")
                .select("grade,subject,chapter,title,created_at")
                .execute()
            )
        except Exception:
            return merged

    uploaded_by_subject = {}

    for document in response.data or []:
        grade = document.get("grade")
        subject = document.get("subject")
        chapter = document.get("chapter")

        if not grade or not subject or not chapter:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode = "SOF" if "Olympiad" in subject else normalize_board(document.get("board"))
        mode_data = grade_data.setdefault(mode, {})
        chapters = mode_data.setdefault(subject, [])

        key = (grade, mode, subject)
        uploaded_by_subject.setdefault(key, []).append({
            "chapter": chapter,
            "title": document.get("title") or "",
            "created_at": document.get("created_at") or "",
        })

    for (grade, mode, subject), uploaded_items in uploaded_by_subject.items():
        chapters = merged[grade][mode][subject]
        merged[grade][mode][subject] = sort_uploaded_chapters(
            chapters,
            uploaded_items,
        )

    merged = apply_syllabus_overrides(merged, fetch_syllabus_overrides())

    return apply_subject_overrides(merged, fetch_subject_overrides())


def rename_rag_chapter_labels(grade, subject, items):
    """
    Keep RAG metadata aligned when admin renames a dropdown chapter label.

    The student pages send the selected chapter back into RAG retrieval, so a
    visible label rename must also update matching rag_documents rows.
    """
    renamed_pairs = []

    for item in items:
        old_label = str(item.original_chapter or "").strip()
        new_label = str(item.chapter or "").strip()

        if (
            not old_label
            or not new_label
            or normalize_chapter_lookup(old_label) == normalize_chapter_lookup(new_label)
        ):
            continue

        response = (
            admin_client
            .table("rag_documents")
            .select("id,title")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", old_label)
            .execute()
        )

        for document in response.data or []:
            current_title = document.get("title") or ""
            next_title = (
                current_title.replace(old_label, new_label)
                if old_label in current_title
                else current_title
            )

            admin_client.table("rag_documents").update({
                "chapter": new_label,
                "title": next_title,
            }).eq("id", document["id"]).execute()

        renamed_pairs.append({
            "from": old_label,
            "to": new_label,
        })

    return renamed_pairs


@router.get("")
def get_syllabus():
    """Return the Class 1-10 syllabus tree plus uploaded RAG chapter metadata."""
    return {
        "success": True,
        "syllabus": merge_uploaded_rag_chapters(SYLLABUS),
        "lesson_steps": LESSON_STEPS
    }


@router.get("/admin-review")
def get_admin_syllabus_review(_admin=Depends(require_admin)):
    """Return effective syllabus dropdowns for admin validation."""
    overrides = fetch_syllabus_overrides()
    subject_overrides = fetch_subject_overrides()
    effective_syllabus = merge_uploaded_rag_chapters(SYLLABUS)

    return {
        "success": True,
        "syllabus": effective_syllabus,
        "content_status": build_chapter_content_status(
            effective_syllabus,
            fetch_rag_chapter_counts(),
        ),
        "overrides": [
            {
                "grade": grade,
                "mode": mode,
                "subject": subject,
                "chapters": override.get("chapters", []),
                "updated_at": override.get("updated_at"),
            }
            for (grade, mode, subject), override in overrides.items()
        ],
        "subject_overrides": [
            {
                "grade": grade,
                "mode": mode,
                "subjects": override.get("subjects", []),
                "updated_at": override.get("updated_at"),
            }
            for (grade, mode), override in subject_overrides.items()
        ],
    }


@router.post("/admin-review/override")
def save_admin_syllabus_override(
    data: SyllabusChapterOverrideRequest,
    admin=Depends(require_admin),
):
    """Persist an admin-approved dropdown list for one grade/mode/subject."""
    grade = data.grade.strip()
    mode = data.mode.strip()
    subject = data.subject.strip()
    chapters = clean_chapter_list([item.chapter for item in data.items])

    if not grade or not mode or not subject:
        raise HTTPException(status_code=400, detail="Grade, mode, and subject are required.")

    if not chapters:
        raise HTTPException(status_code=400, detail="At least one chapter is required.")

    try:
        renamed_pairs = rename_rag_chapter_labels(grade, subject, data.items)
        response = (
            admin_client
            .table("syllabus_chapter_overrides")
            .upsert(
                {
                    "grade": grade,
                    "mode": mode,
                    "subject": subject,
                    "chapters": chapters,
                    "updated_by": admin["profile"]["id"],
                },
                on_conflict="grade,mode,subject",
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save syllabus review. Run "
                "backend/sql/add_syllabus_chapter_overrides.sql in Supabase SQL editor."
            ),
        ) from exc

    return {
        "success": True,
        "message": "Syllabus dropdown saved.",
        "override": response.data[0] if response.data else None,
        "renamed": renamed_pairs,
    }


@router.post("/admin-review/subjects")
def save_admin_subject_override(
    data: SyllabusSubjectOverrideRequest,
    admin=Depends(require_admin),
):
    """Persist the visible subject list for one grade/mode dropdown."""
    grade = data.grade.strip()
    mode = data.mode.strip()
    subjects = clean_subject_list(data.subjects)

    if not grade or not mode:
        raise HTTPException(status_code=400, detail="Grade and mode are required.")

    if not subjects:
        raise HTTPException(status_code=400, detail="At least one subject is required.")

    try:
        response = (
            admin_client
            .table("syllabus_subject_overrides")
            .upsert(
                {
                    "grade": grade,
                    "mode": mode,
                    "subjects": subjects,
                    "updated_by": admin["profile"]["id"],
                },
                on_conflict="grade,mode",
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save subject review. Run "
                "backend/sql/add_syllabus_chapter_overrides.sql in Supabase SQL editor."
            ),
        ) from exc

    return {
        "success": True,
        "message": "Subject list saved.",
        "override": response.data[0] if response.data else None,
    }
