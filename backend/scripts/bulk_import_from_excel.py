"""
bulk_import_from_excel.py
─────────────────────────────────────────────────────────────────────────────
Reads a filled-in copy of the roster template (see
generate_bulk_import_template.py) and bulk-creates the teacher and student
accounts it describes, linked to one school.

Column headers are read via app.services.bulk_import_service.TEACHER_COLUMNS
/ STUDENT_COLUMNS — the same mapping the template generator writes — so the
two scripts can never drift out of sync.

Teachers are imported before students, so a student row's "Assigned Teacher
Email" can resolve against a teacher created moments earlier in the same run.

Safe by default: without --confirm this only validates and prints a preview,
no accounts are created. Real account creation always requires --confirm.

Usage:
    cd backend
    .venv/bin/python scripts/bulk_import_from_excel.py --file roster.xlsx --school-code TES-KJFC0
    .venv/bin/python scripts/bulk_import_from_excel.py --file roster.xlsx --school-code TES-KJFC0 --confirm
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd  # noqa: E402

from app.services import bulk_import_service as svc  # noqa: E402
from app.services.auth_service import admin_client  # noqa: E402


def _read_sheet(path: str, sheet_name: str, columns: dict) -> list[dict]:
    df = pd.read_excel(path, sheet_name=sheet_name, dtype=str).fillna("")
    rows = []
    for _, series in df.iterrows():
        row = {}
        for header, key in columns.items():
            row[key] = (series.get(header) or "").strip()
        if any(row.values()):  # skip fully-blank rows
            rows.append(row)
    return rows


def _resolve_school_id(school_code: str) -> str:
    resp = (
        admin_client.table("schools")
        .select("id, name")
        .eq("school_code", school_code.strip().upper())
        .limit(1)
        .execute()
    )
    school = (resp.data or [None])[0]
    if not school:
        raise SystemExit(f"No school found for school_code={school_code}")
    print(f"Target school: {school['name']} ({school['id']})")
    return school["id"]


def _print_errors(label: str, validation_errors: list[dict]) -> None:
    if not validation_errors:
        return
    print(f"\n{label}: {len(validation_errors)} row(s) have errors — fix these before re-running:")
    for e in validation_errors[:20]:
        print(f"  row {e['row']}: {', '.join(e['issues'])}")


def _write_results_csv(out_dir: str, teacher_results: list[dict], student_results: list[dict]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(out_dir, f"bulk_import_results_{timestamp}.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "row", "name", "username", "email", "success", "temp_password", "error", "teacher_link"])
        for r in teacher_results:
            writer.writerow(["teacher", r["row"], r.get("name", ""), r.get("username", ""), r.get("email", ""),
                              r["success"], r.get("temp_password", ""), r.get("error", ""), ""])
        for r in student_results:
            writer.writerow(["student", r["row"], r.get("name", ""), r.get("username", ""), r.get("email", ""),
                              r["success"], r.get("temp_password", ""), r.get("error", ""), r.get("teacher_link", "")])
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to the filled-in roster .xlsx")
    parser.add_argument("--school-code", required=True, help="The school's join code (e.g. TES-KJFC0)")
    parser.add_argument("--confirm", action="store_true", help="Actually create accounts (default is preview-only)")
    parser.add_argument("--out-dir", default=os.path.dirname(__file__), help="Where to write the results CSV")
    args = parser.parse_args()

    school_id = _resolve_school_id(args.school_code)

    teacher_rows = _read_sheet(args.file, "Teachers", svc.TEACHER_COLUMNS)
    student_rows = _read_sheet(args.file, "Students", svc.STUDENT_COLUMNS)
    print(f"Parsed {len(teacher_rows)} teacher row(s), {len(student_rows)} student row(s).")

    teacher_preview, teacher_errors = svc.validate_teacher_rows(teacher_rows)
    student_preview, student_errors = svc.validate_student_rows(student_rows)
    _print_errors("Teachers", teacher_errors)
    _print_errors("Students", student_errors)

    if teacher_errors or student_errors:
        print("\nFix the row(s) above and re-run. Nothing was created.")
        return

    if not args.confirm:
        print(f"\nPreview only — {len(teacher_preview)} teacher(s) and {len(student_preview)} student(s) "
              "look valid. Re-run with --confirm to actually create these accounts.")
        return

    print("\nCreating teacher accounts...")
    teacher_outcome = svc.import_teachers(teacher_rows, school_id=school_id)
    print(f"  {teacher_outcome['created']} created, {teacher_outcome['failed']} failed")

    print("Creating student accounts...")
    student_outcome = svc.import_students(student_rows, school_id=school_id)
    print(f"  {student_outcome['created']} created, {student_outcome['failed']} failed")

    out_path = _write_results_csv(args.out_dir, teacher_outcome["results"], student_outcome["results"])
    print(f"\nResults (including one-time temp passwords) written to: {out_path}")
    print("Store this file securely and delete it once passwords are shared — it is not encrypted.")


if __name__ == "__main__":
    main()
