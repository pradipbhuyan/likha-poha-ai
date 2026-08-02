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

# NCERT figure caption pattern — three conventions verified across
# different textbook series:
#   - Exploration series (Science): COLON right after the figure number:
#       "Fig. 2.13: Endoplasmic reticulum and Golgi apparatus..."
#   - Understanding Society series (Social Science, 2026 edition): PERIOD
#     right after the figure number, often with a very short 1-3 word
#     caption (labels like a place/landform name rather than a full
#     sentence):
#       "Fig. 2.10. Waterfall"
#       "Fig. 2.3. World map showing major plates and their direction of movement"
#   - Same series, multi-panel infographic figures: NO punctuation at
#     all — the figure number sits alone on its own line, followed
#     immediately by the panel/box label on the next line:
#       "Fig. 6.5\nTeam A\nAll students gather in one place..."
#     (confirmed on the Democracy chapter, iest106.pdf page 11 — this
#     figure was referenced extensively in GPT-5.5's generated lesson
#     text ("Fig. 6.5 Team A/B/C/D") but was never attached as an image
#     because this caption style silently failed to match either of the
#     colon/period patterns above.)
# All three are genuine, deterministic NCERT captions — only an in-text
# reference (pointing to a figure discussed elsewhere) differs, using a
# closing parenthesis directly after the number instead of a colon,
# period, or newline:
#       "...different parts of a microscope (Fig. 2.2) in your school..."
# Requiring a colon, period, OR newline immediately after "Fig. N.N"
# (never a closing paren) is what keeps this deterministic and excludes
# in-text references like "(Fig. 2.9)" from being mistaken for captions.
# The period after "Fig"/"Figure" is OPTIONAL (confirmed live for
# Grade 11 Mathematics, NCERT's "kemh1" series: it consistently prints
# bare "Fig 9.1" captions with NO period, unlike most other NCERT books
# which print "Fig. 9.1" -- without this fix, every genuine caption in
# this book was silently rejected and 0 images were ever approved for
# any Grade 11 Maths chapter, even heavily-illustrated ones like
# Straight Lines and Conic Sections.
_FIG_CAPTION_RE = re.compile(
    r"Fig(?:ure)?\.?[\s\xa0]*(\d+\.\d+)(?:\s*[:.]\s*|\s*\n\s*)([^\n]{2,140})",
    re.IGNORECASE,
)
# A THIRD genuine-caption style, confirmed live for Grade 11 Biology
# ("kebo1" series): captions are printed as "Figure 19.1 Location of
# endocrine glands" -- number and description separated by only a
# SPACE, no colon/period/newline at all. Without this, every genuine
# caption in this book was silently rejected (0 images ever approved
# for figure-heavy chapters like "Chemical Coordination and
# Integration", which has 5 real diagrams). This is intentionally a
# SEPARATE, more restrictive pattern (not merged into _FIG_CAPTION_RE
# above) because requiring the description to start with a capital
# letter immediately after the number, on the SAME line, is the only
# way to distinguish a genuine caption line from an in-text reference
# like "...is shown in Figure 19.2 and it regulates..." (which also has
# just a space after the number, but continues in lowercase prose).
# The overall match is additionally required to start a fresh line by
# the caller (see the fig_starts_new_line check in
# extract_figure_captions below), matching how the colon/period style
# above is already guarded against in-text "(Fig. 2.9)" references.
_FIG_CAPTION_SPACE_RE = re.compile(
    r"Fig(?:ure)?\.?[\s\xa0]+(\d+\.\d+)[\s\xa0]+([A-Z][^\n]{1,140})",
    re.IGNORECASE,
)


def extract_figure_captions(nearby_text: str, expected_chapter: str | None = None) -> list[tuple[str, str]]:
    """
    Return [(fig_number, caption_text), ...] for every genuine NCERT
    figure caption found in this page's extracted text.

    Requires the colon- or period-separated "Fig. N.N: <description>" /
    "Fig. N.N. <description>" form (see module docstring) AND at least
    1 real word of description -- this excludes both bare in-text
    references like "(Fig. 2.2)" and caption-less figure labels like
    "Fig. 2.20" followed immediately by an unrelated lettered exercise
    list with no real words after it.

    The minimum word count is intentionally low (1, not 3) because the
    Understanding Society series often uses single-word captions that
    are still genuine, printed NCERT captions (e.g. "Fig. 2.10. Waterfall",
    "Fig. 2.11. Meander", "Fig. 2.12. Delta") -- requiring 3+ words would
    incorrectly reject these real captions.

    expected_chapter, if given (e.g. "9" for iest109.pdf), rejects any
    match whose figure-number chapter prefix does NOT equal it -- this
    catches "Image Credits" appendix leakage where a WHOLE-BOOK credits
    page lists "Fig. 4.1: Seal from Mohenjodaro...; p.93, Corpus of..."
    inside chapter 9's page range: a caption citing "Fig. 4.1" cannot be
    a genuine figure in chapter 9, so this is a strong, deterministic
    signal of credits-page bleed rather than a real pedagogical caption.

    A newline-separated "caption" (the regex's \n-branch, used when a
    figure number is followed by a line break rather than ": "/". " on
    the SAME line) is only trusted when "Fig" itself starts a fresh
    line in the source text -- i.e. it is the label printed directly
    under a diagram. If "Fig N.N" instead appears mid-sentence (an
    in-text reference like "...is shown in Fig 9.1.") followed by a
    line break into the NEXT paragraph's body text, that unrelated body
    text must NOT be captured as if it were a genuine caption (confirmed
    live for Grade 11 Mathematics page 1 of kemh109.pdf).
    """
    text = nearby_text or ""
    results = []
    for match in _FIG_CAPTION_RE.finditer(text):
        fig_number = match.group(1)
        caption_text = match.group(2).strip()

        fig_start = match.start()
        fig_starts_new_line = fig_start == 0 or text[fig_start - 1] in "\n\r"
        # The regex's second capture group is on a fresh line relative to
        # the figure number only when the raw matched text contains a
        # newline between the number and the caption start.
        num_to_caption_gap = match.group(0)[len(match.group(0)) - len(match.group(2)) - len(caption_text) : len(match.group(0)) - len(caption_text)]
        caption_on_new_line = "\n" in match.group(0)[match.group(0).find(fig_number) + len(fig_number):match.group(0).rfind(caption_text)] if caption_text else False
        if caption_on_new_line and not fig_starts_new_line:
            # In-text reference (e.g. "...shown in Fig 9.1.\nNext para...")
            # -- reject, this is not a genuine caption.
            continue

        # A genuine caption has at least one real word (letters), not just
        # trailing punctuation, page numbers, or whitespace.
        if not re.search(r"[A-Za-z]", caption_text):
            continue
        if len(caption_text.split()) < 1:
            continue
        # Reject "captions" that are themselves just the START of the
        # NEXT bare figure label (confirmed live for Grade 11
        # Mathematics: consecutive stacked labels like "Fig 9.2\nFig 9.
        # 3 (i)\n" must not let the \n-branch of the regex swallow
        # "Fig 9. 3 (i)" as if it were fig 9.2's genuine caption text).
        if re.match(r"^Fig(?:ure)?\.?\s", caption_text, re.IGNORECASE):
            continue
        # Reject the page-footer "Reprint YYYY-YY" artifact being
        # swallowed as if it were the genuine caption text (confirmed
        # live for Grade 11 Mathematics kemh106.pdf page 2: raw text is
        # "...Fig. 6.2.\nFig 6.1\nFig 6.2\nReprint 2026-27\n" -- the
        # SECOND bare "Fig 6.2" label starts a fresh line, so it passes
        # the earlier check, but its "caption" is only the following
        # page-footer stamp, not a real description).
        if re.match(r"^Reprint\s+\d{4}-\d{2,4}\s*$", caption_text, re.IGNORECASE):
            continue
        # Reject figures whose chapter-number prefix doesn't match this
        # PDF's own chapter -- the clearest signal of credits-page bleed.
        if expected_chapter and fig_number.split(".")[0] != expected_chapter:
            continue
        # Reject "Image Credits" appendix entries -- the book's end-of-volume
        # credits page lists "Fig. N.N. <source/attribution>" for EVERY
        # figure across the WHOLE book (not just this chapter), and this
        # section can get swept into a chapter's backfilled page range when
        # it immediately follows the last chapter's content. These are
        # never genuine pedagogical captions -- confirmed on iest109.pdf's
        # trailing pages, e.g. "Fig. 5.1. https://commons.wikimedia.org/...",
        # "Fig. 2.32. Public domain", "Fig. 4.25. Wikimedia Commons: ...",
        # "Fig. 4.1. Seal from Mohenjodaro M375A; p.93..., Corpus of...".
        if re.search(
            r"https?://|www\.|courtesy\s*:|public domain|wikimedia|"
            r"shutterstock|getty\s*images|istock|\u00a9|copyright|"
            r"\bp\.\s*\d+\b|corpus of",
            caption_text, re.IGNORECASE,
        ):
            continue
        # Reject comma-separated lists of OTHER figure numbers -- a genuine
        # caption describes what the figure shows in prose; a credits-page
        # line instead just enumerates sibling figure numbers sharing one
        # attribution, e.g. "Fig. 2.9. (b), 2.10, 2.11, 2.12, 2.14, 2.15...".
        if len(re.findall(r"\b\d+\.\d+\b", caption_text)) >= 2:
            continue
        results.append((fig_number, caption_text))

    if results:
        return results

    # SECOND pass: space-separated caption style (see
    # _FIG_CAPTION_SPACE_RE docstring above). Only attempted after the
    # primary colon/period/newline styles find nothing, so it cannot
    # mask a real caption already found by the primary pattern.
    for match in _FIG_CAPTION_SPACE_RE.finditer(text):
        fig_number = match.group(1)
        caption_text = match.group(2).strip()

        fig_start = match.start()
        fig_starts_new_line = fig_start == 0 or text[fig_start - 1] in "\n\r"
        if not fig_starts_new_line:
            # Mid-sentence in-text reference (e.g. "...is shown in
            # Figure 19.2 and it regulates...") -- reject. A genuine
            # caption is always printed as its own line, directly under
            # the diagram.
            continue
        if expected_chapter and fig_number.split(".")[0] != expected_chapter:
            continue
        if re.search(
            r"https?://|www\.|courtesy\s*:|public domain|wikimedia|"
            r"shutterstock|getty\s*images|istock|\u00a9|copyright|"
            r"\bp\.\s*\d+\b|corpus of",
            caption_text, re.IGNORECASE,
        ):
            continue
        if len(re.findall(r"\b\d+\.\d+\b", caption_text)) >= 2:
            continue
        results.append((fig_number, caption_text))

    if results:
        return results

    # Fallback for NCERT books that print BARE figure labels with no
    # descriptive text at all under the diagram itself (confirmed live
    # for Grade 11 Mathematics, "kemh1" series: e.g. page text literally
    # contains "Fig 9.2\nFig 9. 3 (i)\nReprint 2026-27\n" with nothing
    # descriptive between the label and the next figure/footer). This
    # fallback only fires when the primary pass above found ZERO
    # genuine captions on the page, so it cannot mask a real caption.
    bare_label_re = re.compile(
        r"^Fig(?:ure)?\.?[\s\xa0]*(\d+\.\s?\d+)\s*(?:\([a-z]+\))?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    bare_results = []
    for match in bare_label_re.finditer(text):
        fig_number = match.group(1).replace(" ", "")
        if expected_chapter and fig_number.split(".")[0] != expected_chapter:
            continue
        bare_results.append((fig_number, ""))
    return bare_results


def page_has_large_embedded_photo(pdf_path: str, page_number: int) -> bool:
    """
    True if this page contains at least one substantial embedded raster
    image, with no attempt to detect a caption at all.

    Used as a fallback approval path for chapters whose source PDF
    genuinely has ZERO "Fig N.N" caption occurrences anywhere (confirmed
    live for every one of Grade 11 English's 11 chapters: NCERT's
    literature readers -- Hornbill and Snapshots -- illustrate almost
    every page with uncaptioned photographs/illustrations rather than
    science-style numbered figures, e.g. kehb103.pdf "Discovering Tut:
    the Saga Continues" has 3-5 embedded images on every one of its 14
    pages, yet 0 "Fig N.N" mentions anywhere in the book -- the primary
    caption-based approval logic correctly finds no genuine NCERT figure
    caption on any page, but this left the ENTIRE subject showing 0
    active images despite being visually rich with real photographs).

    Deliberately permissive on image size compared to
    extract_figure_captions()'s companion crop-region filter
    (_figure_crop_rect, used only for cropping an ALREADY-approved
    page) -- this function's only job is to decide whether a page is
    worth approving at all, so a large "background-style" image (which
    _figure_crop_rect intentionally EXCLUDES from its crop-region
    calculation, since a true watermark should not define the crop
    box) is still valid evidence of a genuine photograph here. Only
    truly tiny decorative elements (page-corner icons, bullet dots) are
    excluded, matching the same >60x60px minimum used elsewhere in this
    file.
    """
    import fitz  # PyMuPDF

    pdf_document = fitz.open(pdf_path)
    try:
        page = pdf_document.load_page(page_number - 1)
        page_area = page.rect.width * page.rect.height
        for img in page.get_images(full=True):
            xref = img[0]
            for rect in page.get_image_rects(xref):
                if rect.width <= 60 or rect.height <= 60:
                    continue  # tiny decorative icon/bullet
                rect_area = rect.width * rect.height
                if rect_area / page_area >= 0.10:
                    return True
        return False
    finally:
        pdf_document.close()


def build_caption(fig_number: str, caption_text: str) -> str:
    """Build the display caption exactly as printed in the NCERT text.

    caption_text may be empty for the bare-figure-label fallback (books
    with no printed description under the diagram, e.g. Grade 11
    Mathematics) -- in that case omit the trailing colon entirely
    rather than producing an ugly "Fig. 9.2:" with nothing after it.
    """
    if not caption_text:
        return f"Fig. {fig_number}"
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
        rf"Fig(?:ure)?\.[\s\xa0]*{re.escape(fig_number)}\s*[:.\n]", re.IGNORECASE,
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


# NCERT book-code filenames end in a 2-digit chapter number, e.g.
# "iest106" (book code "iest1" + chapter "06"). Stripping the trailing
# 2 digits and converting to int removes the leading zero so it matches
# the "6" in a "Fig. 6.5" match's chapter-number group. This is only a
# best-effort signal for the credits-page cross-check in
# extract_figure_captions() — filenames that don't end in exactly 2
# digits are simply skipped (falls back to the other credits filters).
_CHAPTER_NUM_RE = re.compile(r"(\d{2})$")
# Bare "Fig N.N" / "Fig. N.N" occurrences anywhere in the page text --
# used to VOTE on the real chapter number across the whole PDF, since
# neither the filename-based guess NOR a printed page-1 heading can be
# trusted for every NCERT book. Confirmed live for Grade 11 Chemistry's
# Part-II volume (kech2*.pdf): "kech201.pdf" is actually Chapter 7
# (Redox Reactions), but its filename-based 2-digit suffix ("01")
# wrongly guesses chapter "1" (this book restarts its OWN internal
# filename numbering per physical volume/part, unlike most single-
# volume NCERT books). Attempting to read a page-1 printed heading also
# failed for all 3 of this volume's chapters: kech201.pdf's page 1 has
# no chapter-number text at all (rendered as a decorative graphic, not
# extractable text), and kech202.pdf/kech203.pdf's page-1 text is
# corrupted by a non-standard font encoding (garbled Unicode). The most
# robust signal across ALL observed NCERT books is simply: whichever
# chapter-prefix appears most often among this PDF's own "Fig N.N"
# occurrences IS this chapter's real number -- a few outlier citations
# to other chapters (e.g. credits-page bleed, or a genuine cross-
# reference to an earlier chapter's figure) will never outnumber the
# chapter's own real figures.
_BARE_FIG_NUM_RE = re.compile(r"Fig(?:ure)?\.?[\s\xa0]+(\d+)\.\d+", re.IGNORECASE)


def _guess_chapter_number(pdf_path: str, all_page_texts: dict[int, str] | None = None) -> str | None:
    """Best-effort chapter number for this PDF.

    Primary strategy: vote across every "Fig N.N" occurrence in the
    whole PDF (all_page_texts) and take the most frequent chapter
    prefix N -- this is robust even when neither the filename nor any
    single page's printed heading reliably states the chapter number
    (confirmed necessary for Grade 11 Chemistry's Part-II volume).

    Falls back to the filename-based guess (book-code + trailing
    2-digit suffix, e.g. iest106.pdf -> chapter 6) only when no page
    text is supplied or no "Fig N.N" occurrences exist anywhere in the
    PDF (e.g. a chapter with zero figures at all)."""
    if all_page_texts:
        from collections import Counter  # noqa: PLC0415
        votes = Counter()
        for text in all_page_texts.values():
            for match in _BARE_FIG_NUM_RE.finditer(text or ""):
                votes[match.group(1)] += 1
        if votes:
            return votes.most_common(1)[0][0]
    stem = Path(pdf_path).stem
    match = _CHAPTER_NUM_RE.search(stem)
    return str(int(match.group(1))) if match else None


def curate_document(document_id: str, pdf_path: str, dry_run: bool, force: bool) -> None:
    print(f"\n  Curating visuals for document_id={document_id}")
    print(f"  Source PDF: {pdf_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    page_texts = load_full_page_texts(pdf_path)
    expected_chapter = _guess_chapter_number(pdf_path, page_texts)
    # If this PDF has ZERO "Fig N.N" occurrences anywhere, _guess_chapter_
    # number() falls through to its filename-based guess and returns a
    # (likely meaningless) chapter number rather than None. Detect that
    # exact "no figures anywhere" condition directly, since it is also the
    # trigger condition for the photo-essay fallback mode below (e.g.
    # Grade 11 English's literature readers, which have real uncaptioned
    # photographs but never print an NCERT-style "Fig N.N" caption).
    has_any_fig_caption_in_book = any(
        _BARE_FIG_NUM_RE.search(text or "") for text in page_texts.values()
    )
    photo_essay_mode = not has_any_fig_caption_in_book
    if photo_essay_mode:
        print("  No 'Fig N.N' captions found anywhere in this PDF -- "
              "using photo-essay fallback mode (approve pages with a "
              "substantial embedded photograph, generic caption).\n")

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

        captions = extract_figure_captions(full_text, expected_chapter=expected_chapter)

        if not captions:
            # PHOTO-ESSAY FALLBACK: this whole book has no "Fig N.N"
            # captions anywhere (see photo_essay_mode above), so fall
            # back to approving any page with a substantial embedded
            # photograph, using a generic caption since there is no
            # printed figure number/description to extract. This never
            # fires for books that DO use NCERT's figure-caption
            # convention (photo_essay_mode is only True for the whole
            # book, decided once before this loop), so it cannot mask a
            # genuine caption-detection failure on a normal science-style
            # textbook page.
            if photo_essay_mode and page_has_large_embedded_photo(pdf_path, page_number):
                new_caption = "Photograph"
                already_active = current_status == "active"
                print(f"  Page {page_number:>3}: APPROVE (photo-essay fallback) -> {new_caption}"
                      f"{' (already active)' if already_active else ''}")
                approved_count += 1
                if not dry_run and not (already_active and not force):
                    admin_client.table("rag_visual_assets").update({
                        "status": "active",
                        "caption": new_caption,
                    }).eq("id", row["id"]).execute()
                continue

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
