#!/usr/bin/env python3
"""
Apply Chapter Infographic Posters to lesson_cache
=================================================
One command takes an authored poster image (e.g. a GPT-5.5 infographic PNG) and
puts it at the end of a chapter's final lesson step:

  1. Optimise — convert to WebP and downscale to MAX_EDGE. A 2 MB PNG poster
     typically lands around 240 KB with no visible loss, which matters because
     this ships to students on mobile data.
  2. Upload — to the existing public `rag-visuals` Supabase Storage bucket,
     under chapter-infographics/<board>/<grade>/<subject>/<chapter>.webp
  3. Record — write a sidecar JSON under
     backend/app/data/chapter_infographics/... so the applied state is in git.
  4. Apply — append a ```chapter-infographic fence under a
     "## Chapter at a glance" heading on the target lesson step.

Rendered by frontend/src/components/ChapterInfographicBlock.jsx (web) and
mobile/components/ChapterInfographicCard.tsx, both validating against
shared/utils/chapterInfographic.js.

Idempotent: re-running replaces the existing block rather than appending a
second copy, so a re-authored poster fully supersedes the old one.

Usage:
    cd backend
    python3 scripts/apply_chapter_infographic.py \
        --image ~/Downloads/poster.png \
        --grade "Grade 12" --subject Biology \
        --chapter "Chapter 9: Biotechnology: Principles and Processes" \
        --alt "One-page revision poster covering ..." \
        --dry-run

    # Re-apply everything already recorded in the sidecar files
    python3 scripts/apply_chapter_infographic.py --dir app/data/chapter_infographics

    # Remove a previously applied block
    python3 scripts/apply_chapter_infographic.py --remove \
        --grade "Grade 12" --subject Biology --chapter "Chapter 9: ..."
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.grade_db_router import get_content_db  # noqa: E402

RAG_VISUAL_BUCKET = "rag-visuals"
SECTION_HEADING = "## Chapter at a glance"
SIDECAR_ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "chapter_infographics"

# Posters are read by panning a zoomed view, so resolution matters more than
# for an inline figure — but past ~2000px the file grows faster than legibility.
MAX_EDGE = 2000
WEBP_QUALITY = 85

# Matches the whole appended section — heading plus fence — so re-running
# replaces it rather than stacking copies.
_APPLIED_BLOCK_RE = re.compile(
    r"\n*##\s*Chapter at a glance\s*\n+```chapter-infographic\n.*?\n```\s*",
    re.DOTALL,
)

# The text-summary block this poster replaces, so a chapter never ends up
# showing both the wall-chart and the poster for the same content.
_APPLIED_SUMMARY_RE = re.compile(
    r"\n*##\s*Chapter at a glance\s*\n+```chapter-summary\n.*?\n```\s*",
    re.DOTALL,
)


def _slug(value: str) -> str:
    """Lowercase, hyphenated, filesystem- and URL-safe."""
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def optimise(image_path: Path) -> tuple[bytes, int, int]:
    """Convert a poster to WebP, downscaling only if it exceeds MAX_EDGE.

    Returns (webp_bytes, width, height).
    """
    from PIL import Image  # imported lazily so --remove works without Pillow

    with Image.open(image_path) as im:
        im = im.convert("RGB")
        if max(im.size) > MAX_EDGE:
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        buffer = io.BytesIO()
        # method=6 is the slowest/densest WebP search — worth it for a one-off
        # authoring step that every student then downloads.
        im.save(buffer, "WEBP", quality=WEBP_QUALITY, method=6)
        return buffer.getvalue(), im.width, im.height


def upload(payload: bytes, storage_path: str) -> str:
    """Upload to the public rag-visuals bucket and return the public URL."""
    try:
        admin_client.storage.from_(RAG_VISUAL_BUCKET).upload(
            path=storage_path,
            file=payload,
            file_options={"content-type": "image/webp", "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(
            f"Upload to Supabase Storage bucket '{RAG_VISUAL_BUCKET}' failed. "
            f"Confirm the bucket exists and is public. Original error: {exc}"
        ) from exc

    url = admin_client.storage.from_(RAG_VISUAL_BUCKET).get_public_url(storage_path)
    # get_public_url appends a trailing "?" in some client versions, which is
    # harmless in a browser but makes the stored URL look malformed.
    return url.rstrip("?")


def build_block(infographic: dict) -> str:
    """Render the poster as the markdown section appended to the lesson step."""
    payload = json.dumps(infographic, ensure_ascii=False, indent=2)
    return f"\n\n{SECTION_HEADING}\n\n```chapter-infographic\n{payload}\n```\n"


def apply_to_content(content: str, block: str) -> str:
    """Replace an already-applied block (or text summary), else append."""
    stripped = _APPLIED_BLOCK_RE.sub("", content)
    stripped = _APPLIED_SUMMARY_RE.sub("", stripped).rstrip()
    return stripped + block


def remove_from_content(content: str) -> str:
    """Strip a previously applied poster block, leaving the lesson intact."""
    return _APPLIED_BLOCK_RE.sub("", content).rstrip() + "\n"


def update_lesson_rows(
    *, grade: str, subject: str, chapter: str, step_title: str,
    block: str, dry_run: bool, remove: bool,
) -> bool:
    """Apply or remove the block on every persona variant of the target step."""
    db = get_content_db(grade)
    result = (
        db.table("lesson_cache")
        .select("id, lesson_content, teacher_persona")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .eq("step_title", step_title)
        .eq("status", "active")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print(f"  ✗ no active lesson_cache row for {grade} / {subject} / {chapter} / {step_title}")
        return False

    action, past_action = ("remove", "removed") if remove else ("apply", "applied")

    # A chapter step can have several rows (one per teacher_persona variant,
    # since persona is part of the cache key). Every variant a student may be
    # served must carry the same poster, so update them all.
    for row in rows:
        original = row.get("lesson_content") or ""
        updated = remove_from_content(original) if remove else apply_to_content(original, block)

        if updated == original:
            print(f"  = already up to date (row {row['id'][:8]})")
            continue

        persona = row.get("teacher_persona") or "default"
        if dry_run:
            print(f"  → would {action} on row {row['id'][:8]} (persona: {persona}, {len(updated) - len(original):+d} chars)")
        else:
            db.table("lesson_cache").update({"lesson_content": updated}).eq("id", row["id"]).execute()
            print(f"  ✓ {past_action} on row {row['id'][:8]} (persona: {persona})")

    return True


def refresh_chapter_doc(*, board: str, grade: str, subject: str, chapter: str, mode: str = "CBSE") -> None:
    """Rebuild the stored lesson_chapter_doc from the just-updated lesson_cache.

    Grades 9-12 are served the Chapter Journey view, which reads the CACHED
    lesson_chapter_doc row rather than lesson_cache directly. Without this the
    poster is written to lesson_cache but the student keeps seeing whatever the
    doc was last built from — which looks exactly like the change not working.
    """
    try:
        from app.services.chapter_doc_service import get_or_convert_chapter_doc  # noqa: PLC0415
        doc = get_or_convert_chapter_doc(
            board=board, grade=grade, subject=subject, chapter=chapter,
            mode=mode, force_refresh=True,
        )
        print("  ✓ chapter doc rebuilt" if doc else "  · no chapter doc for this chapter (per-step view only)")
    except Exception as exc:
        # Never fail the apply over this — the lesson_cache write already
        # succeeded, and the doc can be rebuilt from the UI "Refresh lesson".
        print(f"  ! chapter doc refresh failed ({exc}); use the 'Refresh lesson' button in the app")


def sidecar_path(grade: str, subject: str, chapter: str) -> Path:
    return SIDECAR_ROOT / _slug(grade) / _slug(subject) / f"{_slug(chapter)}.json"


def run_apply(args: argparse.Namespace) -> int:
    image_path = Path(args.image).expanduser()
    if not image_path.exists():
        print(f"✗ image not found: {image_path}")
        return 1

    print(f"Optimising {image_path.name} …")
    payload, width, height = optimise(image_path)
    original_kb = image_path.stat().st_size / 1024
    print(f"  {original_kb:.0f} KB → {len(payload) / 1024:.0f} KB WebP at {width}x{height}")

    storage_path = "/".join([
        "chapter-infographics",
        _slug(args.board),
        _slug(args.grade),
        _slug(args.subject),
        f"{_slug(args.chapter)}.webp",
    ])

    if args.dry_run:
        print(f"  → would upload to {RAG_VISUAL_BUCKET}/{storage_path}")
        url = f"https://<project>.supabase.co/storage/v1/object/public/{RAG_VISUAL_BUCKET}/{storage_path}"
    else:
        url = upload(payload, storage_path)
        print(f"  ✓ uploaded: {url}")

    infographic = {
        "url": url,
        "alt": args.alt,
        "caption": args.caption or "",
        "width": width,
        "height": height,
    }

    path = sidecar_path(args.grade, args.subject, args.chapter)
    record = {
        "grade": args.grade,
        "subject": args.subject,
        "chapter": args.chapter,
        "step_title": args.step,
        "source_image": image_path.name,
        "infographic": infographic,
    }
    if args.dry_run:
        print(f"  → would write sidecar {path.relative_to(SIDECAR_ROOT.parents[2])}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✓ sidecar written: {path.relative_to(SIDECAR_ROOT.parents[2])}")

    print(f"\nApplying to {args.grade} / {args.subject} / {args.chapter} / {args.step}")
    ok = update_lesson_rows(
        grade=args.grade, subject=args.subject, chapter=args.chapter,
        step_title=args.step, block=build_block(infographic),
        dry_run=args.dry_run, remove=False,
    )
    if ok and not args.dry_run:
        refresh_chapter_doc(board=args.board, grade=args.grade, subject=args.subject, chapter=args.chapter)
    return 0 if ok else 1


def run_from_dir(args: argparse.Namespace) -> int:
    """Re-apply every recorded sidecar — the image is already hosted."""
    paths = sorted(Path(args.dir).expanduser().rglob("*.json"))
    if not paths:
        print(f"No .json files found under {args.dir}")
        return 1

    failures = 0
    for path in paths:
        print(f"{path}")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  ✗ not valid JSON: {exc}")
            failures += 1
            continue

        ok = update_lesson_rows(
            grade=record["grade"], subject=record["subject"], chapter=record["chapter"],
            step_title=record["step_title"], block=build_block(record["infographic"]),
            dry_run=args.dry_run, remove=args.remove,
        )
        if ok and not args.dry_run:
            refresh_chapter_doc(
                board=record.get("board", "CBSE"), grade=record["grade"],
                subject=record["subject"], chapter=record["chapter"],
            )
        if not ok:
            failures += 1
        print()

    print(f"Done: {len(paths) - failures} succeeded, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image", help="Poster image to optimise, upload and apply")
    parser.add_argument("--dir", help="Re-apply every recorded sidecar JSON under this folder")
    parser.add_argument("--grade")
    parser.add_argument("--subject")
    parser.add_argument("--chapter")
    parser.add_argument("--board", default="CBSE")
    parser.add_argument("--step", default="Revision and recap", help="Lesson step to append to")
    parser.add_argument("--alt", help="Screen-reader description (required with --image)")
    parser.add_argument("--caption", default="", help="Optional line shown under the poster")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--remove", action="store_true", help="Strip a previously applied block")
    args = parser.parse_args()

    if args.dir:
        return run_from_dir(args)

    if args.remove:
        if not all([args.grade, args.subject, args.chapter]):
            parser.error("--remove needs --grade, --subject and --chapter")
        print(f"Removing poster from {args.grade} / {args.subject} / {args.chapter} / {args.step}")
        ok = update_lesson_rows(
            grade=args.grade, subject=args.subject, chapter=args.chapter,
            step_title=args.step, block="", dry_run=args.dry_run, remove=True,
        )
        if ok and not args.dry_run:
            refresh_chapter_doc(board=args.board, grade=args.grade, subject=args.subject, chapter=args.chapter)
        return 0 if ok else 1

    if not args.image:
        parser.error("one of --image, --dir or --remove is required")
    if not all([args.grade, args.subject, args.chapter, args.alt]):
        parser.error("--image needs --grade, --subject, --chapter and --alt")

    return run_apply(args)


if __name__ == "__main__":
    raise SystemExit(main())
