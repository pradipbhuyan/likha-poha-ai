#!/usr/bin/env python3
"""
Curate Textbook Visuals — deterministic, NCERT-caption-based approval
========================================================================
Fixes the "random/subjective page approval" problem found during the
Cell chapter pilot: the first curation pass approved pages by eyeballing
text snippets, which incorrectly approved 2 pure-text pages with no real
diagram (pages 7, 17) and missed 3 pages that DO contain real NCERT
figures (pages 8, 18, 19).

This script replaces subjective judgment with a deterministic rule:

  A page is approved ONLY IF PyMuPDF's extracted text contains at least
  one NCERT-style figure caption matching the pattern:
      "Fig. <chapter>.<number>: <caption text>"
  (NCERT's own convention throughout the Exploration series, verified
  against the actual Cell chapter PDF text.)

  The approved page's `caption` field is set to the ACTUAL printed
  caption extracted from the page text (e.g. "Fig. 2.13: Endoplasmic
  reticulum and Golgi apparatus — pathway for protein processing and
  secretion") — never an invented/guessed description.

  Pages with NO Fig. N.N caption anywhere in their extracted text are
  left as `status="needs_review"` and are NEVER auto-approved, no
  matter how "relevant-sounding" the surrounding prose looks — text-only
  pages add no diagram value and were explicitly what the user flagged
  as "randomly added."

IMPORTANT — why this reads the source PDF directly, not `nearby_text`:
`rag_visual_assets.nearby_text` is truncated to 1200 characters at
backfill time (see rag_visual_service.py), and NCERT's real figure
caption text blocks are frequently extracted by PyMuPDF near the END of
a page's raw text (since captions are separate text objects positioned
near the images, appearing after the main body paragraphs in extraction
order). The truncated `nearby_text` field routinely cuts these captions
off entirely — confirmed directly against the Cell chapter, where page
10's real caption "Fig. 2.13: Endoplasmic reticulum and Golgi
apparatus..." was truncated away, while only an unrelated in-text
reference "(Fig. 2.13)." survived in the stored 1200-char snippet. This
script therefore re-extracts full, untruncated text straight from the
source PDF for accurate caption detection.

Usage:
    cd backend
    python3 scripts/curate_textbook_visuals.py --document-id 346 --pdf-path "../RAG DB/Science/iesc102.pdf" --dry-run
    python3 scripts/curate_textbook_visuals.py --document-id 346 --pdf-path "../RAG DB/Science/iesc102.pdf" --force
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# NCERT figure caption pattern — two conventions verified across
# different textbook series:
#   - Exploration series (Science): COLON right after the figure number:
#       "Fig. 2.13: Endoplasmic reticulum and Golgi apparatus..."
#   - Understanding Society series (Social Science, 2026 edition): PERIOD
#     right after the figure number, often with a very short 1-3 word
#     caption (labels like a place/landform name rather than a full
#     sentence):
#       "Fig. 2.10. Waterfall"
#       "Fig. 2.3. World map showing major plates and their direction of movement"
# Both are genuine, deterministic NCERT captions — only an in-text
# reference (pointing to a figure discussed elsewhere) differs, using a
# closing parenthesis instead of a colon/period right after the number:
#       "...different parts of a microscope (Fig. 2.2) in your school..."
# Requiring a colon OR a period immediately after "Fig. N.N" (not a
# closing paren) is what keeps this deterministic and excludes in-text
# references like "(Fig. 2.9)" from being mistaken for captions.
_FIG_CAPTION_RE = re.compile(
    r"Fig(?:ure)?\.[\s\xa0]*(\d+\.\d+)\s*[:.]\s*([^\n]{2,140})",
    re.IGNORECASE,
)


def extract_figure_captions(nearby_text: str) -> list[tuple[str, str]]:
    """
    Return [(fig_number, caption_text), ...] for every genuine NCERT
    figure caption found in this page's extracted text.

    Requires the colon- or period-separated "Fig. N.N: <description>" /
    "Fig. N.N. <description>" form (see module docstring) AND at least
    1 real word of description — this excludes both bare in-text
    references like "(Fig. 2.2)" and caption-less figure labels like
    "Fig. 2.20" followed immediately by an unrelated lettered exercise
    list with no real words after it.

    The minimum word count is intentionally low (1, not 3) because the
    Understanding Society series often uses single-word captions that
    are still genuine, printed NCERT captions (e.g. "Fig. 2.10. Waterfall",
    "Fig. 2.11. Meander", "Fig. 2.12. Delta") — requiring 3+ words would
    incorrectly reject these real captions.
    """
    results = []
    for match in _FIG_CAPTION_RE.finditer(nearby_text or ""):
        fig_number = match.group(1)
        caption_text = match.group(2).strip()
        # A genuine caption has at least one real word (letters), not just
        # trailing punctuation, page numbers, or whitespace.
        if not re.search(r"[A-Za-z]", caption_text):
            continue
        if len(caption_text.split()) < 1:
            continue
        results.append((fig_number, caption_text))
    return results


def build_caption(fig_number: str, caption_text: str) -> str:
    """Build the display caption exactly as printed in the NCERT text."""
    return f"Fig. {fig_number}: {caption_text}".rstrip(" .") 


def load_full_page_texts(pdf_path: str) -> dict[int, str]:
    """Return {page_number (1-indexed): full_untruncated_text} for a PDF."""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    texts = {}
    for i in range(doc.page_count):
        texts[i + 1] = doc.load_page(i).get_text("text") or ""
    doc.close()
    return texts


def _figure_crop_rect(page, fig_number: str) -> "fitz.Rect | None":
    """
    Compute a crop rectangle spanning the FULL PAGE WIDTH but trimmed
    vertically to the region containing the actual figure image(s) and
    their caption.

    Design change (per user feedback): the earlier version cropped
    tightly on all four sides to the embedded image's bounding box. That
    risked clipping parts of the diagram or its caption whenever the
    image bounding box PyMuPDF reports does not perfectly match what is
    visually printed (labels, arrows, or multi-part figures can extend
    slightly beyond the raw image rect). The user asked for horizontal
    cropping to be removed entirely — keep the full page width exactly
    as printed — and only trim vertically (removing unrelated content
    above/below the figure), with generous padding so nothing is ever
    cut off.

    Returns None if the page has no embedded raster images (some NCERT
    figures are vector line-art, not embedded images — those pages keep
    the full-page fallback rather than guessing a crop region).
    """
    import fitz  # PyMuPDF

    page_area = page.rect.width * page.rect.height
    image_rects = []
    for img in page.get_images(full=True):
        xref = img[0]
        for rect in page.get_image_rects(xref):
            # Skip tiny decorative images (icons, bullets) — a genuine
            # NCERT figure occupies a meaningful fraction of the page,
            # but skip near-full-page images too (background textures/
            # watermarks) — these swallow the whole union and defeat the
            # crop entirely. Confirmed on a real page: one such
            # background image was 610x863pt on a 594x784pt page,
            # exceeding the page bounds and making every "crop" equal
            # the full page again.
            rect_area = rect.width * rect.height
            if rect.width > 60 and rect.height > 60 and rect_area < 0.55 * page_area:
                image_rects.append(rect)

    if not image_rects:
        return None

    # Union of all embedded image rects (a figure can be made of multiple
    # image pieces, e.g. a labelled diagram with separate label overlays).
    union = image_rects[0]
    for rect in image_rects[1:]:
        union |= rect

    # Extend downward to capture the caption line — NCERT captions are
    # printed as a text block directly below the figure. Search text
    # blocks for this exact figure's "Fig. N.N:" caption and extend the
    # vertical range to include whichever caption block sits just below
    # the image, and any label text sitting just above it too.
    caption_pattern = re.compile(
        rf"Fig(?:ure)?\.[\s\xa0]*{re.escape(fig_number)}\s*[:.]", re.IGNORECASE,
    )
    top = union.y0
    bottom = union.y1
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:  # not a text block
            continue
        block_text = "".join(
            span.get("text", "")
            for line in block.get("lines", [])
            for span in line.get("spans", [])
        )
        if caption_pattern.search(block_text):
            block_rect = fitz.Rect(block["bbox"])
            # Only extend if this caption block is reasonably close below
            # the image (avoids grabbing an unrelated caption far down
            # the page for a different figure with a similar number).
            if union.y1 - 20 <= block_rect.y0 <= union.y1 + 140:
                bottom = max(bottom, block_rect.y1)

    # Generous vertical padding on both sides — this is intentionally
    # larger than the previous tight crop to guarantee no part of the
    # diagram, its labels, or its caption is ever clipped. Horizontal
    # bounds are NOT touched: the crop always spans the full page width.
    pad_top = 24
    pad_bottom = 30
    top = max(0, top - pad_top)
    bottom = min(page.rect.height, bottom + pad_bottom)

    return fitz.Rect(0, top, page.rect.width, bottom)


def crop_and_reupload_figure(
    document_id: str,
    pdf_path: str,
    page_number: int,
    fig_number: str,
    storage_path: str,
    dry_run: bool,
) -> bool:
    """
    Re-render just the figure region (image + caption) for an approved
    page and overwrite the existing full-page screenshot in Supabase
    Storage at the same storage_path — the asset_url and DB row stay
    unchanged, only the image content improves.

    Returns True if a crop was applied, False if the page had no
    detectable embedded image (kept as full-page fallback).
    """
    import fitz  # PyMuPDF

    pdf_document = fitz.open(pdf_path)
    try:
        page = pdf_document.load_page(page_number - 1)
        crop_rect = _figure_crop_rect(page, fig_number)
        if crop_rect is None:
            return False

        if dry_run:
            return True

        matrix = fitz.Matrix(2.2, 2.2)  # higher scale since crop is smaller
        pixmap = page.get_pixmap(matrix=matrix, clip=crop_rect, alpha=False)
        image_bytes = pixmap.tobytes("jpeg")

        admin_client.storage.from_("rag-visuals").upload(
            path=storage_path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return True
    finally:
        pdf_document.close()


def curate_document(document_id: str, pdf_path: str, dry_run: bool, force: bool) -> None:
    print(f"\n  Curating visuals for document_id={document_id}")
    print(f"  Source PDF: {pdf_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    page_texts = load_full_page_texts(pdf_path)

    result = (
        admin_client.table("rag_visual_assets")
        .select("id, page_number, nearby_text, status, caption, storage_path")
        .eq("document_id", document_id)
        .order("page_number")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print("  No rag_visual_assets rows found for this document_id. "
              "Run the backfill first (rag_visual_service.backfill_visual_assets_for_document).")
        return

    approved_count = 0
    rejected_count = 0
    cropped_count = 0

    for row in rows:
        page_number = row["page_number"]
        # Use FULL untruncated page text from the source PDF, not the
        # 1200-char nearby_text field (see module docstring for why).
        full_text = page_texts.get(page_number, "") or row.get("nearby_text") or ""
        current_status = row.get("status")

        captions = extract_figure_captions(full_text)

        if not captions:
            # No genuine NCERT figure on this page — never auto-approve.
            action = "SKIP (no real figure caption found)"
            if current_status == "active" and not dry_run:
                # Previously (incorrectly) approved with no real figure —
                # revert to needs_review so it stops being served.
                admin_client.table("rag_visual_assets").update(
                    {"status": "needs_review"}
                ).eq("id", row["id"]).execute()
                action = "REVERTED to needs_review (was active but has no real figure)"
            print(f"  Page {page_number:>3}: {action}")
            rejected_count += 1
            continue

        # Use the first genuine figure caption found on the page (pages can
        # have 2+ figures; the first is usually the dominant one referenced
        # by the surrounding paragraph).
        fig_number, caption_text = captions[0]
        new_caption = build_caption(fig_number, caption_text)

        already_active = current_status == "active"
        print(f"  Page {page_number:>3}: APPROVE -> {new_caption}"
              f"{' (already active, updating caption)' if already_active else ''}")
        approved_count += 1

        # Crop to just the figure + caption instead of leaving the full
        # PDF page screenshot — fixes images visually containing large
        # blocks of unrelated surrounding page text/exercises baked into
        # the pixels (see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md §4p).
        storage_path = row.get("storage_path")
        if storage_path:
            was_cropped = crop_and_reupload_figure(
                document_id=document_id,
                pdf_path=pdf_path,
                page_number=page_number,
                fig_number=fig_number,
                storage_path=storage_path,
                dry_run=dry_run,
            )
            if was_cropped:
                cropped_count += 1
                print(f"           -> cropped to figure region (was full-page screenshot)")
            else:
                print(f"           -> no embedded raster image detected; kept full-page image")

        if dry_run:
            continue
        if already_active and not force:
            continue  # already active with correct workflow — leave as-is unless forcing caption refresh

        admin_client.table("rag_visual_assets").update({
            "status": "active",
            "caption": new_caption,
        }).eq("id", row["id"]).execute()

    print(f"\n  Summary: {approved_count} page(s) have genuine NCERT figures "
          f"(approved/kept active, {cropped_count} cropped to figure-only), "
          f"{rejected_count} page(s) rejected "
          f"(no real figure — text-only or exercise-only pages).\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically curate textbook visual pages using NCERT's own Fig. N.N caption convention"
    )
    parser.add_argument("--document-id", required=True, help="rag_documents.id to curate")
    parser.add_argument("--pdf-path", required=True, help="Path to the source PDF (for full-text caption extraction)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--force", action="store_true",
                        help="Also refresh captions for pages already active")
    args = parser.parse_args()

    curate_document(
        document_id=args.document_id,
        pdf_path=args.pdf_path,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
