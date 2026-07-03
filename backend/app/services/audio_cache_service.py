"""
audio_cache_service.py — Pre-warmed TTS audio cache backed by Supabase Storage.

Flow:
  1. get_cached_audio(grade, subject, chapter, step_title) → URL or None
     Frontend calls this before generating TTS. If URL returned → instant playback.

  2. store_audio(grade, subject, chapter, step_title, mp3_bytes) → URL
     Called by prewarm script after Edge TTS generates an MP3.
     Uploads to Supabase Storage bucket "lesson-audio", saves URL to DB.

Storage layout in bucket:
    lesson-audio / grade-9 / english / chapter-1-how-i-taught / concept-introduction.mp3

POC scope: Grade 9 English (155 lessons, ~240 MB actual, ~48 min generation).
Extend to other grades/subjects by running the prewarm script with different filters.
"""

import hashlib
import os
import re

from app.services.auth_service import admin_client
from app.services.logger_service import get_logger

_log = get_logger("audio_cache_service")

BUCKET_NAME = "lesson-audio"

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
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    try:
        r = (
            admin_client
            .table("lesson_audio_cache")
            .select("audio_url")
            .eq("cache_key", cache_key)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if r.data:
            # Update last_accessed_at in background (best-effort)
            try:
                admin_client.table("lesson_audio_cache").update(
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
    Upload MP3 bytes to Supabase Storage and save the public URL to DB.
    Returns the public URL.
    Raises RuntimeError if upload or DB insert fails.
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    file_path = _make_file_path(grade, subject, chapter, step_title)

    # ── Upload to Supabase Storage ─────────────────────────────────────────
    try:
        admin_client.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=mp3_bytes,
            file_options={"content-type": "audio/mpeg", "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(f"Storage upload failed: {exc}") from exc

    # ── Get public URL ─────────────────────────────────────────────────────
    try:
        public_url = admin_client.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception as exc:
        raise RuntimeError(f"Could not get public URL: {exc}") from exc

    # ── Save to DB ─────────────────────────────────────────────────────────
    try:
        admin_client.table("lesson_audio_cache").upsert(
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

    _log.info(
        "audio_cache.stored",
        grade=grade,
        subject=subject,
        chapter=chapter,
        step_title=step_title,
        size_kb=round(len(mp3_bytes) / 1024),
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
