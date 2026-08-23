import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.data.syllabus import SYLLABUS, LESSON_STEPS
from app.services.auth_service import admin_client, require_admin
from app.services.board_service import normalize_board
from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS

_logger = logging.getLogger("likhapoha.syllabus")

router = APIRouter()


UPLOAD_PLACEHOLDER_CHAPTERS = {
    "Uploaded Book Content",
}


def placeholder_chapter_for_mode(mode):
    """Return the only non-RAG chapter placeholder allowed for an empty subject."""
    return "Uploaded Book Content"


def is_uploaded_placeholder(chapter):
    """Return whether a syllabus chapter is only a pre-upload placeholder."""
    return chapter in UPLOAD_PLACEHOLDER_CHAPTERS


def is_exemplar_chapter(chapter):
    """
    Return whether a chapter label is an NCERT Exemplar supplementary book
    entry (e.g. "Exemplar: Matter in Our Surroundings"), rather than a
    regular textbook chapter.

    Per explicit user instruction: hide ALL Exemplar chapters from every
    grade/subject's student-facing dropdown. Exemplar content was uploaded
    to rag_documents as a supplementary problem-book alongside the main
    NCERT textbook chapters (confirmed: 179 such rows across 11 grade/
    subject combinations — Grade 8/9/10/11/12 Science, Maths, Physics,
    Biology), but students should only see the main textbook chapters in
    the Lessons dropdown. This check is applied everywhere rag_documents
    rows are turned into dropdown options, so Exemplar chapters never
    appear for ANY grade or subject, not just the ones already found.
    """
    return str(chapter or "").strip().lower().startswith("exemplar:")


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


def extract_book_source(text):
    """Find the book/source name when one subject has multiple books."""
    normalized = str(text or "").lower()

    if re.search(r"\bgeography\b", normalized):
        return "Geography"

    if re.search(r"\bhistory\b", normalized):
        return "History"

    if re.search(r"\bcivics\b|\bpolitical\s+science\b", normalized):
        return "Political Science"

    if re.search(r"\beconomics\b", normalized):
        return "Economics"

    if re.search(r"\bsupplement(?:ary|ery)?\b|\bsupplement(?:ary|ery)?\s+reader\b", normalized):
        return "Supplementary Reader"

    if re.search(r"\bgrammar\b|\bgrammer\b", normalized):
        return "Grammar"

    if re.search(r"\bwork\s*book\b|\bworkbook\b", normalized):
        return "Workbook"

    if re.search(r"\btext\s*book\b|\btextbook\b|\bbeehive\b", normalized):
        return "Text Book"

    if re.search(r"\breader\b", normalized):
        return "Reader"

    return ""


def book_source_rank(source):
    """Sort book sources in the order students usually study them."""
    ranks = {
        "Text Book": 1,
        "Reader": 2,
        "Supplementary Reader": 3,
        "Grammar": 4,
        "Workbook": 5,
        "History": 6,
        "Geography": 7,
        "Political Science": 8,
        "Economics": 9,
    }

    return ranks.get(source or "", 99)


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


def strip_book_source_prefix(chapter):
    """Remove display-only book source prefixes from a chapter label."""
    return re.sub(
        (
            r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
            r"History|Geography|Political Science|Economics)\s*[-:]\s*"
        ),
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

    # Exemplar chapters already have "Exemplar:" as a distinguishing prefix —
    # adding "Part N - " would break the exemplar lock checks everywhere.
    if normalized.startswith("exemplar:") or "exemplar:" in normalized:
        return chapter

    front_matter_match = re.match(
        r"^front matter\s*(?:\((?:part\s*)?(?:i{1,3}|iv|v|\d+)\))?$",
        normalized,
        flags=re.IGNORECASE,
    )

    if front_matter_match:
        return f"{format_part_label(part_number)} - Front Matter"

    return f"{format_part_label(part_number)} - {chapter}"


def create_source_display_label(chapter, source, use_source_prefix):
    """
    Add a display-only source prefix for subjects with multiple books.

    For example, Grade 10 English may have Text Book, Supplementary Reader, and
    Grammar documents. Prefixing prevents duplicate-looking "Chapter 1" labels
    while the stored RAG chapter remains clean.
    """
    chapter = str(chapter or "").strip()
    source = str(source or "").strip()

    if not use_source_prefix or not source or not chapter:
        return chapter

    if re.match(
        (
            r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
            r"History|Geography|Political Science|Economics)\s*[-:]"
        ),
        chapter,
        flags=re.IGNORECASE,
    ):
        return chapter

    return f"{source} - {chapter}"


def is_part_display_label(chapter):
    """Return whether a dropdown label is scoped to a displayed book part."""
    return bool(re.match(r"^\s*part\s*\d+\s*[-:]", str(chapter or ""), re.I))


def keep_consistent_part_series(chapters):
    """
    Drop accidentally mixed book-series labels from a reviewed dropdown list.

    A review can become polluted if admins switch grades while saving. When a
    list mixes normal chapter labels with Part 1/Part 2 labels, keep the series
    that appears first, which matches what the admin was reviewing on screen.
    """
    labels = clean_chapter_list(chapters)

    if not labels:
        return []

    has_part_labels = any(is_part_display_label(chapter) for chapter in labels)
    has_plain_labels = any(not is_part_display_label(chapter) for chapter in labels)

    if not has_part_labels or not has_plain_labels:
        return labels

    keep_part_labels = is_part_display_label(labels[0])

    return [
        chapter
        for chapter in labels
        if is_part_display_label(chapter) == keep_part_labels
    ]


def title_prefix_for_source_detection(title, chapter):
    """
    Return the book/part-labeling portion of a title, with the chapter's own
    text stripped off the end.

    rag_documents.title is always built as "<book/part description> -
    {chapter}", so the chapter's own subject-matter wording must never be
    scanned for source/part detection -- confirmed live for Grade 6 Social
    Science: chapter "4. Timeline and Sources of History" made
    extract_book_source() misdetect the book source as "History" (it's
    really "Text Book", the word "History" only appears because it's part of
    THIS chapter's own title), and every single "Text Book - N. <title>"
    chapter made extract_part_number() misdetect the chapter's own leading
    ordinal N as a fake "Part N" marker (its regex matches "book" followed by
    "- N", which is exactly what "Text Book - 4." looks like). Both bugs
    together caused every chapter in the subject to get a spurious, mutually
    inconsistent "Part N -" / "<wrong source> - Part N -" label, which in
    turn broke admin-reviewed-order matching in normalize_rag_chapter_lookup
    (a differently-prefixed live label never matches the unprefixed saved
    override), so the whole dropdown silently fell back to raw upload order.
    """
    title = title or ""
    chapter = chapter or ""
    if chapter and title.endswith(chapter):
        return title[: -len(chapter)]
    return title


def uploaded_chapter_sort_key(item):
    """
    Sort uploaded RAG chapters for student dropdowns.

    Confirmed chapter text is preserved, but the list is presented as a book:
    front matter first, then Chapter 1..N, grouped by Part I/II when present.
    """
    chapter = item["chapter"]
    title = item.get("title") or ""
    title_prefix = title_prefix_for_source_detection(title, chapter)
    normalized = chapter.lower()
    source = extract_book_source(title_prefix)
    part_number = extract_part_number(title_prefix)
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
        book_source_rank(source),
        part_number,
        section_rank,
        chapter_rank,
        item.get("created_at", ""),   # insertion order as tiebreaker (chapters uploaded in order)
        chapter.lower(),
    )


def normalize_chapter_lookup(chapter):
    """Normalize chapter labels for duplicate detection without changing display text."""
    return re.sub(r"\s+", " ", str(chapter or "").strip()).casefold()


def normalize_rag_chapter_lookup(chapter):
    """Normalize display labels to the stored RAG chapter label for matching.

    Display labels are constructed as "<Source> - Part N - <chapter>" (source
    prefix wraps the part prefix, see sort_uploaded_chapters) -- so unwrapping
    must strip the source prefix FIRST, then the part prefix. Stripping in
    the opposite order (as this used to) leaves a dangling "Part N - " on any
    chapter that has both prefixes stacked, so it can never normalize-match
    a plain saved-override label, and the admin-reviewed chapter order is
    silently discarded for the entire subject in favor of raw upload order --
    confirmed live for Grade 6 Social Science, where this caused all 14
    reviewed chapters to be dropped and the dropdown to fall back to
    unsorted/mislabeled live chapters."""
    without_source = strip_book_source_prefix(chapter)
    without_part = strip_part_prefix(without_source)

    return re.sub(r"\s+", " ", without_part.strip()).casefold()


def sort_uploaded_chapters(existing_chapters, uploaded_items):
    """Sort uploaded RAG chapters and never mix in static syllabus defaults."""
    placeholder_chapters = [
        chapter
        for chapter in existing_chapters
        if is_uploaded_placeholder(chapter)
    ]
    seen = set()
    sorted_uploaded = []
    part_numbers = {
        extract_part_number(
            title_prefix_for_source_detection(item.get("title") or "", item.get("chapter") or "")
        )
        for item in uploaded_items
    }
    source_labels = {
        extract_book_source(
            title_prefix_for_source_detection(item.get("title") or "", item.get("chapter") or "")
        )
        for item in uploaded_items
    }
    use_part_prefix = len(part_numbers) > 1
    use_source_prefix = len({source for source in source_labels if source}) > 1

    for item in sorted(uploaded_items, key=uploaded_chapter_sort_key):
        chapter = item["chapter"].strip()
        title_prefix = title_prefix_for_source_detection(item.get("title") or "", chapter)
        source = extract_book_source(title_prefix)
        part_number = extract_part_number(title_prefix)
        display_chapter = create_part_display_label(
            chapter,
            part_number,
            use_part_prefix,
        )
        display_chapter = create_source_display_label(
            display_chapter,
            source,
            use_source_prefix,
        )
        lookup_key = normalize_chapter_lookup(display_chapter)

        if not display_chapter or lookup_key in seen:
            continue

        sorted_uploaded.append(display_chapter)
        seen.add(lookup_key)

    if sorted_uploaded:
        return sorted_uploaded

    return placeholder_chapters


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
        # Strip non-printable characters (e.g. \x08 backspace from PDF
        # uploads) the same way merge_uploaded_rag_chapters() already does
        # for live rag_documents.chapter values -- otherwise a saved admin
        # override containing a stray backspace (confirmed live: 4 of 10
        # Grade 6 Maths chapters) never normalizes to match its live
        # counterpart in merge_reviewed_and_live_chapters(), so those
        # entries silently fall through to the "append new live chapters
        # at the end" path instead of keeping their correct reviewed
        # position -- producing an out-of-order student-facing dropdown.
        label = "".join(c for c in str(chapter or "") if c.isprintable()).strip()
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
    """
    Apply reviewed subject order without hiding newly uploaded live RAG subjects.

    A saved subject review can become stale when admins upload another subject
    later. Keep the reviewed order first, then append any live subject that has
    real RAG chapters for the same grade and board so the admin can review it.
    """
    for (grade, mode), override in subject_overrides.items():
        subjects = override.get("subjects") or []

        if not subjects:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode_data = grade_data.setdefault(mode, {})
        reviewed_mode_data = {}

        for subject in subjects:
            reviewed_mode_data[subject] = mode_data.get(
                subject,
                [placeholder_chapter_for_mode(mode)],
            )

        for subject, chapters in mode_data.items():
            if subject in reviewed_mode_data:
                continue

            has_live_content = any(
                not is_uploaded_placeholder(chapter)
                for chapter in chapters
            )

            if has_live_content:
                reviewed_mode_data[subject] = chapters

        grade_data[mode] = reviewed_mode_data

    return merged


def build_rag_only_syllabus_shell(syllabus):
    """
    Build grade/board/subject selectors without carrying static chapters forward.

    Uploaded RAG metadata is the source of truth for chapter dropdowns. The
    static syllabus catalog is intentionally reduced to a shell so default Class
    9/10 chapters cannot leak into another grade or reappear after deletion.
    """
    shell = {}

    for grade, grade_data in (syllabus or {}).items():
        shell[grade] = {}

        for mode, mode_data in (grade_data or {}).items():
            shell[grade][mode] = {}

            for subject in (mode_data or {}).keys():
                shell[grade][mode][subject] = [placeholder_chapter_for_mode(mode)]

    return shell


# ── In-process TTL cache for rag_documents ───────────────────────────────────
# Each unique `fields` string is cached separately for 30 minutes.
# This eliminates the 860-row Supabase query that fires on EVERY page load.
# Cache is invalidated automatically by TTL, and can be force-cleared by
# calling _invalidate_rag_cache() (e.g. after a RAG upload).
import time as _time  # noqa: E402

_RAG_CACHE: dict[str, tuple[list, float]] = {}   # fields → (rows, expires_at)
_RAG_CACHE_TTL = 1800  # 30 minutes
_RAG_CACHE_CLIENT_REF: object = None   # the supabase object that last filled the cache


def _invalidate_rag_cache() -> None:
    """Force-clear the in-process rag_documents cache (call after RAG upload)."""
    global _RAG_CACHE_CLIENT_REF
    _RAG_CACHE.clear()
    _RAG_CACHE_CLIENT_REF = None
    _logger.info("rag_documents cache invalidated.")


def _fetch_all_rag_documents(fields="grade,subject,chapter,board"):
    """Fetch rag_documents from the primary Supabase project.

    Results are cached in-process for 30 minutes to avoid re-fetching on every
    page load (the primary cause of Supabase egress overage).
    """
    global _RAG_CACHE_CLIENT_REF
    # Invalidate cache when supabase client is replaced (e.g. test monkeypatching).
    # Use `is` (object identity) not id() — id() can be reused after garbage collection.
    if _RAG_CACHE_CLIENT_REF is not None and _RAG_CACHE_CLIENT_REF is not supabase:
        _RAG_CACHE.clear()
        _RAG_CACHE_CLIENT_REF = None

    # Return cached result if still valid
    cached = _RAG_CACHE.get(fields)
    if cached and _time.monotonic() < cached[1]:
        return cached[0]

    def _query(db, select_fields, label="primary"):
        """Return (rows, failed). `failed=True` only on a genuine query error —
        never on a not-yet-configured client — so callers can tell "really
        empty" apart from "we couldn't ask" and avoid caching the latter.
        """
        if db is None:
            return [], False

        try:
            r = db.table("rag_documents").select(select_fields).execute()
            rows = r.data or []
            _logger.info("rag_documents query [%s]: %d rows returned.", label, len(rows))
            return rows, False
        except Exception as exc:
            _logger.error("rag_documents query [%s] FAILED with %s: %s", label, type(exc).__name__, exc)
            try:
                r = db.table("rag_documents").select("grade,subject,chapter").execute()
                rows = r.data or []
                _logger.info("rag_documents fallback query [%s]: %d rows returned.", label, len(rows))
                return rows, False
            except Exception as exc2:
                _logger.error("rag_documents fallback query [%s] also FAILED: %s", label, exc2)
                return [], True

    combined, failed = _query(supabase, fields, label="primary")
    _logger.info("_fetch_all_rag_documents total: %d rows", len(combined))

    # A genuine query failure must never be cached as "no documents" — that would
    # turn one transient Supabase hiccup into 30 minutes of every dropdown across
    # every grade/subject looking empty. Skip the cache write so the very next
    # request retries instead of serving a stale, wrong empty result.
    if failed:
        _logger.warning(
            "_fetch_all_rag_documents: fetch failure detected — not caching this result, "
            "will retry on next request."
        )
        return combined

    # Store in cache with TTL and record which client filled it
    _RAG_CACHE[fields] = (combined, _time.monotonic() + _RAG_CACHE_TTL)
    _RAG_CACHE_CLIENT_REF = supabase
    return combined


def fetch_rag_chapter_counts():
    """Count live RAG documents by grade/mode/subject/chapter label."""
    all_docs = _fetch_all_rag_documents()
    if not all_docs:
        return {}

    counts = {}

    for document in all_docs:
        grade = document.get("grade")
        subject = document.get("subject")
        chapter = document.get("chapter")

        if (
            not grade
            or not subject
            or not chapter
            or "Olympiad" in subject
            or is_exemplar_chapter(chapter)
        ):
            continue

        mode = normalize_board(document.get("board"))
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


def chapter_sort_tuple_for_ordering(chapter):
    """Return a (source_rank, part_number, chapter_number) tuple for
    chronological ordering.

    Display labels can carry a "Part N - " and/or "<Source> - " prefix (see
    create_part_display_label/create_source_display_label) stacked in front of
    the actual chapter text. Multi-book subjects (e.g. Grade 10 Social
    Science's Text Book/History/Geography/Political Science, each restarting
    at "Chapter 1") must be grouped by source FIRST, then ordered by chapter
    number within that source -- sorting by chapter number alone interleaves
    every book's Chapter 1s together, then every book's Chapter 2s, and so on
    (confirmed live for Grade 10 Social Science's dropdown). Multi-part
    textbooks similarly restart chapter numbering per part (e.g. "Part 1 -
    Chapter 1", "Part 2 - Chapter 1"), so the part number is the next sort
    key, with chapter number only breaking ties within the same source and
    part. Returns None if the chapter has no parseable chapter number (so
    callers can detect subjects that shouldn't be reordered at all, e.g.
    custom-titled readers).
    """
    text = str(chapter or "")
    without_source = strip_book_source_prefix(text)
    chapter_number = extract_chapter_number(strip_part_prefix(without_source))

    if chapter_number is None:
        return None

    part_number = extract_part_number(text) if is_part_display_label(text) else 0
    source_rank = book_source_rank(extract_book_source(text))

    return (source_rank, part_number, chapter_number)


def merge_reviewed_and_live_chapters(reviewed_chapters, live_chapters, mode="CBSE"):
    """
    Keep admin-reviewed order, but reconcile it against live RAG content.

    The RAG table is the source of truth for what students can study. A saved
    review should preserve ordering for matching live chapters, but it should
    not hide newly reuploaded chapters or keep deleted chapters selectable.

    A saved review is a point-in-time snapshot: if chapters are re-uploaded or
    newly added to a subject AFTER the review was saved, the old code appended
    them to the very END of the reviewed list regardless of their chapter
    number -- confirmed live for Grade 12 Geography, where chapters 3-7 were
    uploaded/re-reviewed after the original review (covering chapters 1, 2,
    9-17) was saved, producing the student-facing order 1, 2, 9, 10, ..., 17,
    3, 4, 5, 6, 7 instead of 1-17. When every chapter in the final merged list
    has a parseable "Chapter N" number, re-sort the whole list chronologically
    by that number so out-of-order reviews like this self-heal automatically.
    Subjects whose chapters aren't numbered (e.g. custom-titled readers) keep
    the original reviewed-order-then-append behavior untouched.
    """
    reviewed = clean_chapter_list(reviewed_chapters)
    live = clean_chapter_list([
        chapter
        for chapter in (live_chapters or [])
        if not is_uploaded_placeholder(chapter)
    ])

    if not live:
        return [placeholder_chapter_for_mode(mode)]

    live_lookup = {
        normalize_rag_chapter_lookup(chapter): chapter
        for chapter in live
    }
    merged = []
    seen = set()

    for chapter in reviewed:
        lookup = normalize_rag_chapter_lookup(chapter)

        if lookup in live_lookup:
            merged.append(chapter)
            seen.add(lookup)

    for chapter in live:
        lookup = normalize_rag_chapter_lookup(chapter)

        if lookup not in seen:
            merged.append(chapter)
            seen.add(lookup)

    result = merged or live

    if len(result) > 1:
        sort_tuples = [chapter_sort_tuple_for_ordering(chapter) for chapter in result]

        if all(sort_tuple is not None for sort_tuple in sort_tuples):
            result = [
                chapter
                for _, chapter in sorted(
                    zip(sort_tuples, result, strict=True),
                    key=lambda pair: pair[0],
                )
            ]

    return result


def apply_syllabus_overrides(merged, overrides):
    """Apply admin-reviewed dropdowns as authoritative student-facing lists."""
    for (grade, mode, subject), override in overrides.items():
        chapters = clean_chapter_list(override.get("chapters") or [])

        if not chapters:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode_data = grade_data.setdefault(mode, {})
        mode_data[subject] = merge_reviewed_and_live_chapters(
            chapters,
            mode_data.get(subject, []),
            mode,
        )

    return merged


def merge_uploaded_rag_chapters(syllabus):
    """
    Build syllabus dropdowns from uploaded RAG document chapters.

    The static syllabus only supplies grade/board/subject shells. Chapter
    options are loaded from rag_documents so deleted content cannot remain
    selectable and chapters from one grade cannot be mixed into another grade.
    """
    merged = build_rag_only_syllabus_shell(syllabus)

    all_docs = _fetch_all_rag_documents("grade,subject,chapter,title,created_at,board")

    uploaded_by_subject = {}

    for document in all_docs:
        grade = document.get("grade")
        subject = document.get("subject")
        raw_chapter = document.get("chapter")

        if (
            not grade
            or not subject
            or not raw_chapter
            or "Olympiad" in subject
            or is_exemplar_chapter(raw_chapter)
        ):
            continue

        # Strip non-printable characters (e.g. \x08 backspace from PDF uploads)
        # so chapter names display and match cleanly everywhere.
        chapter = "".join(c for c in raw_chapter if c.isprintable()).strip()
        if not chapter:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode = normalize_board(document.get("board"))
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

    overrides = fetch_syllabus_overrides()

    # ── Grade 11/12 secondary-DB fallback ────────────────────────────────────
    # merge_reviewed_and_live_chapters correctly returns a placeholder when
    # there are no live RAG docs (e.g. no upload yet for a subject). However,
    # Grade 11/12 content lives in the secondary Supabase which may be
    # temporarily unavailable (key rotation, maintenance). In that case
    # uploaded_by_subject has no Grade 11/12 entries, so the normal path would
    # hide the chapters under "Uploaded Book Content".
    #
    # When we detect that the secondary DB is down (no Grade 11/12 docs fetched)
    # we inject the saved chapter overrides DIRECTLY — bypassing
    # merge_reviewed_and_live_chapters — so students continue seeing their
    # correct chapter dropdowns. This does NOT affect Grade 1-10 subjects which
    # always go through the normal merge path.
    _secondary_grades_in_docs = {
        grade
        for (grade, _, _) in uploaded_by_subject.keys()
        if grade in ("Grade 11", "Grade 12")
    }
    _grade_1112_overrides = {}
    _other_overrides = {}
    for key, val in overrides.items():
        if key[0] in ("Grade 11", "Grade 12") and key[0] not in _secondary_grades_in_docs:
            # Secondary DB unavailable for this grade → inject directly
            _grade_1112_overrides[key] = val
        else:
            _other_overrides[key] = val

    # Direct injection: set chapters without requiring live RAG docs
    for (grade, mode, subject), override in _grade_1112_overrides.items():
        chapters = clean_chapter_list(override.get("chapters") or [])
        if not chapters:
            continue
        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode_data = grade_data.setdefault(mode, {})
        mode_data[subject] = chapters

    # Normal path for all other grades (Grade 1-10 + Grade 11/12 when DB is up)
    merged = apply_syllabus_overrides(merged, _other_overrides)

    return apply_subject_overrides(merged, fetch_subject_overrides())


def rename_rag_chapter_labels(grade, mode, subject, items):
    """
    Keep RAG metadata aligned when admin renames a dropdown chapter label.

    The student pages send the selected chapter back into RAG retrieval, so a
    visible label rename must also update matching rag_documents rows.
    """
    renamed_pairs = []
    from app.services.grade_db_router import get_content_db  # noqa: PLC0415
    content_db = get_content_db(grade)

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
            content_db
            .table("rag_documents")
            .select("id,title,board,chapter")
            .eq("grade", grade)
            .eq("subject", subject)
            .execute()
        )
        old_lookup_key = normalize_rag_chapter_lookup(old_label)

        for document in response.data or []:
            document_mode = normalize_board(document.get("board"))

            if document_mode != mode:
                continue

            stored_chapter = document.get("chapter") or ""

            if normalize_rag_chapter_lookup(stored_chapter) != old_lookup_key:
                continue

            current_title = document.get("title") or ""
            clean_new_label = strip_book_source_prefix(strip_part_prefix(new_label))
            next_title = (
                current_title.replace(stored_chapter, clean_new_label)
                if stored_chapter and stored_chapter in current_title
                else current_title
            )

            content_db.table("rag_documents").update({
                "chapter": clean_new_label,
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
        renamed_pairs = rename_rag_chapter_labels(grade, mode, subject, data.items)
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
