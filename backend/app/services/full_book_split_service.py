import io
import os
import re
import tempfile
from dataclasses import dataclass

from pypdf import PdfReader

from app.services.file_extract_service import count_words
from app.services.ocr_service import extract_text_from_image_bytes


MIN_FULL_BOOK_TEXT_WORDS = 200
MAX_FULL_BOOK_PAGES = 220


@dataclass
class FullBookPage:
    """Per-page text extracted from a full textbook PDF."""

    page_number: int
    text: str
    word_count: int
    extraction_method: str


def get_pdf_page_count(file_bytes: bytes) -> int:
    """Return page count for a PDF without extracting all content."""
    reader = PdfReader(io.BytesIO(file_bytes))
    return len(reader.pages)


def extract_pdf_text_pages(
    filename: str,
    file_bytes: bytes,
    progress_callback=None,
) -> list[FullBookPage]:
    """Extract embedded text per page from a PDF."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        page_count = len(reader.pages)

        for page_index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append(
                FullBookPage(
                    page_number=page_index,
                    text=text,
                    word_count=count_words(text),
                    extraction_method="pdf_text",
                )
            )
            if progress_callback:
                progress_callback(
                    phase="extracting_pages",
                    processed_pages=page_index,
                    page_count=page_count,
                    message=f"Extracted text from page {page_index} of {page_count}.",
                )

        return pages
    except Exception:
        if progress_callback:
            progress_callback(
                phase="extracting_pages",
                processed_pages=0,
                page_count=0,
                message="Standard PDF extraction failed. Retrying with PyMuPDF.",
            )

        return extract_pdf_text_pages_with_pymupdf(
            filename,
            file_bytes,
            progress_callback,
        )


def extract_pdf_text_pages_with_pymupdf(
    filename: str,
    file_bytes: bytes,
    progress_callback=None,
) -> list[FullBookPage]:
    """Fallback PDF text extraction for compressed PDFs that pypdf cannot parse."""
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise RuntimeError(
            "PDF text extraction failed and PyMuPDF fallback is unavailable. "
            "Install backend requirement PyMuPDF and redeploy."
        ) from exc

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    document = None
    try:
        document = fitz.open(tmp_path)
        page_count = document.page_count
        pages = []

        for page_index in range(page_count):
            text = (document.load_page(page_index).get_text("text") or "").strip()
            pages.append(
                FullBookPage(
                    page_number=page_index + 1,
                    text=text,
                    word_count=count_words(text),
                    extraction_method="pdf_text_pymupdf",
                )
            )
            if progress_callback:
                progress_callback(
                    phase="extracting_pages",
                    processed_pages=page_index + 1,
                    page_count=page_count,
                    message=f"Extracted text from page {page_index + 1} of {page_count}.",
                )

        return pages
    finally:
        if document is not None:
            document.close()
        os.remove(tmp_path)


def render_pdf_page_to_jpeg(file_bytes: bytes, page_index: int) -> bytes:
    """
    Render one PDF page to JPEG bytes for OCR.

    PyMuPDF is imported lazily so normal text-PDF uploads do not require it at
    import time. Deployment must install PyMuPDF for scanned full-book OCR.
    """
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise RuntimeError(
            "Scanned full-book OCR requires PyMuPDF. Install backend requirement "
            "PyMuPDF and redeploy, or upload a searchable/OCR PDF."
        ) from exc

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    document = None
    try:
        document = fitz.open(tmp_path)
        page = document.load_page(page_index)
        # 1.5x scaling balances readability and OpenAI image payload size.
        matrix = fitz.Matrix(1.5, 1.5)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("jpeg", jpg_quality=80)
    finally:
        if document is not None:
            document.close()
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def extract_full_book_pages(
    *,
    filename: str,
    file_bytes: bytes,
    ocr_scanned: bool = False,
    max_pages: int = MAX_FULL_BOOK_PAGES,
    progress_callback=None,
) -> tuple[list[FullBookPage], list[str]]:
    """
    Extract full-book page text using embedded text, optionally OCRing scanned pages.

    The function raises a clear error for scanned PDFs unless OCR is explicitly
    enabled, preventing the old bad behavior where a full book became one
    publisher-front-matter chunk.
    """
    page_count = get_pdf_page_count(file_bytes)
    if progress_callback:
        progress_callback(
            phase="extracting_pages",
            page_count=page_count,
            processed_pages=0,
            message=f"Starting text extraction for {page_count} pages.",
        )

    if page_count > max_pages:
        raise ValueError(
            f"This PDF has {page_count} pages. Full-book splitting currently supports "
            f"up to {max_pages} pages per upload."
        )

    pages = extract_pdf_text_pages(filename, file_bytes, progress_callback)
    total_words = sum(page.word_count for page in pages)
    warnings = []

    if total_words >= MIN_FULL_BOOK_TEXT_WORDS:
        if progress_callback:
            progress_callback(
                phase="extracted_pages",
                page_count=page_count,
                processed_pages=page_count,
                message="Readable PDF text extracted.",
            )
        return pages, warnings

    if not ocr_scanned:
        raise ValueError(
            "This PDF appears to be scanned or image-based. "
            f"Only {total_words} readable words were extracted from {page_count} pages. "
            "Turn on OCR for scanned PDF, upload chapter images, or upload a searchable/OCR PDF."
        )

    ocr_pages = []

    for page_index in range(page_count):
        image_bytes = render_pdf_page_to_jpeg(file_bytes, page_index)
        text = (extract_text_from_image_bytes(image_bytes) or "").strip()
        ocr_pages.append(
            FullBookPage(
                page_number=page_index + 1,
                text=text,
                word_count=count_words(text),
                extraction_method="pdf_page_ocr",
            )
        )
        if progress_callback:
            progress_callback(
                phase="ocr_pages",
                page_count=page_count,
                processed_pages=page_index + 1,
                message=f"OCR completed for page {page_index + 1} of {page_count}.",
            )

    ocr_words = sum(page.word_count for page in ocr_pages)

    if ocr_words < MIN_FULL_BOOK_TEXT_WORDS:
        warnings.append(
            f"OCR extracted only {ocr_words} words from {page_count} pages. Review carefully before upload."
        )

    return ocr_pages, warnings


def clean_chapter_title(title: str) -> str:
    """Normalize noisy chapter labels for dropdown display."""
    cleaned = re.sub(r"\s+", " ", title or "").strip(" :-–—")
    cleaned = re.sub(r"\bpage\s+\d+\b", "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned


def normalize_title_for_match(title: str) -> str:
    """Create a compact comparison key for noisy PDF-extracted titles."""
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def extract_numbered_contents_titles(pages: list[FullBookPage]) -> list[dict]:
    """
    Extract lesson/chapter titles from early table-of-contents pages.

    Some English reader books do not print "Chapter" on lesson starts; their
    reliable structure is the Contents page plus numbered story titles such as
    "1. The Lost Child ..... 1". These titles then anchor page ranges.
    """
    contents_titles = []
    seen = set()

    for page in pages[:20]:
        text = page.text or ""

        if "contents" not in text.lower() and not re.search(r"\.{2,}\s*\d", text):
            continue

        for raw_line in text.splitlines():
            line = clean_chapter_title(raw_line)
            match = re.match(
                r"^(\d{1,2})\.\s+(.+?)\s*(?:\.{2,}|…+|\s{2,})\s*([\d\sivxlcdm]+)$",
                line,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            number = int(match.group(1))
            title = clean_chapter_title(match.group(2))
            printed_page_text = re.sub(r"\s+", "", match.group(3))
            printed_page = int(printed_page_text) if printed_page_text.isdigit() else None
            title = re.sub(r"\s+", " ", title)
            match_key = normalize_title_for_match(title)

            if len(match_key) < 5 or match_key in seen:
                continue

            seen.add(match_key)
            contents_titles.append(
                {
                    "number": number,
                    "title": title,
                    "printed_page": printed_page,
                    "toc_page": page.page_number,
                    "match_key": match_key,
                }
            )

    return contents_titles


def chapter_heading_from_page(text: str) -> str:
    """Detect a chapter/unit/lesson heading from the top portion of a page."""
    lines = [
        clean_chapter_title(line)
        for line in (text or "").splitlines()
        if clean_chapter_title(line)
    ]

    top_lines = lines[:14]

    for index, line in enumerate(top_lines):
        match = re.match(
            r"^(chapter|lesson|unit)\s+([0-9ivxlcdm]+)\s*[:.\-–—]?\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        prefix = match.group(1).title()
        number = match.group(2).upper() if not match.group(2).isdigit() else match.group(2)
        title_tail = clean_chapter_title(match.group(3))

        if not title_tail and index + 1 < len(top_lines):
            next_line = top_lines[index + 1]
            if not re.match(r"^(chapter|lesson|unit)\b", next_line, flags=re.IGNORECASE):
                title_tail = next_line

        return f"{prefix} {number}: {title_tail}" if title_tail else f"{prefix} {number}"

    return ""


def detect_chapters_from_contents(pages: list[FullBookPage]) -> list[dict]:
    """Use Contents-page titles to locate lesson starts in reader-style books."""
    contents_titles = extract_numbered_contents_titles(pages)

    if len(contents_titles) < 2:
        return []

    detected = []

    for item in contents_titles:
        start_page = None
        toc_cutoff = item["toc_page"] + 1
        expected_page = None

        if item.get("printed_page") is not None:
            expected_page = item["toc_page"] + item["printed_page"]

        candidate_pages = []

        if expected_page:
            candidate_pages.extend([
                page for page in pages
                if max(toc_cutoff, expected_page - 2) <= page.page_number <= expected_page + 4
            ])

        candidate_pages.extend([
            page for page in pages
            if page.page_number >= toc_cutoff and page not in candidate_pages
        ])

        for page in candidate_pages:
            page_key = normalize_title_for_match(page.text)

            if item["match_key"] in page_key:
                start_page = page.page_number
                break

        if start_page is None:
            continue

        title = f"Chapter {item['number']}: {item['title']}"

        if detected and detected[-1]["title"].lower() == title.lower():
            continue

        detected.append(
            {
                "title": title,
                "start_page": start_page,
                "end_page": start_page,
                "confidence": "High",
                "preview": next(
                    (page.text[:500] for page in pages if page.page_number == start_page),
                    "",
                ),
                "include": True,
            }
        )

    return detected if len(detected) >= 2 else []


def detect_full_book_chapters(pages: list[FullBookPage]) -> list[dict]:
    """
    Build editable chapter ranges from extracted page text.

    Local heading detection is deliberately conservative. Admin review remains
    the source of truth before RAG documents are created.
    """
    detected = detect_chapters_from_contents(pages)

    if not detected:
        detected = []

        for page in pages:
            title = chapter_heading_from_page(page.text)

            if title:
                if detected and detected[-1]["title"].lower() == title.lower():
                    continue

                detected.append({
                    "title": title,
                    "start_page": page.page_number,
                    "end_page": page.page_number,
                    "confidence": "Medium",
                    "preview": page.text[:500],
                    "include": True,
                })

    if not detected:
        return [
            {
                "title": "Uploaded Book Content",
                "start_page": 1,
                "end_page": pages[-1].page_number if pages else 1,
                "confidence": "Low",
                "preview": pages[0].text[:500] if pages else "",
                "include": True,
            }
        ]

    for index, chapter in enumerate(detected):
        if index + 1 < len(detected):
            chapter["end_page"] = max(
                chapter["start_page"],
                detected[index + 1]["start_page"] - 1,
            )
        else:
            chapter["end_page"] = pages[-1].page_number if pages else chapter["start_page"]

    return detected


def combine_pages_for_range(
    pages: list[FullBookPage],
    start_page: int,
    end_page: int,
) -> str:
    """Combine page text for one reviewed chapter range."""
    selected_pages = [
        page for page in pages
        if start_page <= page.page_number <= end_page
    ]

    return "\n\n".join(
        f"Page {page.page_number}\n{page.text}"
        for page in selected_pages
        if page.text.strip()
    ).strip()
