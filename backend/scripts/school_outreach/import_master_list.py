"""
import_master_list.py — clean the CBSE principals spreadsheet into a local
staging DB (step 1 of 2 for getting a fresh export into Supabase).

Campaign state now lives in Supabase (school_outreach_principals — see the
admin console, Admin Control -> School Outreach), not this file. This script
still exists as the spreadsheet-cleaning step: dedupe, validate email format,
strip missing rows. After running this, run migrate_sqlite_to_supabase.py to
push the cleaned rows into Supabase (upsert-based — never disturbs a row
that's already sent/failed/pending there).

Safe to re-run against a refreshed spreadsheet export: emails already in this
local DB are left untouched, only genuinely new rows are added as 'pending'.

Usage:
    cd backend
    .venv/bin/python scripts/school_outreach/import_master_list.py \\
        --xlsx ~/Downloads/Cbse_Schools_Database_198177009900.xlsx
    .venv/bin/python scripts/school_outreach/migrate_sqlite_to_supabase.py
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3

import pandas as pd

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_STAGING_DB_PATH = os.path.join(os.path.dirname(__file__), "campaign_state.db")


def _get_staging_connection() -> sqlite3.Connection:
    """
    Minimal local staging table — just enough to dedupe/hold cleaned rows
    before migrate_sqlite_to_supabase.py pushes them on. Send-state tracking
    (status/reminders/responses) lives in Supabase now, not here.
    """
    conn = sqlite3.connect(_STAGING_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS principals (
            email          TEXT PRIMARY KEY,
            principal_name TEXT NOT NULL DEFAULT '',
            school_name    TEXT NOT NULL DEFAULT '',
            district       TEXT NOT NULL DEFAULT '',
            state          TEXT NOT NULL DEFAULT '',
            aff_no         TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'pending',
            resend_id      TEXT NOT NULL DEFAULT '',
            error          TEXT NOT NULL DEFAULT '',
            attempts       INTEGER NOT NULL DEFAULT 0,
            sent_at        TEXT,
            reminder_sent_at TEXT,
            responded        INTEGER NOT NULL DEFAULT 0,
            responded_at     TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _upsert_rows(conn: sqlite3.Connection, rows: list[dict]) -> tuple[int, int]:
    """Insert new rows as 'pending'; existing emails are left untouched. Returns (inserted, skipped)."""
    inserted = 0
    for row in rows:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO principals
                (email, principal_name, school_name, district, state, aff_no, status)
            VALUES (:email, :principal_name, :school_name, :district, :state, :aff_no, :status)
            """,
            row,
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted, len(rows) - inserted


def _staging_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM principals GROUP BY status").fetchall()
    counts = {r["status"]: r["n"] for r in rows}
    return {"total": sum(counts.values()), **counts}


def clean_rows(xlsx_path: str) -> tuple[list[dict], dict]:
    df = pd.read_excel(xlsx_path)

    required = {"Email", "Principal/Head of School", "School Name"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Spreadsheet is missing expected column(s): {missing}")

    report = {"total_rows": len(df), "missing_email": 0, "invalid_email": 0, "duplicate_email": 0}
    seen_emails: set[str] = set()
    rows: list[dict] = []

    for _, r in df.iterrows():
        raw_email = r.get("Email")
        if pd.isna(raw_email):
            report["missing_email"] += 1
            continue
        email = str(raw_email).strip().lower()
        if not _EMAIL_RE.match(email):
            report["invalid_email"] += 1
            continue
        if email in seen_emails:
            report["duplicate_email"] += 1
            continue
        seen_emails.add(email)

        rows.append({
            "email": email,
            "principal_name": str(r.get("Principal/Head of School") or "").strip(),
            "school_name": str(r.get("School Name") or "").strip(),
            "district": str(r.get("District") or "").strip(),
            "state": str(r.get("State") or "").strip(),
            "aff_no": str(r.get("Aff No") or "").strip(),
            "status": "pending",
        })

    return rows, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", required=True, help="Path to the CBSE schools spreadsheet")
    args = parser.parse_args()

    xlsx_path = os.path.expanduser(args.xlsx)
    if not os.path.exists(xlsx_path):
        raise SystemExit(f"File not found: {xlsx_path}")

    rows, report = clean_rows(xlsx_path)

    conn = _get_staging_connection()
    inserted, skipped = _upsert_rows(conn, rows)

    print(f"Spreadsheet rows:        {report['total_rows']}")
    print(f"  missing email:         {report['missing_email']}")
    print(f"  invalid email format:  {report['invalid_email']}")
    print(f"  duplicate email:       {report['duplicate_email']}")
    print(f"Clean rows processed:    {len(rows)}")
    print(f"  newly inserted:        {inserted}")
    print(f"  already in DB:         {skipped}")
    print()
    print("Local staging DB state:", _staging_stats(conn))
    print("Next: .venv/bin/python scripts/school_outreach/migrate_sqlite_to_supabase.py")


if __name__ == "__main__":
    main()
