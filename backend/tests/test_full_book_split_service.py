from app.services import full_book_split_service
from app.services.full_book_split_service import (
    FullBookPage,
    combine_pages_for_range,
    detect_full_book_chapters,
    extract_full_book_pages,
)


def test_detect_full_book_chapters_builds_page_ranges():
    """Chapter headings in one full PDF should become editable page ranges."""
    pages = [
        FullBookPage(1, "Contents\nChapter 1: Nouns", 4, "pdf_text"),
        FullBookPage(2, "Chapter 1: Nouns\nNaming words", 5, "pdf_text"),
        FullBookPage(3, "More noun examples", 3, "pdf_text"),
        FullBookPage(4, "Chapter 2: Pronouns\nHe she it", 5, "pdf_text"),
        FullBookPage(5, "Practice questions", 2, "pdf_text"),
    ]

    chapters = detect_full_book_chapters(pages)

    assert chapters[0]["title"] == "Chapter 1: Nouns"
    assert chapters[0]["start_page"] == 1
    assert chapters[0]["end_page"] == 3
    assert chapters[1]["title"] == "Chapter 2: Pronouns"
    assert chapters[1]["start_page"] == 4
    assert chapters[1]["end_page"] == 5


def test_detect_full_book_chapters_uses_numbered_contents_for_reader_books():
    """Reader books with story titles in Contents should split into lessons."""
    pages = [
        FullBookPage(1, "", 0, "pdf_text"),
        FullBookPage(
            2,
            "\n".join([
                "Contents",
                "1. The Lost Child  ..... 1",
                "2. The Adventures of Toto  ..... 7",
                "3. Iswaran the Storyteller  ..... 12",
            ]),
            18,
            "pdf_text",
        ),
        FullBookPage(3, "IT was the festival of spring.\n1. The Lost Child", 9, "pdf_text"),
        FullBookPage(4, "The Lost Child / 2\nMore story text", 7, "pdf_text"),
        FullBookPage(
            5,
            "GRANDFATHER bought Toto from a tonga-driver.\n2. The Adventures of Toto",
            10,
            "pdf_text",
        ),
        FullBookPage(6, "The Adventures of Toto / 8\nMore story text", 8, "pdf_text"),
        FullBookPage(7, "THE story was narrated to Ganesh.\n3. Iswaran the Storyteller", 10, "pdf_text"),
    ]

    chapters = detect_full_book_chapters(pages)

    assert [chapter["title"] for chapter in chapters] == [
        "Chapter 1: The Lost Child",
        "Chapter 2: The Adventures of Toto",
        "Chapter 3: Iswaran the Storyteller",
    ]
    assert chapters[0]["start_page"] == 3
    assert chapters[0]["end_page"] == 4
    assert chapters[1]["start_page"] == 5
    assert chapters[1]["end_page"] == 6
    assert chapters[2]["start_page"] == 7


def test_detect_full_book_chapters_uses_contents_page_numbers_for_short_titles():
    """Short titles should not match incidental words before their real start."""
    pages = [
        FullBookPage(1, "Contents\n1. The Happy Prince ..... 28\n2. The Beggar ..... 62", 10, "pdf_text"),
        FullBookPage(29, "5. The Happy Prince\nThe beggars sat near the gates.", 9, "pdf_text"),
        FullBookPage(63, "KIND sir, have pity on a poor man.\n2. The Beggar", 10, "pdf_text"),
    ]

    chapters = detect_full_book_chapters(pages)

    assert chapters[0]["title"] == "Chapter 1: The Happy Prince"
    assert chapters[0]["start_page"] == 29
    assert chapters[1]["title"] == "Chapter 2: The Beggar"
    assert chapters[1]["start_page"] == 63


def test_combine_pages_for_range_keeps_page_context():
    """Reviewed chapter ranges should combine only matching page text."""
    pages = [
        FullBookPage(1, "Front matter", 2, "pdf_text"),
        FullBookPage(2, "Chapter text", 2, "pdf_text"),
        FullBookPage(3, "Exercise text", 2, "pdf_text"),
    ]

    combined = combine_pages_for_range(pages, 2, 3)

    assert "Page 1" not in combined
    assert "Page 2" in combined
    assert "Chapter text" in combined
    assert "Exercise text" in combined


def test_full_book_extraction_falls_back_to_pymupdf_when_pypdf_fails(monkeypatch):
    """Full-book analysis should retry with PyMuPDF for pypdf decompression limits."""
    class BrokenPdfReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [object()]

    def fallback_extraction(_filename, _file_bytes, _progress_callback=None):
        return [
            FullBookPage(
                page_number=1,
                text="Chapter 8 Heredity and evolution content " * 20,
                word_count=120,
                extraction_method="pdf_text_pymupdf",
            ),
            FullBookPage(
                page_number=2,
                text="Mendel experiments and inherited traits " * 20,
                word_count=100,
                extraction_method="pdf_text_pymupdf",
            ),
        ]

    monkeypatch.setattr(full_book_split_service, "PdfReader", BrokenPdfReader)
    monkeypatch.setattr(
        full_book_split_service,
        "extract_pdf_text_pages_with_pymupdf",
        fallback_extraction,
    )

    pages, warnings = extract_full_book_pages(
        filename="jesc108.pdf",
        file_bytes=b"%PDF compressed",
        ocr_scanned=False,
    )

    assert not warnings
    assert pages[0].extraction_method == "pdf_text_pymupdf"
    assert "Heredity" in pages[0].text
