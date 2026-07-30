#!/usr/bin/env python3
"""
Ingest GPT-5.5 Chapter Output
================================
See docs/GPT55_CHAPTER_AUTHORING_PROMPT.md for the full workflow this
script completes.

Takes the JSON output produced by pasting the GPT-5.5 chapter-authoring
prompt into a GPT-5.5 chat session, validates it against the expected
schema, and:
  1. Writes the "manifest" object to
     backend/app/data/chapter_manifests/<grade_slug>/<subject_slug>/<chapter_slug>.json
  2. Seeds all 5 "lessons" entries directly into Supabase lesson_cache
     via store_lesson_cache() with source_type="MANUAL" (bypassing live
     LLM generation entirely for this chapter).
  3. Automatically re-runs the Tier A chapter-boundary audit for this
     exact grade/subject/chapter and prints the result, so the user
     immediately knows if the GPT-5.5 output passed cleanly or needs
     another round.

Usage:
    cd backend
    python3 scripts/ingest_gpt55_chapter_output.py --input gpt_output/grade9_science_cell.json --dry-run
    python3 scripts/ingest_gpt55_chapter_output.py --input gpt_output/grade9_science_cell.json --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

MANIFEST_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "chapter_manifests"

REQUIRED_MANIFEST_KEYS = [
    "grade", "subject", "chapter", "central_question", "in_scope_units",
    "banned_topics", "must_include_keywords", "known_pitfalls",
    "recommended_example_progression",
]

REQUIRED_LESSON_STEPS = [
    "Concept introduction", "Core explanation", "Worked examples",
    "Exam-style problems", "Revision and recap",
]

# Two accepted heading sets — English (default) and Hindi (used for Hindi
# chapters, see scripts/prepare_gpt55_prompts.py HEADING_SETS["hi"]). A
# lesson step's headings are validated against whichever set it actually
# matches best, so Hindi chapters authored with Hindi headings aren't
# incorrectly flagged as missing all 7 English headings.
REQUIRED_LESSON_HEADINGS_EN = [
    "## What you will learn",
    "## Simple explanation",
    "## Step-by-step breakdown",
    "## Worked example",
    "## Common mistake",
    "## Quick check question",
    "## Summary",
]

REQUIRED_LESSON_HEADINGS_HI = [
    "## आप क्या सीखेंगे",
    "## सरल व्याख्या",
    "## चरण-दर-चरण विवरण",
    "## हल किया गया उदाहरण",
    "## सामान्य भूल",
    "## शीघ्र जाँच प्रश्न",
    "## सारांश",
]

BOARD = "CBSE"
MODE = "CBSE"


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def load_and_validate(input_path: Path) -> dict:
    """Load the GPT-5.5 JSON output and validate its schema. Raises on failure."""
    raw = input_path.read_text(encoding="utf-8").strip()
    # Tolerate accidental markdown fences even though the prompt forbids them
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Input is not valid JSON: {e}")

    if "manifest" not in data or "lessons" not in data:
        raise ValueError("Top-level JSON must have both 'manifest' and 'lessons' keys.")

    manifest = data["manifest"]
    lessons = data["lessons"]

    missing_manifest_keys = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing_manifest_keys:
        raise ValueError(f"Manifest is missing required keys: {missing_manifest_keys}")

    missing_steps = [s for s in REQUIRED_LESSON_STEPS if s not in lessons]
    if missing_steps:
        raise ValueError(f"Lessons object is missing required steps: {missing_steps}")

    for step, content in lessons.items():
        if not isinstance(content, str) or len(content.strip()) < 200:
            raise ValueError(f"Lesson step '{step}' content is missing or suspiciously short.")
        # Validate against whichever heading set (English or Hindi) this
        # content actually matches best — a Hindi chapter authored with
        # Hindi headings should not be flagged as missing all 7 English
        # headings, and vice versa.
        missing_en = [h for h in REQUIRED_LESSON_HEADINGS_EN if h not in content]
        missing_hi = [h for h in REQUIRED_LESSON_HEADINGS_HI if h not in content]
        missing_headings = missing_en if len(missing_en) <= len(missing_hi) else missing_hi
        if missing_headings:
            print(f"  [warn] Step '{step}' is missing expected headings: {missing_headings}")

    return data


def resolve_suggested_images(supplementary_enrichment: dict | None, dry_run: bool) -> dict | None:
    """
    For each entry in supplementary_enrichment["suggested_web_images"],
    attempt to resolve a real, freely-licensed image from Wikimedia
    Commons using its search_description, and fill in
    resolved_image_url/thumb_url/source_page_url/license/attribution.

    Runs only at ingestion time (never at student-serving time) so a
    slow/unavailable Commons API never affects page load. If resolution
    fails for a given image, that entry is left with empty resolved
    fields and the frontend falls back to showing the plain-text search
    suggestion, so ingestion never fails because of this step.
    """
    if not supplementary_enrichment:
        return supplementary_enrichment

    images = supplementary_enrichment.get("suggested_web_images") or []
    if not images:
        return supplementary_enrichment

    print(f"  Resolving {len(images)} suggested image(s) via Wikimedia Commons...")
    if dry_run:
        print("    -> [DRY RUN] Would attempt Commons resolution for each suggested image.")
        return supplementary_enrichment

    try:
        from app.services.commons_image_service import resolve_commons_image  # noqa: PLC0415
    except Exception as e:
        print(f"    [skip] Could not import commons_image_service: {e}")
        return supplementary_enrichment

    resolved_count = 0
    for img in images:
        search = img.get("search_description") or img.get("topic") or ""
        topic = img.get("topic") or ""
        if not search:
            continue
        result = resolve_commons_image(search, topic=topic)
        if result:
            img["resolved_image_url"] = result.get("full_url", "")
            img["thumb_url"] = result.get("thumb_url", "")
            img["source_page_url"] = result.get("source_page_url", "")
            img["license"] = result.get("license", "")
            img["attribution"] = result.get("attribution", "")
            resolved_count += 1
            print(f"    -> resolved: {img.get('topic', search)[:50]!r}")
        else:
            print(f"    -> [no match] {img.get('topic', search)[:50]!r}")

    print(f"    Resolved {resolved_count}/{len(images)} images from Wikimedia Commons.")
    return supplementary_enrichment


def write_manifest(manifest: dict, dry_run: bool, supplementary_enrichment: dict | None = None) -> Path:
    grade_slug = _slugify(manifest["grade"])
    subject_slug = _slugify(manifest["subject"])
    chapter_slug = _slugify(manifest["chapter"])
    out_dir = MANIFEST_ROOT / grade_slug / subject_slug
    out_path = out_dir / f"{chapter_slug}.json"

    # Enrich with standard manifest metadata fields used by the pilot manifests
    enriched = dict(manifest)
    enriched.setdefault("manifest_version", "1.0")
    enriched.setdefault("manifest_status", "gpt55_generated")

    # If GPT-5.5 provided a "supplementary_enrichment" object (extra
    # research notes + suggested free/open-licence web images, see
    # scripts/prepare_gpt55_prompts_advanced.py), persist it inside the
    # manifest file under its own key so it stays clearly separate from
    # the strictly-grounded manifest/lesson fields but is still saved
    # somewhere durable for the frontend/admin tooling to read later.
    if supplementary_enrichment:
        enriched["supplementary_enrichment"] = supplementary_enrichment

    print(f"  Manifest target: {out_path}")
    if dry_run:
        print("    -> [DRY RUN] Would write manifest.")
        if supplementary_enrichment:
            n_notes = len(supplementary_enrichment.get("beyond_the_textbook", []))
            n_images = len(supplementary_enrichment.get("suggested_web_images", []))
            print(f"    -> [DRY RUN] Would include supplementary_enrichment "
                  f"({n_notes} notes, {n_images} suggested images).")
        return out_path

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print("    -> Manifest written.")
    if supplementary_enrichment:
        n_notes = len(supplementary_enrichment.get("beyond_the_textbook", []))
        n_images = len(supplementary_enrichment.get("suggested_web_images", []))
        print(f"    -> Included supplementary_enrichment ({n_notes} notes, {n_images} suggested images).")
    return out_path


def ensure_textbook_images(manifest: dict, dry_run: bool, force: bool) -> None:
    """
    Automatically backfill + deterministically curate real NCERT textbook
    images for this chapter, so every future GPT-5.5-ingested chapter gets
    relevant figures attached with zero extra manual steps.

    This locates the chapter's source PDF via prepare_gpt55_prompts.py's
    BOOK_SOURCES (grade/subject -> pdf_dir/book_code/chapter_count) and its
    rag_documents.id via a robust lookup that tries the exact manifest
    chapter string, then the "Chapter N: " prefixed form, then a bare
    suffix match — the same three-tier fallback used elsewhere in this
    plan (see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4i/§4l/§4m) to
    handle the recurring chapter-naming-convention mismatch.

    Never fails the overall ingestion — if the PDF or rag_documents row
    cannot be found (e.g. a brand-new subject/grade with no BOOK_SOURCES
    entry yet, or the PDF hasn't been uploaded to RAG), this prints a
    clear warning and the script continues; content ingestion is not
    blocked by missing visuals.
    """
    grade = manifest["grade"]
    subject = manifest["subject"]
    chapter = manifest["chapter"]

    print(f"  Textbook images: locating source PDF and rag_documents row for this chapter...")

    try:
        from scripts.prepare_gpt55_prompts import (  # noqa: PLC0415
            BOOK_SOURCES,
            _resolve_pdf_path_for_chapter,
            get_chapter_list,
        )
    except Exception as e:
        print(f"    [skip] Could not import prepare_gpt55_prompts.BOOK_SOURCES: {e}")
        return

    key = (grade, subject)
    if key not in BOOK_SOURCES:
        print(f"    [skip] No BOOK_SOURCES entry for {grade}/{subject} — "
              f"add one to scripts/prepare_gpt55_prompts.py to enable textbook "
              f"images for this grade/subject. Content ingestion is unaffected.")
        return

    source_cfg = BOOK_SOURCES[key]

    try:
        chapters = get_chapter_list(grade, subject)
    except Exception as e:
        print(f"    [skip] Could not load chapter list for {grade}/{subject}: {e}")
        return

    # Find this chapter's 1-based index in the syllabus list — try exact
    # match first, then a substring match (manifest chapter strings from
    # GPT-5.5 sometimes drop or add a "Chapter N: " prefix vs syllabus.py).
    chapter_index = None
    for i, syllabus_chapter in enumerate(chapters, start=1):
        if syllabus_chapter == chapter or syllabus_chapter in chapter or chapter in syllabus_chapter:
            chapter_index = i
            break
    if chapter_index is None:
        print(f"    [skip] Could not match manifest chapter {chapter!r} to any "
              f"entry in the {grade}/{subject} syllabus chapter list.")
        return

    # Supports both the simple single-part shape ({pdf_dir, book_code,
    # num_chapters}) and the multi-part shape ({parts: [...]}) used by
    # NCERT books physically split into two volumes (e.g. Grade 7 Maths).
    try:
        pdf_path = _resolve_pdf_path_for_chapter(source_cfg, chapter_index)
    except Exception as e:
        print(f"    [skip] Could not resolve PDF path for chapter index {chapter_index}: {e}")
        return
    if not pdf_path.exists():
        print(f"    [skip] Source PDF not found: {pdf_path}")
        return

    # Resolve rag_documents.id — try exact chapter string, then "Chapter N: "
    # prefixed, then a bare suffix match, before giving up.
    document_id = None
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        candidates = [chapter, f"Chapter {chapter_index}: {chapter}"]
        for candidate in candidates:
            result = (
                admin_client.table("rag_documents")
                .select("id")
                .eq("grade", grade)
                .eq("subject", subject)
                .eq("chapter", candidate)
                .limit(1)
                .execute()
            )
            if result.data:
                document_id = str(result.data[0]["id"])
                break
        if document_id is None:
            # Last resort: suffix match against rag_documents.chapter
            result = (
                admin_client.table("rag_documents")
                .select("id")
                .eq("grade", grade)
                .eq("subject", subject)
                .ilike("chapter", f"%{chapter}")
                .limit(1)
                .execute()
            )
            if result.data:
                document_id = str(result.data[0]["id"])
    except Exception as e:
        print(f"    [skip] Error looking up rag_documents row: {e}")
        return

    if document_id is None:
        print(f"    [skip] No rag_documents row found for this chapter — "
              f"upload the source PDF to RAG first to enable textbook images.")
        return

    print(f"    Found: document_id={document_id}, pdf={pdf_path.name}")

    if dry_run:
        print("    [DRY RUN] Would backfill + curate textbook images for this chapter.")
        return

    try:
        from app.services.rag_visual_service import backfill_visual_assets_for_document  # noqa: PLC0415
        from scripts.curate_textbook_visuals import curate_document  # noqa: PLC0415

        file_bytes = pdf_path.read_bytes()
        backfill_result = backfill_visual_assets_for_document(
            document_id=document_id,
            file_bytes=file_bytes,
            filename=pdf_path.name,
            uploaded_by=None,
        )
        print(f"    backfill: {backfill_result.get('message')}")

        curate_document(document_id=document_id, pdf_path=str(pdf_path), dry_run=False, force=force)
    except Exception as e:
        print(f"    [warn] Textbook image backfill/curation failed (content ingestion still succeeded): {e}")


def invalidate_chapter_doc_cache(manifest: dict, dry_run: bool) -> None:
    """
    Delete any stored lesson_chapter_doc row for this chapter so the
    Chapter Journey UI reconverts from the freshly-updated lesson_cache
    content instead of silently serving a stale pre-fix document.

    See docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4i for why this step
    is mandatory after every lesson_cache overwrite.
    """
    grade = manifest["grade"]
    subject = manifest["subject"]
    chapter = manifest["chapter"]

    if dry_run:
        print(f"  [DRY RUN] Would invalidate lesson_chapter_doc for "
              f"{grade}/{subject}/{chapter!r}")
        return

    try:
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415
        db = get_content_db(grade)
        result = (
            db.table("lesson_chapter_doc")
            .delete()
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .execute()
        )
        deleted = len(result.data or [])
        if deleted:
            print(f"  Invalidated {deleted} stale lesson_chapter_doc row(s) "
                  f"for this chapter — Chapter Journey UI will reconvert fresh.")
        else:
            print("  No stale lesson_chapter_doc rows found for this chapter (nothing to invalidate).")
    except Exception as e:
        print(f"  [warn] Could not invalidate lesson_chapter_doc cache: {e}")


def seed_lessons(manifest: dict, lessons: dict, dry_run: bool, force: bool) -> None:
    grade = manifest["grade"]
    subject = manifest["subject"]
    chapter = manifest["chapter"]

    for step_title, content in lessons.items():
        cache_key = make_lesson_cache_key(
            board=BOARD, grade=grade, subject=subject, chapter=chapter,
            mode=MODE, step_title=step_title, teacher_persona="",
        )
        existing = get_cached_lesson(cache_key, grade=grade)
        word_count = len(content.split())
        print(f"  [{step_title}] {word_count} words, cache_key={cache_key[:16]}...")

        if existing and not force:
            print("    -> Already cached. Skipping (use --force to overwrite).")
            continue

        if dry_run:
            print(f"    -> [DRY RUN] Would store {len(content)} chars as source_type=MANUAL.")
            continue

        store_lesson_cache(
            cache_key=cache_key,
            lesson_content=content,
            source_type="MANUAL",
            board=BOARD, grade=grade, subject=subject, chapter=chapter,
            mode=MODE, step_title=step_title, teacher_persona="",
            practice_questions=[],
        )
        print(f"    -> Stored ({len(content)} chars).")


def run_followup_audit(manifest: dict) -> None:
    """Re-run the Tier A audit for this exact chapter and print results."""
    try:
        from scripts.audit_chapter_boundary import run_audit  # noqa: PLC0415
    except Exception as e:
        print(f"  [warn] Could not import audit_chapter_boundary: {e}")
        return

    print("\n  Running Tier A follow-up audit...")
    run_audit(
        grade_filter=manifest["grade"],
        subject_filter=manifest["subject"],
        chapter_filter=manifest["chapter"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GPT-5.5 chapter authoring JSON output")
    parser.add_argument("--input", required=True, help="Path to the GPT-5.5 JSON output file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing cached lessons for these steps")
    parser.add_argument("--skip-audit", action="store_true", help="Skip the automatic follow-up Tier A audit")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        sys.exit(1)

    print(f"\n  Ingest GPT-5.5 Chapter Output")
    print(f"  Input: {input_path}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE WRITE'}\n")

    try:
        data = load_and_validate(input_path)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    manifest = data["manifest"]
    lessons = data["lessons"]
    supplementary_enrichment = data.get("supplementary_enrichment")

    print(f"  Chapter: {manifest['grade']} / {manifest['subject']} / {manifest['chapter']}\n")

    supplementary_enrichment = resolve_suggested_images(supplementary_enrichment, dry_run=args.dry_run)
    print()

    write_manifest(manifest, dry_run=args.dry_run, supplementary_enrichment=supplementary_enrichment)
    print()
    seed_lessons(manifest, lessons, dry_run=args.dry_run, force=args.force)
    print()
    ensure_textbook_images(manifest, dry_run=args.dry_run, force=args.force)
    print()
    invalidate_chapter_doc_cache(manifest, dry_run=args.dry_run)

    if not args.dry_run and not args.skip_audit:
        run_followup_audit(manifest)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
