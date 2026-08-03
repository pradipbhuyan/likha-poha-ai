#!/usr/bin/env python3
"""
LikhaPoha AI — Weekly Database Backup Script
=============================================
Exports critical tables to a dated JSON file in /backups/

Run manually:   python3 scripts/backup_db.py
Auto-schedule:  Add to cron (see README comments below)

Cron setup (macOS/Linux):
  1. Open terminal and type: crontab -e
  2. Add this line (runs every Sunday at 2 AM):
     0 2 * * 0 cd /Users/a0247716/Pradips_Project/cbse-tutor-platform/backend && python3 scripts/backup_db.py >> /tmp/likhapoha_backup.log 2>&1
  3. Save and exit
"""

import json
import os
import sys
import datetime
import gzip

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import admin_client as supabase

# ---- Configuration ----
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
MAX_BACKUPS_TO_KEEP = 8  # keep last 8 weekly backups (~2 months)

# Priority 1: CRITICAL — student data, hard to recover
CRITICAL_TABLES = [
    "profiles",
    "families",
    "student_profiles",
    "student_progress",
    "test_history",
    "mentor_memory",
    "doubt_history",
    "weak_area_alerts",
]

# Priority 2: IMPORTANT — content that cost money to generate
CONTENT_TABLES = [
    "rag_documents",
    "rag_chunks",
    "question_bank",
    "doubt_kb",
    "lesson_kb",
    "lesson_cache",
    "rag_visual_assets",
    "syllabus_chapter_overrides",
    "syllabus_subject_overrides",
]

# Priority 3: CONFIG — admin settings
CONFIG_TABLES = [
    "admin_settings",
    "subscription_plan_settings",
    "onboarding_guide_settings",
]

ALL_TABLES = CRITICAL_TABLES + CONTENT_TABLES + CONFIG_TABLES


def fetch_table(table_name: str) -> list:
    """Fetch all rows from a table with pagination to handle large tables."""
    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        try:
            result = (
                supabase
                .table(table_name)
                .select("*")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = result.data or []
            all_rows.extend(rows)

            if len(rows) < page_size:
                break  # last page

            offset += page_size
        except Exception as e:
            print(f"  ⚠️  {table_name}: fetch error at offset {offset} — {e}")
            break

    return all_rows


def run_backup():
    """Main backup function."""
    today = datetime.date.today()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.json.gz"
    filepath = os.path.join(BACKUP_DIR, filename)

    # Create backups directory if needed
    os.makedirs(BACKUP_DIR, exist_ok=True)

    print(f"=" * 55)
    print(f"LikhaPoha AI Database Backup — {today}")
    print(f"=" * 55)
    print()

    backup_data = {
        "_meta": {
            "created_at": datetime.datetime.now().isoformat(),
            "supabase_url": os.getenv("SUPABASE_URL", "unknown"),
            "tables": ALL_TABLES,
        }
    }

    total_rows = 0
    for table in ALL_TABLES:
        priority = "🔴" if table in CRITICAL_TABLES else ("🟡" if table in CONTENT_TABLES else "🔵")
        try:
            rows = fetch_table(table)
            backup_data[table] = rows
            total_rows += len(rows)
            print(f"  {priority} {table}: {len(rows):,} rows")
        except Exception as e:
            backup_data[table] = []
            print(f"  ❌ {table}: FAILED — {e}")

    print()
    print(f"Total rows backed up: {total_rows:,}")

    # Save as compressed JSON
    json_bytes = json.dumps(backup_data, indent=2, default=str).encode("utf-8")
    with gzip.open(filepath, "wb") as f:
        f.write(json_bytes)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"Saved: {filepath}")
    print(f"Size:  {size_kb:.1f} KB (compressed)")

    # Clean up old backups — keep only MAX_BACKUPS_TO_KEEP
    all_backups = sorted([
        f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".json.gz")
    ])

    if len(all_backups) > MAX_BACKUPS_TO_KEEP:
        to_delete = all_backups[:-MAX_BACKUPS_TO_KEEP]
        for old_file in to_delete:
            os.remove(os.path.join(BACKUP_DIR, old_file))
            print(f"Deleted old backup: {old_file}")

    print()
    print(f"✅ Backup complete — {len(all_backups)} weekly backup(s) stored")
    print(f"=" * 55)

    return filepath


if __name__ == "__main__":
    run_backup()
