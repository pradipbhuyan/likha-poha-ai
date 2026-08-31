"""
generate_bulk_import_template.py
─────────────────────────────────────────────────────────────────────────────
Generates the Excel roster template principals/teachers fill out to bulk-
enroll their school. Column headers come from
app.services.bulk_import_service.TEACHER_COLUMNS / STUDENT_COLUMNS — the
same mapping scripts/bulk_import_from_excel.py reads back, so the template
and the importer can never drift out of sync with each other.

Usage:
    cd backend
    .venv/bin/python scripts/generate_bulk_import_template.py [output_path.xlsx]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import xlsxwriter  # noqa: E402

from app.services.bulk_import_service import (  # noqa: E402
    GRADE_OPTIONS,
    STREAM_OPTIONS,
    STUDENT_COLUMNS,
    TEACHER_COLUMNS,
)

DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "LikhaPoha_School_Roster_Template.xlsx")


def _write_sheet(workbook, sheet_name: str, headers: list[str], header_fmt, num_blank_rows: int = 60) -> None:
    sheet = workbook.add_worksheet(sheet_name)
    for col, header in enumerate(headers):
        sheet.write(0, col, header, header_fmt)
        sheet.set_column(col, col, max(18, min(60, len(header) + 4)))
    sheet.freeze_panes(1, 0)
    return sheet


def build(output_path: str) -> None:
    workbook = xlsxwriter.Workbook(output_path)

    title_fmt = workbook.add_format({"bold": True, "font_size": 14, "font_color": "#4338ca"})
    body_fmt = workbook.add_format({"font_size": 11, "text_wrap": True, "valign": "top"})
    header_fmt = workbook.add_format({
        "bold": True, "bg_color": "#eef2ff", "font_color": "#312e81",
        "border": 1, "valign": "vcenter", "text_wrap": True,
    })

    # ── Instructions ─────────────────────────────────────────────────────────
    instructions = workbook.add_worksheet("Instructions")
    instructions.set_column(0, 0, 90)
    instructions.write(0, 0, "Likha Poha AI — School Roster Template", title_fmt)
    instructions.write(2, 0, (
        "1. Fill in the \"Teachers\" sheet first — one row per teacher.\n"
        "2. Then fill in the \"Students\" sheet — one row per student.\n"
        "3. Grade must be picked from the dropdown (Grade 5 to Grade 12).\n"
        "4. Stream is required ONLY for Grade 11 and Grade 12 — pick PCM, PCB, PCMB, "
        "Commerce, or Humanities from the dropdown. It's what determines the right "
        "subjects for that student, so 11th/12th rows without a stream will be "
        "rejected. Leave it blank for Grade 5-10.\n"
        "5. \"Assigned Teacher Email\" on the Students sheet is optional — if filled in, "
        "it must exactly match an email you entered on the Teachers sheet, and that "
        "student will show up under that teacher's roster.\n"
        "6. Email is optional for students (some may not have one yet) but required "
        "for teachers, since they need it to log in.\n"
        "7. Leave \"Temporary Password\" blank to have one generated automatically — "
        "you'll receive it back after the import so you can share it with each "
        "person securely.\n"
        "8. Send the completed file back to us — we'll run the import and confirm "
        "once everyone is set up."
    ), body_fmt)

    # ── Teachers ─────────────────────────────────────────────────────────────
    teacher_headers = list(TEACHER_COLUMNS.keys())
    _write_sheet(workbook, "Teachers", teacher_headers, header_fmt)

    # ── Students ─────────────────────────────────────────────────────────────
    student_headers = list(STUDENT_COLUMNS.keys())
    student_sheet = _write_sheet(workbook, "Students", student_headers, header_fmt)
    grade_col = student_headers.index("Grade")
    student_sheet.data_validation(1, grade_col, 500, grade_col, {
        "validate": "list",
        "source": GRADE_OPTIONS,
        "error_message": "Please pick a grade from the dropdown (Grade 5 to Grade 12).",
    })

    stream_col = next(i for i, h in enumerate(student_headers) if h.startswith("Stream"))
    student_sheet.data_validation(1, stream_col, 500, stream_col, {
        "validate": "list",
        "source": STREAM_OPTIONS,
        "error_message": "Required for Grade 11/12 only — pick PCM, PCB, PCMB, Commerce, or Humanities.",
    })

    workbook.close()
    print(f"Wrote template to {output_path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    build(out)
