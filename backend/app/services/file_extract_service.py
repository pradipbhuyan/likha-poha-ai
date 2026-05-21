import os
import tempfile

from pypdf import PdfReader
from docx import Document
from pptx import Presentation

from app.services.ocr_service import extract_text_from_image_bytes


IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

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