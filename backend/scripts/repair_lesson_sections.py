"""
repair_lesson_sections.py — CLI for Admin Lesson Repair
─────────────────────────────────────────────────────────────────────────────
Reads the latest lesson_sections audit report and creates repair jobs.
LLM repair is opt-in only (--use-llm flag).

CLI:
  cd backend
  .venv/bin/python scripts/repair_lesson_sections.py --sample
  .venv/bin/python scripts/repair_lesson_sections.py --grade 9 --subject Science
  .venv/bin/python scripts/repair_lesson_sections.py --all --use-llm
  .venv/bin/python scripts/repair_lesson_sections.py --validate-only

Safety:
  - Never overwrites published lesson content automatically
  - LLM repair requires explicit --use-llm flag
  - Prints cost warning before running LLM
  - All repairs stored as drafts in lesson_repair_tasks
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("repair_lesson_sections")

REPORT_DIR = Path("reports/lesson_sections")


def _print_separator(char: str = "=", width: int = 60) -> None:
    print(char * width)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lesson Repair CLI — reads audit report and creates/runs repair tasks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Repair a sample of 10 failed lessons (no LLM — creates tasks for review)
  .venv/bin/python scripts/repair_lesson_sections.py --sample

  # Repair all failed Grade 9 Science lessons using LLM
  .venv/bin/python scripts/repair_lesson_sections.py --grade 9 --subject Science --use-llm

  # Validate a specific repaired draft JSON file
  .venv/bin/python scripts/repair_lesson_sections.py --validate-only --draft-file /path/to/draft.json

  # Show failed lessons from latest report without repairing
  .venv/bin/python scripts/repair_lesson_sections.py --list-failures
        """,
    )
    parser.add_argument("--sample", action="store_true", help="Repair a sample of 10 failed lessons")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Repair ALL failed lessons")
    parser.add_argument("--grade", help="Filter by grade, e.g. 9 or 'Grade 9'")
    parser.add_argument("--subject", help="Filter by subject, e.g. Science")
    parser.add_argument("--chapter", help="Filter by chapter name")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM to generate repaired content (costs money)")
    parser.add_argument("--validate-only", action="store_true", help="Validate a draft JSON file without LLM")
    parser.add_argument("--draft-file", help="Path to repaired draft JSON file for --validate-only")
    parser.add_argument("--list-failures", action="store_true", help="List failed lessons without repairing")
    parser.add_argument("--admin-id", default="cli-admin", help="Admin identifier for audit trail")
    args = parser.parse_args()

    from app.services.lesson_repair_service import (
        extract_failed_lessons,
        load_latest_audit_report,
        run_repair_job,
        validate_repaired_draft,
        _db_insert_job,
        _db_list_jobs,
    )

    # ── Validate-only mode ──────────────────────────────────────────────────
    if args.validate_only:
        if not args.draft_file:
            print("ERROR: --validate-only requires --draft-file <path>")
            sys.exit(1)
        fp = Path(args.draft_file)
        if not fp.exists():
            print(f"ERROR: Draft file not found: {fp}")
            sys.exit(1)
        try:
            draft = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: Could not parse JSON: {e}")
            sys.exit(1)
        result = validate_repaired_draft(draft)
        _print_separator()
        print("VALIDATION RESULT")
        _print_separator("-")
        print(f"Valid:              {'YES ✓' if result['valid'] else 'NO ✗'}")
        print(f"Overall score:      {result['overall_score']}/100")
        print(f"Depth score:        {result['depth_score']}/100")
        print(f"Section compliance: {result['section_compliance']}%")
        print(f"Critical issues:    {result['critical_count']}")
        print(f"Missing sections:   {result['missing_sections']}")
        if result['issues']:
            print("\nIssues:")
            for issue in result['issues']:
                sev = issue.get('severity', '?').upper()
                print(f"  [{sev}] {issue.get('section', '?')}: {issue.get('issue', '')}")
        _print_separator()
        sys.exit(0 if result['valid'] else 1)

    # ── Load audit report ───────────────────────────────────────────────────
    report = load_latest_audit_report()
    if not report:
        print("ERROR: No lesson_sections audit report found.")
        print("Run: .venv/bin/python scripts/audit_lesson_sections.py --sample")
        sys.exit(1)

    # Normalise grade
    grade = args.grade
    if grade and not grade.startswith("Grade "):
        grade = "Grade " + grade

    # ── List failures mode ──────────────────────────────────────────────────
    is_sample = args.sample and not args.run_all
    failed = extract_failed_lessons(
        report,
        grade=grade,
        subject=args.subject,
        chapter=args.chapter,
        sample=is_sample,
        sample_size=10,
    )

    if args.list_failures or not (args.sample or args.run_all or grade or args.subject):
        _print_separator()
        print(f"FAILED LESSONS ({len(failed)} found)")
        _print_separator("-")
        for i, lesson in enumerate(failed[:50], 1):
            scores = lesson.get("scores", {})
            counts = lesson.get("issue_counts", {})
            print(
                f"{i:3}. [{lesson.get('grade', '?')}] {lesson.get('subject', '?')} "
                f"| {lesson.get('chapter', '?')} | {lesson.get('step_title', '?')}"
            )
            print(
                f"     Score: {scores.get('overall_lesson_score', '?')}/100  "
                f"Critical: {counts.get('critical', 0)}  High: {counts.get('high', 0)}"
            )
        _print_separator()
        print("Use --sample, --all, --grade, or --subject to run repairs.")
        sys.exit(0)

    if not failed:
        print("No failed lessons found matching the given filters.")
        sys.exit(0)

    # ── LLM cost warning ────────────────────────────────────────────────────
    if args.use_llm:
        _print_separator("!")
        print("⚠  LLM REPAIR ENABLED — THIS WILL INCUR AI TOKEN COSTS")
        print(f"   Lessons to repair: {len(failed)}")
        print("   Estimated cost: ~$0.01–$0.05 per lesson depending on model")
        print("   Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        _print_separator("!")
        import time
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

    # ── Create and run repair job ───────────────────────────────────────────
    job_id = str(uuid.uuid4())
    mode = "sample" if is_sample else ("filtered" if (grade or args.subject or args.chapter) else "all")
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "id": job_id,
        "requested_by_admin_id": args.admin_id,
        "status": "queued",
        "mode": mode,
        "grade": grade,
        "subject": args.subject,
        "chapter": args.chapter,
        "use_llm": args.use_llm,
        "total_tasks": len(failed),
        "completed_tasks": 0,
        "failed_tasks": 0,
        "approved_tasks": 0,
        "published_tasks": 0,
        "created_at": now,
        "updated_at": now,
    }

    _db_insert_job(job)
    jobs_mem: dict = {job_id: job}
    tasks_mem: dict = {}

    _print_separator()
    print(f"STARTING REPAIR JOB: {job_id}")
    print(f"Mode: {mode} | Grade: {grade or 'all'} | Subject: {args.subject or 'all'}")
    print(f"Tasks: {len(failed)} | LLM: {'YES' if args.use_llm else 'NO'}")
    _print_separator()

    # Run synchronously (CLI mode — no background thread)
    run_repair_job(
        job_id=job_id,
        admin_id=args.admin_id,
        mode=mode,
        use_llm=args.use_llm,
        grade=grade,
        subject=args.subject,
        chapter=args.chapter,
        in_memory_jobs=jobs_mem,
        in_memory_tasks=tasks_mem,
    )

    # ── Print results ───────────────────────────────────────────────────────
    final_job = jobs_mem.get(job_id, {})
    _print_separator()
    print("REPAIR JOB COMPLETE")
    _print_separator("-")
    print(f"Job ID:    {job_id}")
    print(f"Status:    {final_job.get('status', '?')}")
    print(f"Total:     {final_job.get('total_tasks', 0)}")
    print(f"Completed: {final_job.get('completed_tasks', 0)}")
    print(f"Failed:    {final_job.get('failed_tasks', 0)}")

    all_tasks = list(tasks_mem.values())
    ready = [t for t in all_tasks if t.get("status") == "ready_for_review"]
    val_failed = [t for t in all_tasks if t.get("status") == "validation_failed"]
    task_failed = [t for t in all_tasks if t.get("status") == "failed"]

    print(f"\nReady for review:   {len(ready)}")
    print(f"Validation failed:  {len(val_failed)}")
    print(f"Task failed:        {len(task_failed)}")

    if task_failed:
        print("\nFailed tasks:")
        for t in task_failed[:5]:
            print(f"  {t.get('grade')} | {t.get('subject')} | {t.get('step_title')}")
            print(f"  Error: {t.get('error_message', '')[:120]}")

    if final_job.get("error_summary"):
        print(f"\nJob error: {final_job.get('error_summary')}")

    _print_separator()
    if ready:
        print(f"\n{len(ready)} tasks are ready for admin review.")
        print("Use the Admin UI (QA Center → Lesson Repair) to approve and publish.")
    _print_separator()

    sys.exit(0 if final_job.get("status") == "completed" else 1)


if __name__ == "__main__":
    main()
