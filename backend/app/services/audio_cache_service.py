"""
audio_cache_service.py — Pre-warmed TTS audio cache backed by Cloudflare R2.

Storage: Cloudflare R2 (S3-compatible, 10 GB free, zero egress fees)
  Bucket: lesson-audio (public)
  Client: boto3 with R2 endpoint

DB tracking: lesson_audio_cache table on Supabase 1 (primary)
  — stores public URLs, file sizes, cache keys
  — DB is always Supabase 1 regardless of storage backend

Flow:
  1. get_cached_audio_url(grade, ...) → URL or None
     Single DB lookup by cache_key (indexed). Returns R2 public URL.
  2. store_audio(grade, ..., mp3_bytes) → URL
     Uploads to R2 bucket, saves public URL + metadata to DB.

Environment variables required:
  R2_ACCOUNT_ID         — Cloudflare Account ID
  R2_ACCESS_KEY_ID      — R2 API token Access Key ID
  R2_SECRET_ACCESS_KEY  — R2 API token Secret Access Key
  R2_BUCKET_NAME        — bucket name (default: lesson-audio)
  R2_PUBLIC_URL         — public base URL e.g. https://pub-xxxx.r2.dev
"""

import hashlib
import os
import re

from app.services.auth_service import admin_client
from app.services.logger_service import get_logger

_log = get_logger("audio_cache_service")

BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "lesson-audio")


# ── R2 client (lazy singleton) ────────────────────────────────────────────────

_r2_client = None


def _get_r2_client():
    """
    Return a boto3 S3 client configured for Cloudflare R2.
    Lazy singleton — created once on first use.
    Raises RuntimeError if R2 credentials are not configured.
    """
    global _r2_client
    if _r2_client is not None:
        return _r2_client

    account_id        = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key_id     = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    if not all([account_id, access_key_id, secret_access_key]):
        raise RuntimeError(
            "Cloudflare R2 credentials not configured. "
            "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env"
        )

    import boto3  # noqa: PLC0415
    _r2_client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name="auto",
    )
    return _r2_client


def _get_r2_public_url(file_path: str) -> str:
    """
    Build the public URL for an object in the R2 bucket.
    Uses R2_PUBLIC_URL env var (set from bucket Settings → Public Access URL).
    e.g. https://pub-xxxx.r2.dev/grade-9/english/ch1/step1.mp3
    """
    base = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
    if not base:
        raise RuntimeError(
            "R2_PUBLIC_URL not configured. "
            "Set it to the public bucket URL from R2 bucket Settings tab."
        )
    return f"{base}/{file_path}"


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
) -> str:
    """Build a human-readable storage path inside the R2 bucket."""
    def slugify(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s)
        return s[:60].strip("-")

    grade_slug   = slugify(grade)        # grade-9
    subject_slug = slugify(subject)      # english
    chapter_slug = slugify(chapter)      # chapter-1-how-i-taught-my-grandmother
    step_slug    = slugify(step_title)   # concept-introduction

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
    DB is always Supabase 1; URL points to Cloudflare R2.
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
    Upload MP3 bytes to Cloudflare R2, then save the public URL
    and metadata to lesson_audio_cache on Supabase 1.

    Returns the public R2 URL.
    Raises RuntimeError on upload or DB failure.
    """
    cache_key = _make_cache_key(grade, subject, chapter, step_title, voice, rate)
    file_path = _make_file_path(grade, subject, chapter, step_title)

    # ── Upload to Cloudflare R2 ────────────────────────────────────────────
    try:
        r2 = _get_r2_client()
        r2.put_object(
            Bucket=BUCKET_NAME,
            Key=file_path,
            Body=mp3_bytes,
            ContentType="audio/mpeg",
        )
    except Exception as exc:
        raise RuntimeError(f"R2 upload failed: {exc}") from exc

    # ── Build public URL ───────────────────────────────────────────────────
    try:
        public_url = _get_r2_public_url(file_path)
    except Exception as exc:
        raise RuntimeError(f"Could not build R2 public URL: {exc}") from exc

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
        storage="Cloudflare R2",
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
