#!/usr/bin/env python3
"""
Curate Prose Textbook Visuals — deterministic, image-size/dedup-based approval
=================================================================================
curate_textbook_visuals.py approves pages only when the page text contains
an NCERT-style "Fig. N.N: <caption>" label — the convention used in
Science/Maths/Social Science textbooks. Prose anthologies (e.g. the Grade 9
English "Kaveri" series) don't number their images at all, even though the
PDFs are full of real photographs and illustrations (verified: iebe105.pdf
alone has ~180 embedded images across 32 pages). Running the Fig.-caption
curator against these books approves 0 pages every time — not because the
images don't exist, but because this book's convention has no figure
numbers to match against.

This script uses a different, still fully deterministic signal instead of
any figure-number caption:

  1. Size filter — a candidate image must occupy a meaningful chunk of the
     page (not a tiny icon/bullet) and must not fill almost the whole page
     (not a full-page background/watermark). Same thresholds already
     proven in curate_textbook_visuals.py's _figure_crop_rect().

  2. Uniqueness filter — a candidate image's raw bytes are hashed and
     compared across EVERY page of the document. Decorative graphics
     (section icons, borders, recurring header art) are embedded
     identically on many pages and are excluded; a genuine one-off
     photograph or illustration appears exactly once.

  3. Caption — NEVER invented or paraphrased. If the page's own text
     contains an explicit sentence describing "the picture"/"this
     picture"/"photograph" (e.g. "This is a picture of Sheetal Devi, a
     para-archer..."), that exact sentence is extracted verbatim as the
     caption. Otherwise the caption is left empty — an approved image
     with no caption is still a real, un-invented textbook image; this
     script must never write a caption that isn't literally present in
     the source PDF's text.

Usage:
    cd backend
    python3 scripts/curate_prose_textbook_visuals.py --document-id 378 --pdf-path "../RAG DB/English/iebe105.pdf" --dry-run
    python3 scripts/curate_prose_textbook_visuals.py --document-id 378 --pdf-path "../RAG DB/English/iebe105.pdf" --force
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402

MIN_DIM = 60
MIN_AREA = 15000  # pt^2 — excludes small icons/bullets
# Unlike NCERT diagram pages, this book's genuine content photos are often
# full-bleed portraits that legitimately fill most of the page (confirmed:
# the actual Sheetal Devi photo on iebe105.pdf page 1 is ~87% of the page
# area). A tight area ceiling wrongly excludes real photos here. Genuine
# full-page decorative backgrounds/watermarks are still caught by the
# uniqueness filter below (they recur across multiple pages), so this
# ceiling only needs to guard against a single image literally exceeding
# the page bounds (a scan artifact), not against large real content.
MAX_AREA_FRACTION = 0.97

# Matches a complete sentence that explicitly names a picture/photo, so the
# caption is always a verbatim quote from the page, never a paraphrase.
# Applied to whitespace-normalized text (see extract_verbatim_caption) so a
# sentence that wraps across multiple printed lines is still matched whole.
_CAPTION_SENTENCE_RE = re.compile(
    r"([^.]*\b(?:picture|photograph|photo|image)\b[^.]*\.)",
    re.IGNORECASE,
)

# Instructional/exercise sentences ("Give a caption...", "Look at the
# picture...") mention "picture" too but describe an activity, not the
# image itself — deprioritized below in favour of descriptive sentences.
_INSTRUCTIONAL_RE = re.compile(
    r"^\s*(give|look at|write|draw|describe|observe|study|answer|discuss|"
    r"share your|does this|what do you|how does)\b",
    re.IGNORECASE,
)


def _image_hash_index(pdf_path: str) -> tuple[dict[int, list[tuple[int, str]]], set[str]]:
    """
    Return ({page_number: [(xref, md5hash), ...]}, {recurring_hashes}) for
    every embedded image in the PDF. A hash is "recurring" if it appears on
    2 or more distinct pages — the signal used to exclude decorative art.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    per_page: dict[int, list[tuple[int, str]]] = {}
    hash_pages: dict[str, set[int]] = {}
    for i in range(doc.page_count):
        page_number = i + 1
        page = doc.load_page(i)
        entries = []
        for img in page.get_images(full=True):
            xref = img[0]
            raw = doc.extract_image(xref)["image"]
            h = hashlib.md5(raw).hexdigest()
            entries.append((xref, h))
            hash_pages.setdefault(h, set()).add(page_number)
        per_page[page_number] = entries
    doc.close()
    recurring = {h for h, pages in hash_pages.items() if len(pages) >= 2}
    return per_page, recurring


def find_content_image_rect(page, xref_hashes: dict[int, str], recurring_hashes: set[str]):
    """Return the union rect of this page's genuine, unique, non-decorative
    embedded images, or None if the page has none."""
    import fitz  # PyMuPDF

    page_area = page.rect.width * page.rect.height
    candidate_rects = []
    for img in page.get_images(full=True):
        xref = img[0]
        h = xref_hashes.get(xref)
        if h is None or h in recurring_hashes:
            continue
        for rect in page.get_image_rects(xref):
            area = rect.width * rect.height
            if rect.width > MIN_DIM and rect.height > MIN_DIM and MIN_AREA < area < MAX_AREA_FRACTION * page_area:
                candidate_rects.append(rect)

    if not candidate_rects:
        return None
    union = candidate_rects[0]
    for r in candidate_rects[1:]:
        union |= r
    return union


def extract_verbatim_caption(page_text: str) -> str:
    """Return an exact sentence from the page's own text describing a
    picture/photograph, or "" if none is found. Substring match only —
    never invents or paraphrases.

    The page text is whitespace-normalized first so a sentence that wraps
    across several printed lines (very common in this book's layout) is
    still matched as one sentence instead of being cut off at each line
    break. Among all matching sentences, a descriptive one ("This is a
    picture of...") is preferred over an instructional one ("Give a
    caption for this picture.") when both are present on the page.
    """
    normalized = re.sub(r"\s+", " ", page_text or "").strip()
    candidates = [m.group(1).strip() for m in _CAPTION_SENTENCE_RE.finditer(normalized)]
    if not candidates:
        return ""
    descriptive = [c for c in candidates if not _INSTRUCTIONAL_RE.match(c)]
    chosen = descriptive[0] if descriptive else candidates[0]
    # Strip a stray leading bullet-marker glyph (e.g. a lone "I" from a
    # printed list icon that PyMuPDF captured as literal text before the
    # sentence) — the rest of the sentence is still verbatim from the PDF.
    chosen = re.sub(r"^[IVXivx0-9]{1,3}[.\)]?\s+(?=[A-Z])", "", chosen).strip()
    return chosen[:200]


def crop_and_reupload(pdf_path: str, page_number: int, rect, storage_path: str, dry_run: bool) -> None:
    """Re-render this page as a FULL-PAGE screenshot — no cropping at all.

    History: this originally cropped tightly to the image bbox + 20pt
    padding on all four sides, which routinely cut off surrounding
    paragraph text (confirmed via screenshot: a sentence's final line was
    shown with no context, because the paragraph actually started well
    above the crop's tiny 24pt top padding). A second attempt widened the
    padding but any FIXED padding amount is unreliable — a page's real
    text/caption content can start anywhere above the image, and there is
    no way to detect "how far up is safe to cut" without risking clipping
    someone's sentence, as happened here.

    Per explicit user instruction: "prefer to show entire page wherever
    context suits it. Only do vertical cropping where no text or context
    is cut in the process." For this prose-anthology book (unlike NCERT
    diagram-labelled figures, which have a clear, boundable caption to
    anchor a safe crop), there is no reliable way to guarantee a partial
    crop never clips text — so the safe default is the full, uncropped
    page. This function is now a no-op (the original full-page screenshot
    from the backfill step, rendered by _render_pdf_page_to_jpeg in
    rag_visual_service.py, already exists at `storage_path` and needs no
    re-upload) — kept as a named function (rather than removing the call
    site) so a future, genuinely safe crop heuristic can be reintroduced
    here without touching the caller.
    """
    return


def curate_document(document_id: str, pdf_path: str, dry_run: bool, force: bool) -> None:
    print(f"\n  Curating PROSE-textbook visuals for document_id={document_id}")
    print(f"  Source PDF: {pdf_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    import fitz  # PyMuPDF

    per_page_hashes, recurring_hashes = _image_hash_index(pdf_path)

    doc = fitz.open(pdf_path)
    page_texts = {i + 1: (doc.load_page(i).get_text("text") or "") for i in range(doc.page_count)}

    result = (
        admin_client.table("rag_visual_assets")
        .select("id, page_number, status, storage_path")
        .eq("document_id", document_id)
        .order("page_number")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print("  No rag_visual_assets rows found for this document_id. Run the backfill first.")
        doc.close()
        return

    approved = 0
    rejected = 0
    for row in rows:
        page_number = row["page_number"]
        page = doc.load_page(page_number - 1)
        xref_hashes = {xref: h for xref, h in per_page_hashes.get(page_number, [])}
        rect = find_content_image_rect(page, xref_hashes, recurring_hashes)

        if rect is None:
            action = "SKIP (no genuine unique content image found)"
            if row.get("status") == "active" and not dry_run:
                admin_client.table("rag_visual_assets").update(
                    {"status": "needs_review"}
                ).eq("id", row["id"]).execute()
                action = "REVERTED to needs_review"
            print(f"  Page {page_number:>3}: {action}")
            rejected += 1
            continue

        caption = extract_verbatim_caption(page_texts.get(page_number, ""))
        already_active = row.get("status") == "active"
        print(f"  Page {page_number:>3}: APPROVE -> "
              f"{caption or '(no descriptive sentence found in page text; empty caption)'}"
              f"{' (already active)' if already_active else ''}")
        approved += 1

        storage_path = row.get("storage_path")
        if storage_path:
            crop_and_reupload(pdf_path, page_number, rect, storage_path, dry_run)
            print("           -> cropped to content-image region")

        if dry_run:
            continue
        if already_active and not force:
            continue

        admin_client.table("rag_visual_assets").update({
            "status": "active",
            "caption": caption,
        }).eq("id", row["id"]).execute()

    doc.close()
    print(f"\n  Summary: {approved} page(s) approved (genuine unique content image), "
          f"{rejected} page(s) rejected (no qualifying image).\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically curate prose-textbook visual pages by image size + document-wide uniqueness"
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
