"""
audio_cache_service.py — Pre-warmed TTS audio cache backed by Supabase Storage.

Storage: Supabase Storage (bucket "lesson-audio", public)
  Client: admin_client.storage.from_(BUCKET_NAME) — same Supabase project
  and client used everywhere else in the app (see rag_visual_service.py for
  the same upload/get_public_url pattern). No separate credentials needed —
  reuses the existing admin_client service-role connection.

  Cloudflare R2 was evaluated but never adopted; this service now matches
  what's actually deployed — the "lesson-audio" bucket and its existing
  cached rows already live in Supabase Storage.

DB tracking: lesson_audio_cache table on Supabase 1 (primary)
  — stores public URLs, file sizes, cache keys

Flow:
  1. get_cached_audio_url(grade, ...) → URL or None
     Single DB lookup by cache_key (indexed). Returns Supabase Storage public URL.
  2. store_audio(grade, ..., mp3_bytes) → URL
     Uploads to the Supabase Storage bucket, saves public URL + metadata to DB.
"""

import hashlib
import os
import re
import unicodedata

from app.services.auth_service import admin_client
from app.services.logger_service import get_logger

_log = get_logger("audio_cache_service")

BUCKET_NAME = os.getenv("LESSON_AUDIO_BUCKET", "lesson-audio")


WELCOME_AUDIO_PATHS = {
    "en-IN-NeerjaNeural": "likha/welcome/en-in-neerja.mp3",
    "hi-IN-SwaraNeural": "likha/welcome/hi-in-swara.mp3",
}


def _upload_to_supabase_storage(file_path: str, mp3_bytes: bytes) -> str:
    """
    Upload MP3 bytes to the Supabase Storage bucket and return its public URL.
    Raises RuntimeError if the bucket is missing or the upload fails.
    """
    try:
        admin_client.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=mp3_bytes,
            file_options={"content-type": "audio/mpeg", "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(
            f"Unable to upload audio to Supabase Storage bucket '{BUCKET_NAME}': {exc}"
        ) from exc

    return admin_client.storage.from_(BUCKET_NAME).get_public_url(file_path)


# ── Cache key ─────────────────────────────────────────────────────────────────

def _make_cache_key(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
) -> str:
    """Deterministic SHA-256 hash — same inputs always produce the same key."""
    raw = f"{grade}|{subject}|{chapter}|{step_title}|{voice}|{rate}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_file_path(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
) -> str:
    """
    Build a human-readable, voice-specific Storage path.

    Cache records are keyed by grade, subject, chapter, step, voice, and rate.
    The object path must include voice/rate too, otherwise a Hindi Swara upload
    can overwrite another narration asset that shares the same lesson path.
    """
    def slugify(s: str) -> str:
        """
        Produce an ASCII-only path segment accepted by Supabase Storage.

        Python's ``\\w`` includes Devanagari and other Unicode letters, but the
        Storage API rejects those object keys. A stable hash suffix retains
        uniqueness whenever normalization strips non-ASCII chapter text.
        """
        original = str(s).strip()
        has_non_ascii = any(ord(char) > 127 for char in original)
        normalized = unicodedata.normalize("NFKD", original)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
        ascii_text = re.sub(r"[^a-z0-9\s-]", "", ascii_text)
        ascii_text = re.sub(r"[\s_]+", "-", ascii_text)
        ascii_text = re.sub(r"-+", "-", ascii_text).strip("-")
        if has_non_ascii:
            digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:10]
            ascii_text = f"{ascii_text or 'item'}-{digest}"
        return ascii_text[:60].strip("-")

    grade_slug = slugify(grade)          # grade-5
    subject_slug = slugify(subject)      # hindi
    chapter_slug = slugify(chapter)
    step_slug = slugify(step_title)
    voice_slug = slugify(voice)          # hi-in-swaraneural
    rate_slug = slugify(rate.replace("+", "plus").replace("%", "percent"))

    return (
        f"{grade_slug}/{subject_slug}/{chapter_slug}/"
        f"{voice_slug}/{rate_slug}/{step_slug}.mp3"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_likha_welcome_audio_url(voice: str) -> str | None:
    """Return the shared pre-warmed Likha welcome MP3 for a neural voice."""
    file_path = WELCOME_AUDIO_PATHS.get(voice)
    if not file_path:
        return None

    try:
        file_name = file_path.rsplit("/", 1)[-1]
        entries = admin_client.storage.from_(BUCKET_NAME).list(
            path="likha/welcome",
            options={"search": file_name},
        )
        if not any(entry.get("name") == file_name for entry in entries or []):
            return None
        return admin_client.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception as exc:
        _log.warning("audio_cache.welcome_get_failed", error=str(exc)[:120])
        return None


def store_likha_welcome_audio(voice: str, mp3_bytes: bytes) -> str:
    """Upload or replace the shared Likha welcome MP3 for one neural voice."""
    file_path = WELCOME_AUDIO_PATHS.get(voice)
    if not file_path:
        raise ValueError(f"Unsupported Likha welcome voice: {voice}")

    return _upload_to_supabase_storage(file_path, mp3_bytes)


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
    DB is always Supabase 1; URL points to Supabase Storage.
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
    Upload MP3 bytes to Supabase Storage, then save the public URL
    and metadata to lesson_audio_cache on Supabase 1.

    Returns the public URL.
    Raises RuntimeError on upload or DB failure.
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    file_path = _make_file_path(grade, subject, chapter, step_title, voice, rate)

    # ── Upload to Supabase Storage ──────────────────────────────────────────
    public_url = _upload_to_supabase_storage(file_path, mp3_bytes)

    # ── Save to DB (Supabase 1) ────────────────────────────────────────────
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
        storage="Supabase Storage",
        url=public_url[:80],
    )
    return public_url


def get_audio_cache_overview(grade: str | None = None) -> dict:
    """
    Return a summary of cached audio files — used by admin Cache Management page.
    Reads from lesson_audio_cache DB table on Supabase 1.
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
