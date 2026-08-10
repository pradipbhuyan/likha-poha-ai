"""
Teacher Lesson Plan Edit Service
=================================
Per-teacher, private edited copies of lesson plans (teacher_lesson_plan_edits
table — see migrations/20260809_teacher_lesson_plan_edits.sql).

Design principles (mirrors teacher_student_notes' teacher-private pattern in
teacher_classroom.py):
- The system-generated lesson_plan_bank/*.json files on disk are the single
  shared "system version" for every teacher and are NEVER written to by this
  service — editing/saving here only ever touches this DB table.
- A teacher's saved edit is private to that teacher: reads are always scoped
  to teacher_id == the requesting teacher, so Teacher A can never see or
  overwrite Teacher B's edited copy of the same chapter.
- One row per (teacher_id, grade, subject, chapter) — saving again for the
  same chapter overwrites the teacher's own prior edit (upsert), it does not
  keep a growing history. There is deliberately no version history here,
  mirroring the rest of this codebase's lesson-plan feature (which also has
  no edit-history concept) rather than inventing one.
- Reverting to the system version simply deletes the teacher's row.
"""

from __future__ import annotations

import logging

from app.services.auth_service import admin_client

_logger = logging.getLogger("likhapoha.teacher_lesson_plan")

_TABLE = "teacher_lesson_plan_edits"


def get_teacher_edit(teacher_id: str, grade: str, subject: str, chapter: str) -> dict | None:
    """
    Return this teacher's own saved edit for (grade, subject, chapter), or
    None if they haven't saved one (in which case the caller should fall
    back to the shared system-generated bank content).

    Always filters by teacher_id — a teacher can only ever fetch their own
    saved edits through this function.
    """
    try:
        resp = (
            admin_client.table(_TABLE)
            .select("id, lesson_plan_markdown, created_at, updated_at")
            .eq("teacher_id", teacher_id)
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .maybe_single()
            .execute()
        )
        return resp.data or None
    except Exception as exc:
        _logger.warning("get_teacher_edit failed: %s", str(exc)[:200])
        return None


def save_teacher_edit(teacher_id: str, grade: str, subject: str, chapter: str, lesson_plan_markdown: str) -> dict:
    """
    Create or overwrite this teacher's own private edited copy of a lesson
    plan. Upserts on (teacher_id, grade, subject, chapter) — saving again
    for the same chapter replaces the teacher's previous edit, it does not
    keep multiple versions.

    Never touches the system-generated lesson_plan_bank/*.json files.
    """
    markdown = (lesson_plan_markdown or "").strip()
    if not markdown:
        return {"success": False, "error": "Lesson plan content cannot be empty."}

    row = {
        "teacher_id": teacher_id,
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "lesson_plan_markdown": markdown,
    }
    try:
        result = (
            admin_client.table(_TABLE)
            .upsert(row, on_conflict="teacher_id,grade,subject,chapter")
            .execute()
        )
        saved = result.data[0] if result.data else row
        return {"success": True, "edit": saved}
    except Exception as exc:
        _logger.error("save_teacher_edit failed: %s", str(exc)[:200])
        return {"success": False, "error": str(exc)[:200]}


def delete_teacher_edit(teacher_id: str, grade: str, subject: str, chapter: str) -> dict:
    """
    Delete this teacher's own saved edit, reverting them back to the shared
    system-generated version on their next fetch. Scoped to teacher_id so a
    teacher can only ever delete their own edit.
    """
    try:
        (
            admin_client.table(_TABLE)
            .delete()
            .eq("teacher_id", teacher_id)
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .execute()
        )
        return {"success": True}
    except Exception as exc:
        _logger.error("delete_teacher_edit failed: %s", str(exc)[:200])
        return {"success": False, "error": str(exc)[:200]}
