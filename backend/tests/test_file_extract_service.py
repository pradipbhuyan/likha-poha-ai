from io import BytesIO

from pypdf import PdfWriter

from app.services.file_extract_service import extract_pages_from_uploaded_file


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
