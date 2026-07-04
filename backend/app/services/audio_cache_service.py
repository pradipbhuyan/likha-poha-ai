"""
audio_cache_service.py — Pre-warmed TTS audio cache backed by Supabase Storage.

Storage routing:
  - Grade 9  → 1st Supabase (dpivlbbyzlbpwnwgajso) — bucket: lesson-audio
  - All other grades → 2nd Supabase (sjfjyzaaypfzyfhhggqw) — bucket: lesson-audio

This keeps Grade 9 (~955 MB) on Supabase 1 and all other grades on Supabase 2
so neither project hits the 1 GB free tier storage limit.

Flow:
  1. get_cached_audio_url(grade, ...) → URL or None
     Looks up the correct Supabase DB table for the grade.
  2. store_audio(grade, ..., mp3_bytes) → URL
     Uploads to the correct Supabase Storage bucket and saves URL to DB.
"""

import hashlib
import os
import re

from app.services.auth_service import admin_client
from app.services.logger_service import get_logger

_log = get_logger("audio_cache_service")

BUCKET_NAME = "lesson-audio"

# Grades stored on 2nd Supabase storage (all except Grade 9)
_GRADE_9 = "grade 9"


def _get_storage_client(grade: str):
    """
    Return the correct Supabase storage client for the given grade.
    Grade 9 → 1st Supabase (admin_client).
    All other grades → 2nd Supabase (grade_1112_client).
    """
    if (grade or "").lower().strip() == _GRADE_9:
        return admin_client
    try:
        from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
        if grade_1112_client is None:
            _log.warning("audio_cache: 2nd Supabase not configured, falling back to primary")
            return admin_client
        return grade_1112_client
    except Exception:
        return admin_client


def _get_db_client(grade: str):
    """
    Return the correct Supabase DB client for lesson_audio_cache queries.
    All grades use the primary DB (lesson_audio_cache lives on Supabase 1).
    Storage URLs differ but the DB table is always on Supabase 1.
    """
    return admin_client

# ── Cache key ─────────────────────────────────────────────────────────────────

def _make_cache_key(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
) -> str:
    """Deterministic hash — same inputs always produce the same key."""
    raw = f"{grade}|{subject}|{chapter}|{step_title}|{voice}|{rate}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_file_path(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
) -> str:
    """Build a human-readable storage path inside the bucket."""
    def slugify(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s)
        return s[:60].strip("-")

    grade_slug   = slugify(grade)    # grade-9
    subject_slug = slugify(subject)  # english
    chapter_slug = slugify(chapter)  # chapter-1-how-i-taught-my-grandmother
    step_slug    = slugify(step_title)  # concept-introduction

    return f"{grade_slug}/{subject_slug}/{chapter_slug}/{step_slug}.mp3"


# ── Public API ────────────────────────────────────────────────────────────────

def get_cached_audio_url(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
) -> str | None:
    """
    Return pre-warmed audio URL if available, else None.
    Fast path: single DB lookup by cache_key (indexed).
    DB always lives on Supabase 1; storage URL may point to Supabase 2.
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    db = _get_db_client(grade)
    try:
        r = (
            db
            .table("lesson_audio_cache")
            .select("audio_url")
            .eq("cache_key", cache_key)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if r.data:
            try:
                db.table("lesson_audio_cache").update(
                    {"last_accessed_at": "now()"}
                ).eq("cache_key", cache_key).execute()
            except Exception:
                pass
            return r.data[0]["audio_url"]
    except Exception as exc:
        _log.warning("audio_cache.get_failed", error=str(exc)[:120])
    return None


def store_audio(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    mp3_bytes: bytes,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
) -> str:
    """
    Upload MP3 bytes to the correct Supabase Storage for this grade, then
    save the public URL to the DB on Supabase 1.

    Grade 9  → uploads to Supabase 1 lesson-audio bucket
    Others   → uploads to Supabase 2 lesson-audio bucket (more free space)

    Returns the public URL.  Raises RuntimeError on upload or DB failure.
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    file_path = _make_file_path(grade, subject, chapter, step_title)

    storage = _get_storage_client(grade)
    db      = _get_db_client(grade)

    # ── Upload to correct Supabase Storage ────────────────────────────────
    try:
        storage.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=mp3_bytes,
            file_options={"content-type": "audio/mpeg", "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(f"Storage upload failed: {exc}") from exc

    # ── Get public URL ─────────────────────────────────────────────────────
    try:
        public_url = storage.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception as exc:
        raise RuntimeError(f"Could not get public URL: {exc}") from exc

    # ── Save to DB (always Supabase 1) ────────────────────────────────────
    try:
        db.table("lesson_audio_cache").upsert(
            {
                "cache_key":       cache_key,
                "grade":           grade,
                "subject":         subject,
                "chapter":         chapter,
                "step_title":      step_title,
                "voice":           voice,
                "rate":            rate,
                "audio_url":       public_url,
                "file_path":       file_path,
                "file_size_bytes": len(mp3_bytes),
                "status":          "active",
            },
            on_conflict="cache_key",
        ).execute()
    except Exception as exc:
        raise RuntimeError(f"DB upsert failed: {exc}") from exc

    supabase_label = "Supabase 1 (Grade 9)" if (grade or "").lower().strip() == _GRADE_9 else "Supabase 2"
    _log.info(
        "audio_cache.stored",
        grade=grade,
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        size_kb=round(len(mp3_bytes) / 1024),
        storage=supabase_label,
        url=public_url[:80],
    )
    return public_url


def get_audio_cache_overview(grade: str | None = None) -> dict:
    """
    Return a summary of cached audio files — used by admin Cache Management page.
    """
    try:
        q = admin_client.table("lesson_audio_cache").select(
            "grade, subject, chapter, step_title, file_size_bytes, created_at"
        ).eq("status", "active")
        if grade:
            q = q.eq("grade", grade)
        r = q.execute()
        rows = r.data or []
        total_files  = len(rows)
        total_bytes  = sum(row.get("file_size_bytes") or 0 for row in rows)
        grades = sorted({row["grade"] for row in rows})
        by_grade = {}
        for row in rows:
            g = row["grade"]
            if g not in by_grade:
                by_grade[g] = {"files": 0, "bytes": 0}
            by_grade[g]["files"] += 1
            by_grade[g]["bytes"] += row.get("file_size_bytes") or 0
        return {
            "success":     True,
            "total_files": total_files,
            "total_mb":    round(total_bytes / 1024 / 1024, 1),
            "grades":      grades,
            "by_grade":    by_grade,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
