"""
migrate_sqlite_to_supabase.py — one-time move of the campaign's send-state
from the local SQLite file (campaign_state.db) into Supabase, so the admin
console (Admin Control -> School Outreach) can read/filter/select principals
and trigger sends, instead of a script-local file only this machine can see.

Safe to re-run: upserts on email, so partial failures or a second run never
duplicate rows or clobber progress already recorded in Supabase.

Usage:
    cd backend
    .venv/bin/python scripts/school_outreach/migrate_sqlite_to_supabase.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.services.auth_service import admin_client  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(__file__), "campaign_state.db")
BATCH_SIZE = 500


def main() -> None:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"No local campaign_state.db found at {DB_PATH} — nothing to migrate.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM principals ORDER BY rowid").fetchall()
    conn.close()

    print(f"Read {len(rows)} rows from SQLite.")
    if not rows:
        return

    migrated = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i:i + BATCH_SIZE]
        payload = [
            {
                "email": r["email"],
                "principal_name": r["principal_name"],
                "school_name": r["school_name"],
                "district": r["district"],
                "state": r["state"],
                "aff_no": r["aff_no"],
                "status": r["status"],
                "resend_id": r["resend_id"],
                "error": r["error"],
                "attempts": r["attempts"],
                "sent_at": r["sent_at"],
                "reminder_sent_at": r["reminder_sent_at"] if "reminder_sent_at" in r.keys() else None,
                "responded": bool(r["responded"]) if "responded" in r.keys() else False,
                "responded_at": r["responded_at"] if "responded_at" in r.keys() else None,
            }
            for r in chunk
        ]
        admin_client.table("school_outreach_principals").upsert(payload, on_conflict="email").execute()
        migrated += len(chunk)
        print(f"  migrated {migrated}/{len(rows)}")

    print("Done.")


if __name__ == "__main__":
    main()
