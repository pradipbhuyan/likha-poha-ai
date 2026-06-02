import os
import tempfile

from pypdf import PdfReader
from docx import Document
from pptx import Presentation

from app.services.ocr_service import extract_text_from_image_bytes


IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MIN_USEFUL_PAGE_WORDS = 12

def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        reader = PdfReader(tmp_path)
        text_parts = []

        for page in reader.pages:
            text_parts.append(page.extract_text() or "")

        return "\n\n".join(text_parts).strip()

    finally:
        os.remove(tmp_path)


def count_words(text: str) -> int:
    return len(text.split())


def build_extracted_page(
    *,
    filename: str,
    page_number: int,
    text: str,
    extraction_method: str,
    warnings: list[str] | None = None,
) -> dict:
    clean_text = (text or "").strip()
    page_warnings = list(warnings or [])

    if count_words(clean_text) < MIN_USEFUL_PAGE_WORDS:
        page_warnings.append("Low text detected. Review OCR quality before upload.")

    return {
        "filename": filename,
        "page_number": page_number,
        "text": clean_text,
        "extraction_method": extraction_method,
        "word_count": count_words(clean_text),
        "warnings": page_warnings,
    }


def ocr_pdf_page_images(page) -> str:
    text_parts = []

    for image in getattr(page, "images", []) or []:
        try:
            image_text = extract_text_from_image_bytes(image.data)

            if image_text.strip():
                text_parts.append(image_text)
        except Exception:
            continue

    return "\n\n".join(text_parts).strip()


def extract_pages_from_pdf(filename: str, file_bytes: bytes) -> list[dict]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        reader = PdfReader(tmp_path)
        pages = []

        for page_index, page in enumerate(reader.pages, start=1):
            warnings = []
            text = (page.extract_text() or "").strip()
            extraction_method = "pdf_text"

            if count_words(text) < MIN_USEFUL_PAGE_WORDS:
                ocr_text = ocr_pdf_page_images(page)

                if ocr_text:
                    text = ocr_text
                    extraction_method = "pdf_embedded_image_ocr"
                else:
                    warnings.append(
                        "PDF page may be scanned. No embedded image text could be extracted."
                    )

            pages.append(
                build_extracted_page(
                    filename=filename,
                    page_number=page_index,
                    text=text,
                    extraction_method=extraction_method,
                    warnings=warnings,
                )
            )

        return pages

    finally:
        os.remove(tmp_path)


def extract_text_from_docx(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = Document(tmp_path)
        return "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
            if paragraph.text.strip()
        )

    finally:
        os.remove(tmp_path)


def extract_text_from_pptx(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        prs = Presentation(tmp_path)
        text_parts = []

        for slide_number, slide in enumerate(prs.slides, start=1):
            text_parts.append(f"\nSlide {slide_number}\n")

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text_parts.append(shape.text)

        return "\n".join(text_parts).strip()

    finally:
        os.remove(tmp_path)


def extract_text_from_uploaded_file(filename: str, file_bytes: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]

    if ext in IMAGE_EXTENSIONS:
        return extract_text_from_image_bytes(file_bytes)
    
    if ext == ".txt":
        return extract_text_from_txt(file_bytes)

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)

    if ext == ".docx":
        return extract_text_from_docx(file_bytes)

    if ext == ".pptx":
        return extract_text_from_pptx(file_bytes)

    if ext in [".doc", ".ppt"]:
        raise ValueError(
            "Legacy .doc/.ppt files are not directly supported yet. "
            "Please convert them to .docx/.pptx first."
        )

    raise ValueError(
        "Unsupported file type. Supported: txt, jpg, jpeg, png, webp, pdf, docx, pptx."
    )


def extract_pages_from_uploaded_file(filename: str, file_bytes: bytes) -> list[dict]:
    ext = os.path.splitext(filename.lower())[1]

    if ext in IMAGE_EXTENSIONS:
        return [
            build_extracted_page(
                filename=filename,
                page_number=1,
                text=extract_text_from_image_bytes(file_bytes),
                extraction_method="image_ocr",
            )
        ]

    if ext == ".pdf":
        return extract_pages_from_pdf(filename, file_bytes)

    if ext == ".txt":
        return [
            build_extracted_page(
                filename=filename,
                page_number=1,
                text=extract_text_from_txt(file_bytes),
                extraction_method="text",
            )
        ]

    if ext == ".docx":
        return [
            build_extracted_page(
                filename=filename,
                page_number=1,
                text=extract_text_from_docx(file_bytes),
                extraction_method="docx_text",
            )
        ]

    if ext == ".pptx":
        return [
            build_extracted_page(
                filename=filename,
                page_number=1,
                text=extract_text_from_pptx(file_bytes),
                extraction_method="pptx_text",
            )
        ]

    if ext in [".doc", ".ppt"]:
        raise ValueError(
            "Legacy .doc/.ppt files are not directly supported yet. "
            "Please convert them to .docx/.pptx first."
        )

    raise ValueError(
        "Unsupported file type. Supported: txt, jpg, jpeg, png, webp, pdf, docx, pptx."
    )
