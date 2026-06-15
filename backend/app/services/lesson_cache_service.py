"""
Lesson Cache Service
====================
Pre-generated lesson steps and practice questions stored in Supabase.

Design principles:
- Every operation is wrapped in try/except and fails silently.
- A cache miss or any DB error returns None/[] so the caller falls back
  to live LLM generation — the existing flow is never interrupted.
- Run backend/sql/add_lesson_cache.sql in Supabase before enabling.
- Populate via: python3 backend/scripts/prewarm_lessons.py
"""

import hashlib
import json

from app.services.auth_service import admin_client as supabase


def make_lesson_cache_key(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
) -> str:
    """
    Create a deterministic SHA-256 cache key from lesson parameters.

    Control characters (e.g. \\x08 from PDF uploads) are stripped from
    chapter before hashing so dirty DB values still match clean keys.
    """
    clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
    data = {
        "board": (board or "").strip().lower(),
        "grade": (grade or "").strip().lower(),
        "subject": (subject or "").strip().lower(),
        "chapter": clean_chapter.lower(),
        "mode": (mode or "").strip().lower(),
        "step_title": (step_title or "").strip().lower(),
        "teacher_persona": (teacher_persona or "").strip().lower(),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def get_cached_lesson(cache_key: str) -> dict | None:
    """
    Return a cached lesson dict if it exists and is active, else None.

    Returns: {"lesson_content": str, "practice_questions": list, "source_type": str}
    Returns None on cache miss, table-not-found, or any other error.
    """
    try:
        result = (
            supabase
            .table("lesson_cache")
            .select("lesson_content, practice_questions, source_type, access_count")
            .eq("cache_key", cache_key)
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        row = result.data[0]

        # Update access stats fire-and-forget — failure is acceptable
        try:
            supabase.table("lesson_cache").update({
                "access_count": (row.get("access_count") or 0) + 1,
                "last_accessed_at": "now()",
            }).eq("cache_key", cache_key).execute()
        except Exception:
            pass

        return row

    except Exception:
        return None  # Table may not exist yet — fall back to LLM


def store_lesson_cache(
    cache_key: str,
    lesson_content: str,
    source_type: str,
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
    teacher_persona: str = "",
    practice_questions: list | None = None,
) -> None:
    """
    Store a generated lesson (and optional practice questions) in the cache.

    Failures are silently ignored — a failed cache store must never prevent
    the lesson from being delivered to the student.
    """
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
        supabase.table("lesson_cache").upsert(
            {
                "cache_key": cache_key,
                "board": board,
                "grade": grade,
                "subject": subject,
                "chapter": clean_chapter,
                "mode": mode,
                "step_title": step_title,
                "teacher_persona": teacher_persona or "",
                "lesson_content": lesson_content,
                "practice_questions": practice_questions or [],
                "source_type": source_type,
                "status": "active",
                "access_count": 1,
            },
            on_conflict="cache_key",
        ).execute()
    except Exception:
        pass


def invalidate_cache_for_chapter(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
) -> None:
    """
    Mark all cached lessons for a chapter as stale.

    Call this automatically when new RAG content is uploaded for a chapter
    so the next lesson request regenerates with updated textbook context.
    """
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
        supabase.table("lesson_cache").update({"status": "stale"}).match({
            "board": board,
            "grade": grade,
            "subject": subject,
            "chapter": clean_chapter,
        }).execute()
    except Exception:
        pass


_CHAPTER_PREFIX_RE = __import__("re").compile(
    r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
    r"History|Geography|Political Science|Economics)\s*[-:]\s*",
    __import__("re").IGNORECASE,
)


def _normalize_chapter_for_search(chapter: str) -> str:
    """Strip ALL known source prefixes to get the core chapter name."""
    result = (chapter or "").strip()
    while True:
        stripped = _CHAPTER_PREFIX_RE.sub("", result).strip()
        if stripped == result:
            break
        result = stripped
    return result


def get_cached_lesson_by_chapter_text(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    mode: str,
    step_title: str,
) -> dict | None:
    """
    Text-based chapter lookup for when the cache key hash misses.

    The lesson cache was built with chapter names that may have had different
    source prefixes (e.g. 'Economics - Chapter 1: Development' vs the current
    display 'Text Book - Chapter 1: Development').  Both normalize to
    'Chapter 1: Development'.  We use ilike on the chapter column so that any
    prefix variant in the stored row still matches the stripped search term.

    Falls back to None so the caller can continue to other strategies.
    """
    try:
        core = _normalize_chapter_for_search(chapter)
        if not core:
            return None

        result = (
            supabase
            .table("lesson_cache")
            .select("lesson_content, practice_questions, source_type, access_count")
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("mode", mode)
            .eq("step_title", step_title)
            .eq("status", "active")
            .ilike("chapter", f"%{core}%")
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        row = result.data[0]

        # Update access stats fire-and-forget
        try:
            supabase.table("lesson_cache").update({
                "access_count": (row.get("access_count") or 0) + 1,
                "last_accessed_at": "now()",
            }).ilike("chapter", f"%{core}%").eq("grade", grade).eq(
                "subject", subject
            ).eq("mode", mode).eq("step_title", step_title).execute()
        except Exception:
            pass

        return row

    except Exception:
        return None


def archive_lesson_cache_for_grade(grade: str) -> int:
    """
    Archive (soft-delete) all cached lessons for a grade.

    Archived lessons are NOT deleted from the database — they can be restored
    at any time.  This protects token-expensive pre-generated content from
    accidental loss when an admin clicks 'Clear Lessons'.

    Returns the number of lessons archived.
    """
    try:
        result = (
            supabase
            .table("lesson_cache")
            .update({"status": "archived"})
            .eq("grade", grade)
            .in_("status", ["active", "stale"])
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0


def restore_archived_lessons_for_grade(grade: str) -> int:
    """
    Restore archived lessons for a grade back to 'active' status.

    Allows recovery from an accidental 'Clear Lessons' without spending tokens.
    Returns the number of lessons restored.
    """
    try:
        result = (
            supabase
            .table("lesson_cache")
            .update({"status": "active"})
            .eq("grade", grade)
            .eq("status", "archived")
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0


def get_archived_lesson_count(grade: str) -> int:
    """Return count of archived (recoverable) lessons for a grade."""
    try:
        result = (
            supabase
            .table("lesson_cache")
            .select("id", count="exact")
            .eq("grade", grade)
            .eq("status", "archived")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def get_cache_stats() -> dict:
    """Return summary statistics for the admin cache health panel."""
    try:
        result = (
            supabase
            .table("lesson_cache")
            .select("status, access_count, grade, subject")
            .execute()
        )
        rows = result.data or []
        active = [r for r in rows if r.get("status") == "active"]
        stale = [r for r in rows if r.get("status") == "stale"]
        return {
            "total": len(rows),
            "active": len(active),
            "stale": len(stale),
            "total_accesses": sum(r.get("access_count", 0) for r in active),
        }
    except Exception:
        return {"total": 0, "active": 0, "stale": 0, "total_accesses": 0}
