"""
cleanup_audio_storage.py
─────────────────────────────────────────────────────────────────────────────
Cleans up the Supabase Storage 'lesson-audio' bucket to recover the 2.32 GB
quota being consumed.

The audio bucket stores pre-generated TTS MP3 files. They are large (~240 MB
per grade) but can be regenerated at any time using the "Build Audio Cache"
button in the Admin Cache & Question Bank page.

MODES:
  --analyze          Show bucket usage by grade (no deletions). Run first.
  --delete-grade X   Delete all audio files for a specific grade (e.g. "grade-9")
  --delete-all       Delete ALL audio files from the bucket (nuclear option)
  --mark-archived    After deletion, mark lesson_audio_cache rows as archived

USAGE:
  cd backend
  python scripts/cleanup_audio_storage.py --analyze
  python scripts/cleanup_audio_storage.py --delete-grade grade-9 --mark-archived
  python scripts/cleanup_audio_storage.py --delete-all --mark-archived

SAFETY:
  - Dry run by default unless --confirm flag is added
  - Audio files can always be regenerated — no permanent data loss
  - Only affects audio cache; lessons, questions, and student data are untouched

─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.ssl_service import enable_system_truststore
enable_system_truststore()

import supabase as sb

# The lesson-audio bucket lives on Supabase 2 (Grade 11/12 project).
# Falls back to main Supabase if Grade 11/12 keys are not set.
SUPABASE_URL = (
    os.environ.get("SUPABASE_GRADE_1112_URL")
    or os.environ.get("SUPABASE_URL")
    or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
)
SUPABASE_SERVICE_KEY = (
    os.environ.get("SUPABASE_GRADE_1112_SERVICE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env")
    print("   Need: SUPABASE_GRADE_1112_URL + SUPABASE_GRADE_1112_SERVICE_KEY")
    sys.exit(1)

print(f"🔗 Connecting to: {SUPABASE_URL[:40]}...")

BUCKET = "lesson-audio"


def get_client():
    return sb.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def list_all_files(client, prefix="", limit=1000):
    """Recursively list all files under a prefix in the bucket."""
    files = []
    try:
        result = client.storage.from_(BUCKET).list(prefix, {"limit": limit, "offset": 0})
        for item in result:
            if item.get("id") is None:
                # It's a folder — recurse
                sub_prefix = f"{prefix}/{item['name']}" if prefix else item["name"]
                files.extend(list_all_files(client, sub_prefix, limit))
            else:
                # It's a file
                file_path = f"{prefix}/{item['name']}" if prefix else item["name"]
                files.append({
                    "path": file_path,
                    "name": item["name"],
                    "size": item.get("metadata", {}).get("size", 0) if item.get("metadata") else 0,
                    "updated_at": item.get("updated_at", ""),
                })
    except Exception as e:
        print(f"  Warning: could not list '{prefix}': {e}")
    return files


def analyze(client):
    """Show storage usage breakdown by grade folder."""
    print("\n📊 Analyzing Supabase Storage bucket: lesson-audio")
    print("=" * 60)
    print("Listing files… (this may take 10-30 seconds for large buckets)\n")

    files = list_all_files(client)
    if not files:
        print("  No files found in bucket — bucket may be empty or inaccessible.")
        return

    # Group by top-level folder (grade)
    by_grade = defaultdict(lambda: {"count": 0, "size": 0})
    total_size = 0
    total_files = 0

    for f in files:
        parts = f["path"].split("/")
        grade_folder = parts[0] if parts else "unknown"
        by_grade[grade_folder]["count"] += 1
        by_grade[grade_folder]["size"] += f["size"]
        total_size += f["size"]
        total_files += 1

    print(f"{'Grade Folder':<25} {'Files':>8} {'Size':>12}")
    print("-" * 50)
    for grade, info in sorted(by_grade.items()):
        size_mb = info["size"] / (1024 * 1024)
        print(f"{grade:<25} {info['count']:>8,} {size_mb:>10.1f} MB")

    print("-" * 50)
    total_mb = total_size / (1024 * 1024)
    total_gb = total_mb / 1024
    print(f"{'TOTAL':<25} {total_files:>8,} {total_mb:>10.1f} MB  ({total_gb:.2f} GB)")
    print()

    if total_gb > 1.0:
        print(f"⚠️  Storage exceeds 1 GB free-tier limit. Consider deleting grade folders.")
        print(f"   To delete a specific grade:  --delete-grade <folder-name>")
        print(f"   To delete everything:        --delete-all")
    else:
        print("✅ Storage is within free-tier limits.")

    return files


def delete_grade_folder(client, grade_slug: str, confirm: bool, mark_archived: bool):
    """Delete all audio files for a specific grade slug (e.g. 'grade-9')."""
    print(f"\n🗑️  Preparing to delete audio files for: {grade_slug}")
    files = list_all_files(client, prefix=grade_slug)

    if not files:
        print(f"  No files found under '{grade_slug}/' — nothing to delete.")
        return

    total_size = sum(f["size"] for f in files)
    total_mb = total_size / (1024 * 1024)
    print(f"  Found {len(files):,} files  ({total_mb:.1f} MB)")

    if not confirm:
        print("\n  DRY RUN — no files deleted. Add --confirm to actually delete.")
        return

    print(f"\n  Deleting {len(files):,} files…")
    paths = [f["path"] for f in files]

    # Delete in batches of 100
    deleted = 0
    failed = 0
    for i in range(0, len(paths), 100):
        batch = paths[i:i+100]
        try:
            client.storage.from_(BUCKET).remove(batch)
            deleted += len(batch)
            print(f"  Deleted batch {i//100 + 1}: {deleted}/{len(paths)} files")
        except Exception as e:
            failed += len(batch)
            print(f"  ⚠️  Batch {i//100 + 1} failed: {e}")

    print(f"\n  ✅ Deleted {deleted} files  |  ❌ Failed {failed} files")
    print(f"  Freed ~{total_mb:.1f} MB from Supabase Storage")

    if mark_archived:
        _mark_archived_in_db(grade_slug)


def delete_all(client, confirm: bool, mark_archived: bool):
    """Delete ALL audio files from the bucket."""
    print("\n☢️  NUCLEAR OPTION: Delete ALL audio files from lesson-audio bucket")
    files = list_all_files(client)

    if not files:
        print("  Bucket is already empty.")
        return

    total_size = sum(f["size"] for f in files)
    total_gb = total_size / (1024 ** 3)
    print(f"  Found {len(files):,} files  ({total_gb:.2f} GB)")
    print("  All audio can be regenerated via Admin → Cache & Question Bank → Build Audio Cache")

    if not confirm:
        print("\n  DRY RUN — no files deleted. Add --confirm to actually delete.")
        return

    paths = [f["path"] for f in files]
    deleted = 0
    failed = 0
    for i in range(0, len(paths), 100):
        batch = paths[i:i+100]
        try:
            client.storage.from_(BUCKET).remove(batch)
            deleted += len(batch)
        except Exception as e:
            failed += len(batch)
            print(f"  ⚠️  Batch {i//100 + 1} failed: {e}")

    print(f"\n  ✅ Deleted {deleted} files  |  ❌ Failed {failed} files")
    print(f"  Freed ~{total_gb:.2f} GB from Supabase Storage")

    if mark_archived:
        _mark_archived_in_db(None)


def _mark_archived_in_db(grade_slug):
    """Mark lesson_audio_cache rows as archived after Storage deletion."""
    try:
        from app.services.grade_db_router import get_content_db

        # Map grade slug → grade label
        grade_map = {
            f"grade-{i}": f"Grade {i}" for i in range(1, 13)
        }

        if grade_slug:
            grade_label = grade_map.get(grade_slug)
            if not grade_label:
                print(f"  ⚠️  Could not map '{grade_slug}' to grade label — skipping DB update")
                return
            grades_to_archive = [grade_label]
        else:
            grades_to_archive = list(grade_map.values())

        for grade_label in grades_to_archive:
            try:
                db = get_content_db(grade_label)
                result = db.table("lesson_audio_cache") \
                    .update({"status": "archived"}) \
                    .eq("grade", grade_label) \
                    .eq("status", "active") \
                    .execute()
                count = len(result.data) if result.data else 0
                print(f"  DB: Marked {count} rows as archived for {grade_label}")
            except Exception as e:
                print(f"  ⚠️  Could not update DB for {grade_label}: {e}")
    except ImportError:
        print("  ⚠️  Could not import DB router — run DB update manually:")
        if grade_slug:
            grade_label = f"Grade {grade_slug.replace('grade-', '').title()}"
            print(f"  SQL: UPDATE lesson_audio_cache SET status='archived' WHERE grade='{grade_label}';")
        else:
            print("  SQL: UPDATE lesson_audio_cache SET status='archived';")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Supabase Storage lesson-audio bucket"
    )
    parser.add_argument("--analyze", action="store_true", help="Show storage usage (read-only)")
    parser.add_argument("--delete-grade", metavar="SLUG", help="Delete audio for one grade (e.g. grade-9)")
    parser.add_argument("--delete-all", action="store_true", help="Delete ALL audio files")
    parser.add_argument("--confirm", action="store_true", help="Actually perform deletions (default: dry run)")
    parser.add_argument("--mark-archived", action="store_true", help="Mark DB rows as archived after deletion")
    args = parser.parse_args()

    if not any([args.analyze, args.delete_grade, args.delete_all]):
        parser.print_help()
        print("\n💡 Tip: Start with --analyze to see what's using space.")
        sys.exit(0)

    client = get_client()

    if args.analyze:
        analyze(client)

    if args.delete_grade:
        delete_grade_folder(client, args.delete_grade, args.confirm, args.mark_archived)

    if args.delete_all:
        delete_all(client, args.confirm, args.mark_archived)

    if (args.delete_grade or args.delete_all) and not args.confirm:
        print("\n" + "=" * 60)
        print("DRY RUN complete. To actually delete, add --confirm:")
        if args.delete_grade:
            print(f"  python scripts/cleanup_audio_storage.py --delete-grade {args.delete_grade} --confirm --mark-archived")
        else:
            print("  python scripts/cleanup_audio_storage.py --delete-all --confirm --mark-archived")


if __name__ == "__main__":
    main()
