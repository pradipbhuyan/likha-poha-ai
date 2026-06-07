from io import BytesIO

from pypdf import PdfWriter

from app.services import file_extract_service
from app.services.file_extract_service import (
    count_devanagari_chars,
    extract_pages_from_uploaded_file,
    extract_text_from_uploaded_file,
    looks_like_broken_hindi_pdf_text,
)


def test_extract_pages_from_txt_returns_page_metadata():
    pages = extract_pages_from_uploaded_file(
        filename="sof-notes.txt",
        file_bytes=b"Nouns name people, places, animals, and things.",
    )

    assert len(pages) == 1
    assert pages[0]["filename"] == "sof-notes.txt"
    assert pages[0]["page_number"] == 1
    assert pages[0]["extraction_method"] == "text"
    assert "Nouns name people" in pages[0]["text"]
    assert pages[0]["word_count"] > 0


def test_extract_pages_from_low_text_pdf_returns_review_warning():
    pdf_buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(pdf_buffer)

    pages = extract_pages_from_uploaded_file(
        filename="scanned-sof.pdf",
        file_bytes=pdf_buffer.getvalue(),
    )

    assert len(pages) == 1
    assert pages[0]["filename"] == "scanned-sof.pdf"
    assert pages[0]["page_number"] == 1
    assert pages[0]["extraction_method"] == "pdf_text"
    assert pages[0]["word_count"] == 0
    assert pages[0]["warnings"]


def test_multi_page_scanned_pdf_upload_is_rejected_before_rag_chunking():
    """
    A large scanned/image-only PDF should not be accepted as a one-chunk RAG doc.

    This protects full textbook uploads from silently indexing only publisher
    front matter when embedded PDF text is unavailable.
    """
    pdf_buffer = BytesIO()
    writer = PdfWriter()

    for _ in range(12):
        writer.add_blank_page(width=200, height=200)

    writer.write(pdf_buffer)

    try:
        extract_text_from_uploaded_file(
            filename="full-book-scan.pdf",
            file_bytes=pdf_buffer.getvalue(),
        )
    except ValueError as exc:
        assert "appears to be scanned" in str(exc)
        assert "RAG upload was stopped" in str(exc)
    else:
        raise AssertionError("Expected scanned multi-page PDF extraction to fail.")


def test_pdf_text_extraction_falls_back_to_pymupdf_when_pypdf_fails(monkeypatch):
    """Compressed PDFs that pypdf cannot decompress should still use PyMuPDF text."""
    class BrokenPdfReader:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("Limit reached while decompressing.")

    monkeypatch.setattr(file_extract_service, "PdfReader", BrokenPdfReader)
    monkeypatch.setattr(
        file_extract_service,
        "extract_pdf_text_parts_with_pymupdf",
        lambda _file_bytes: ["Chapter 8 Heredity text", "More heredity text"],
    )

    text = extract_text_from_uploaded_file(
        filename="jesc108.pdf",
        file_bytes=b"%PDF compressed",
    )

    assert "Chapter 8 Heredity" in text


def test_pdf_page_extraction_falls_back_to_pymupdf_when_pypdf_fails(monkeypatch):
    """Book-set analysis should not create Unknown Section for pypdf-only failures."""
    class BrokenPdfReader:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("Limit reached while decompressing.")

    monkeypatch.setattr(file_extract_service, "PdfReader", BrokenPdfReader)
    monkeypatch.setattr(
        file_extract_service,
        "extract_pdf_text_parts_with_pymupdf",
        lambda _file_bytes: ["Chapter 8 Heredity text"],
    )

    pages = extract_pages_from_uploaded_file(
        filename="jesc108.pdf",
        file_bytes=b"%PDF compressed",
    )

    assert pages[0]["extraction_method"] == "pdf_text_pymupdf"
    assert "Heredity" in pages[0]["text"]


def test_hindi_pdf_font_encoded_gibberish_is_detected():
    broken_text = (
        "dkO; [kaM ån; fIa/q efr lhi lekkuA Lokfr lkjhk dgfga "
        "lqtkuA tks cj''kb cj ckfj fopk:A gksafg dfor eqDrkefu pk:AA "
        "& rqylhnkl Reprint 2026-27 lu~ 1857 osQ ckxh"
    )

    assert looks_like_broken_hindi_pdf_text(broken_text, "jhks101.pdf")


def test_readable_hindi_pdf_text_is_not_marked_as_broken():
    hindi_text = "अध्याय 2: तुलसीदास भक्तिकाल के महान कवि थे। यह पाठ हिंदी साहित्य से जुड़ा है।"

    assert count_devanagari_chars(hindi_text) > 20
    assert not looks_like_broken_hindi_pdf_text(hindi_text, "jhks102.pdf")


def test_english_pdf_text_is_not_marked_as_broken_even_with_short_filename():
    english_text = (
        "Chapter 2: Acids, Bases and Salts. Students learn about indicators, "
        "neutralisation, and common examples from daily life."
    )

    assert not looks_like_broken_hindi_pdf_text(english_text, "jesc102.pdf")
