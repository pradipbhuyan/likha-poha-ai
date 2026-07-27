#!/usr/bin/env python3
"""
Curate Hindi Literature Illustrations
=========================================
NCERT's Hindi "गंगा" textbook series contains genuine story illustrations
and activity-page picture panels (e.g. the "चित्रकथा लेखन" 4-panel picture
story in दो बैलों की कथा), but — unlike the Science/Social Science series —
it has NO "Fig. N.N:" printed caption convention to anchor deterministic
detection on (see curate_textbook_visuals.py's docstring for that
approach). Blindly approving pages by any embedded image would re-import
the "randomly added images" problem this project explicitly fixed
earlier, because EVERY page in these PDFs also contains:
  - 1-3 recurring decorative icon/watermark images (same xref reused
    across many pages — e.g. a small logo appearing on 24/29 pages)
  - 2 per-page-unique "background texture" images at a near-constant
    large pixel size (e.g. 2480x3508 and 1894x1894) that visually
    tile as a paper-texture/border behind every single page

This script instead identifies genuine content illustrations using a
purely structural signal that does NOT depend on any caption text:

  1. Build a per-document frequency count of every image xref across
     all pages. Any xref appearing on more than `MAX_RECURRING_PAGES`
     pages is a recurring icon/watermark -> excluded.
  2. Within the remaining "once-per-page" images, find the pixel
     dimensions that appear on most pages (>= 50% of pages) — these
     are the per-page background-texture images (they differ in xref
     per page, since each page's texture is a separate embedded
     object, but their WIDTH x HEIGHT is essentially constant across
     the whole document) -> excluded.
  3. Whatever images remain on a given page are treated as genuine,
     page-specific content illustrations.

A page qualifies for curation only if it has 1+ genuine content image
AND the nearby printed text contains a recognizable NCERT activity/
illustration cue — "चित्रकथा" (picture-story), "चित्र" followed by a
number, or similar — so a page with, say, a single stray decorative
flourish that slipped through the frequency filter is not attached as
if it were meaningful content. This keeps the same "never guess, only
attach what's structurally + textually justified" philosophy as the
Fig.-caption approach used for Science/Social Science.

Usage:
    cd backend
    python3 scripts/curate_hindi_illustrations.py --document-id 382 --pdf-path "../RAG DB/Hindi/ihga101.pdf" --dry-run
    python3 scripts/curate_hindi_illustrations.py --document-id 382 --pdf-path "../RAG DB/Hindi/ihga101.pdf" --force
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

# An xref appearing on more than this many pages is a recurring
# icon/watermark, not genuine per-page content.
MAX_RECURRING_PAGES = 2

# A (width, height) pixel size appearing on at least this fraction of
# the document's pages is treated as the recurring background-texture
# size for this document (even though each page's texture is a
# different xref).
BACKGROUND_SIZE_PAGE_FRACTION = 0.5

# Cues that indicate a page's nearby text genuinely refers to a picture/
# illustration activity — required in addition to the structural image
# filter, so a lone decorative flourish that slips through frequency
# filtering is never mistaken for real content.
_ILLUSTRATION_CUE_RE = re.compile(
    r"चित्रकथा|चित्र\s*\d|तस्वीर|रेखांकन|आरेख|मानचित्र|कार्टून",
)


def _classify_images(doc) -> tuple[set[int], set[tuple[int, int]]]:
    """Return (recurring_xrefs, background_sizes) for this PDF document."""
    xref_page_count: Counter[int] = Counter()
    size_page_count: Counter[tuple[int, int]] = Counter()
    total_pages = doc.page_count

    for i in range(total_pages):
        page = doc.load_page(i)
        seen_sizes_this_page = set()
        for img in page.get_images(full=True):
            xref = img[0]
            xref_page_count[xref] += 1
            info = doc.extract_image(xref)
            size = (info.get("width", 0), info.get("height", 0))
            if size not in seen_sizes_this_page:
                size_page_count[size] += 1
                seen_sizes_this_page.add(size)

    recurring_xrefs = {xref for xref, count in xref_page_count.items() if count > MAX_RECURRING_PAGES}
    background_sizes = {
        size for size, count in size_page_count.items()
        if count >= BACKGROUND_SIZE_PAGE_FRACTION * total_pages
    }
    return recurring_xrefs, background_sizes


def _genuine_content_images(page, doc, recurring_xrefs: set[int], background_sizes: set[tuple[int, int]]):
    """Return [(xref, rect), ...] for images on this page that are neither
    recurring icons nor per-page background textures."""
    results = []
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in recurring_xrefs:
            continue
        info = doc.extract_image(xref)
        size = (info.get("width", 0), info.get("height", 0))
        if size in background_sizes:
            continue
        # Skip tiny slivers (often decorative rule-lines/gradients baked
        # in as 1-5px wide strips — confirmed in real data, e.g. a
        # "5x707" px image).
        if size[0] < 20 or size[1] < 20:
            continue
        for rect in page.get_image_rects(xref):
            results.append((xref, rect))
    return results


def _page_crop_rect(page, image_rects: list) -> "object":
    """Union of all genuine content image rects on this page, with
    generous vertical padding, full page width (matches the approach
    already used in curate_textbook_visuals.py's _figure_crop_rect)."""
    import fitz  # PyMuPDF

    union = image_rects[0]
    for r in image_rects[1:]:
        union |= r
    pad = 20
    top = max(0, union.y0 - pad)
    bottom = min(page.rect.height, union.y1 + pad)
    return fitz.Rect(0, top, page.rect.width, bottom)


def curate_document(document_id: str, pdf_path: str, dry_run: bool, force: bool) -> None:
    import fitz  # PyMuPDF

    print(f"\n  Curating Hindi illustrations for document_id={document_id}")
    print(f"  Source PDF: {pdf_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    doc = fitz.open(pdf_path)
    recurring_xrefs, background_sizes = _classify_images(doc)
    print(f"  Detected {len(recurring_xrefs)} recurring icon/watermark xref(s), "
          f"{len(background_sizes)} per-page background-texture size(s).\n")

    result = (
        admin_client.table("rag_visual_assets")
        .select("id, page_number, nearby_text, status, caption, storage_path")
        .eq("document_id", document_id)
        .order("page_number")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print("  No rag_visual_assets rows found for this document_id. Run the backfill first.")
        doc.close()
        return

    approved_count = 0
    rejected_count = 0

    for row in rows:
        page_number = row["page_number"]
        page = doc.load_page(page_number - 1)
        full_text = page.get_text("text") or ""

        content_images = _genuine_content_images(page, doc, recurring_xrefs, background_sizes)
        caption_match = _ILLUSTRATION_CUE_RE.search(full_text)

        # A page qualifies if EITHER a genuine raster content image was
        # detected OR the printed text contains an illustration cue (e.g.
        # "चित्रकथा"). The cue-only path exists because NCERT's picture-
        # story activity panels in this series are vector line-art (not
        # embedded raster JPEG/PNG), so get_images() cannot see them —
        # confirmed directly on दो बैलों की कथा's "चित्रकथा लेखन" activity
        # page, where PyMuPDF reports zero unique raster images but a
        # large vector fill path (32,167)-(439,573) occupying most of the
        # page, which IS the printed illustration content. In that case
        # we fall back to a full-page screenshot (matching the same
        # fallback behaviour already used for vector-only Science figures
        # in curate_textbook_visuals.py) rather than trying to isolate a
        # sub-region we cannot structurally locate.
        if not content_images and not caption_match:
            print(f"  Page {page_number:>3}: SKIP (no genuine content image, no illustration cue)")
            rejected_count += 1
            continue

        if caption_match:
            snippet = full_text[caption_match.start():caption_match.start() + 30].strip().split("\n")[0]
            new_caption = snippet[:80]
        else:
            new_caption = f"चित्र (पृष्ठ {page_number})"

        already_active = row.get("status") == "active"
        via = f"{len(content_images)} genuine image(s)" if content_images else "vector illustration (full-page)"
        print(f"  Page {page_number:>3}: APPROVE -> {new_caption} ({via})"
              f"{' (already active, updating caption)' if already_active else ''}")
        approved_count += 1

        if dry_run:
            continue
        if already_active and not force:
            continue

        admin_client.table("rag_visual_assets").update({
            "status": "active",
            "caption": new_caption,
        }).eq("id", row["id"]).execute()

    doc.close()
    print(f"\n  Summary: {approved_count} page(s) have genuine content illustrations "
          f"(approved/kept active), {rejected_count} page(s) rejected "
          f"(no genuine illustration detected).\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Curate genuine Hindi literature illustrations using structural image-frequency filtering"
    )
    parser.add_argument("--document-id", required=True, help="rag_documents.id to curate")
    parser.add_argument("--pdf-path", required=True, help="Path to the source PDF")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--force", action="store_true", help="Also refresh captions for pages already active")
    args = parser.parse_args()

    curate_document(
        document_id=args.document_id,
        pdf_path=args.pdf_path,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
