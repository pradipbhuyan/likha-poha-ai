"""
prewarm_lesson_audio.py — Pre-generate TTS audio for all cached lessons.

Usage:
    # POC: Grade 9 English only
    python3 scripts/prewarm_lesson_audio.py --grade "Grade 9" --subject "English"

    # Resume (skip already-cached):
    python3 scripts/prewarm_lesson_audio.py --grade "Grade 9" --subject "English" --resume

    # Full grade (all subjects):
    python3 scripts/prewarm_lesson_audio.py --grade "Grade 9"

Prerequisites:
    1. Create bucket "lesson-audio" in Cloudflare R2 (set to Public)
    2. Add R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_PUBLIC_URL to .env
    3. Run migration: migrations/20260703_lesson_audio_cache.sql
    4. Run from backend/ directory with .env loaded

Real-world measurements (Grade 9 English, en-IN-NeerjaNeural):
    155 lessons × ~1.55 MB avg × ~18.7s avg = ~240 MB, ~48 min wall-clock
    Edge TTS is free — Cloudflare R2 storage is free up to 10 GB (zero egress fees)
"""

import argparse
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.auth_service import admin_client
from app.services.tts_service import generate_speech_file, clean_text_for_tts
from app.services.audio_cache_service import (
    store_audio,
    get_cached_audio_url,
    BUCKET_NAME,
    _get_r2_client,
)

VOICE = "en-IN-NeerjaNeural"
RATE  = "+0%"


def fetch_lessons(grade: str, subject: str | None) -> list[dict]:
    """Fetch all active cached lessons matching the filter."""
    q = (
        admin_client
        .table("lesson_cache")
        .select("grade, subject, chapter, step_title, lesson_content")
        .eq("grade", grade)
        .eq("status", "active")
        .neq("lesson_content", "")
    )
    if subject:
        q = q.ilike("subject", f"%{subject}%")

    r = q.execute()
    return [row for row in (r.data or []) if row.get("lesson_content") and len(row["lesson_content"]) > 100]


def ensure_bucket_exists():
    """Verify R2 credentials and bucket are accessible — exit with instructions if not."""
    account_id    = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key_id = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key    = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    public_url    = os.getenv("R2_PUBLIC_URL", "").strip()

    missing = [k for k, v in {
        "R2_ACCOUNT_ID": account_id,
        "R2_ACCESS_KEY_ID": access_key_id,
        "R2_SECRET_ACCESS_KEY": secret_key,
        "R2_PUBLIC_URL": public_url,
    }.items() if not v]

    if missing:
        print(f"\n❌  Missing R2 environment variables: {', '.join(missing)}")
        print("    Setup steps:")
        print("    1. Go to dash.cloudflare.com → R2 → Create bucket 'lesson-audio'")
        print("    2. Enable public access on the bucket (Settings tab)")
        print("    3. Create R2 API Token with Object Read & Write permission")
        print("    4. Add R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_PUBLIC_URL to .env")
        print("    5. Re-run this script\n")
        sys.exit(1)

    try:
        r2 = _get_r2_client()
        r2.head_bucket(Bucket=BUCKET_NAME)
        print(f"✅  Cloudflare R2 bucket '{BUCKET_NAME}' accessible.")
    except Exception as e:
        print(f"❌  Could not access R2 bucket '{BUCKET_NAME}': {e}")
        print(f"    Make sure the bucket exists in your Cloudflare R2 dashboard.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Pre-warm TTS audio cache")
    parser.add_argument("--grade",   default="Grade 9", help="Grade to prewarm (default: Grade 9)")
    parser.add_argument("--subject", default=None,      help="Subject filter e.g. 'English' (default: all)")
    parser.add_argument("--resume",  action="store_true", help="Skip lessons that already have cached audio")
    parser.add_argument("--limit",   type=int, default=None, help="Max lessons to process (for testing)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Audio Prewarm — {args.grade} / {args.subject or 'All subjects'}")
    print(f"Voice: {VOICE}  Rate: {RATE}  Resume: {args.resume}")
    print(f"{'='*60}\n")

    ensure_bucket_exists()

    lessons = fetch_lessons(args.grade, args.subject)
    if not lessons:
        print("No cached lessons found matching the filter.")
        return

    if args.limit:
        lessons = lessons[:args.limit]

    print(f"Found {len(lessons)} lessons to process.\n")

    success = skip = fail = 0
    total_bytes = 0
    t_start = time.time()

    for i, lesson in enumerate(lessons, 1):
        grade     = lesson["grade"]
        subject   = lesson["subject"]
        chapter   = lesson["chapter"]
        step      = lesson["step_title"]
        content   = lesson["lesson_content"]

        prefix = f"[{i:3d}/{len(lessons)}] {chapter[:35]:<35} / {step:<25}"

        # ── Resume: skip if already cached ────────────────────────────────
        if args.resume:
            existing = get_cached_audio_url(grade, subject, chapter, step, VOICE, RATE)
            if existing:
                print(f"  ⏭  {prefix} (cached)")
                skip += 1
                continue

        # ── Generate TTS ───────────────────────────────────────────────────
        try:
            clean  = clean_text_for_tts(content)
            t0     = time.time()
            mp3_path = generate_speech_file(clean, voice=VOICE, rate=RATE)
            gen_s  = time.time() - t0
            size_b = os.path.getsize(mp3_path)

            with open(mp3_path, "rb") as f:
                mp3_bytes = f.read()
            os.remove(mp3_path)

            # ── Upload + store in DB ───────────────────────────────────────
            url = store_audio(grade, subject, chapter, step, mp3_bytes, VOICE, RATE)

            success    += 1
            total_bytes += size_b
            elapsed     = time.time() - t_start
            remaining   = (len(lessons) - i) * (elapsed / i)

            print(
                f"  ✅ {prefix} "
                f"{size_b/1024:.0f}KB  {gen_s:.0f}s  "
                f"[ETA {remaining/60:.0f}m]"
            )

        except Exception as exc:
            fail += 1
            print(f"  ❌ {prefix}  ERROR: {str(exc)[:80]}")

        # Small pause to avoid hammering Edge TTS
        time.sleep(0.5)

    # ── Summary ────────────────────────────────────────────────────────────
    elapsed_total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Done in {elapsed_total/60:.1f} min")
    print(f"  ✅ Generated & stored : {success}")
    print(f"  ⏭  Skipped (cached)  : {skip}")
    print(f"  ❌ Failed             : {fail}")
    print(f"  Total size uploaded  : {total_bytes/1024/1024:.1f} MB")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
