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
