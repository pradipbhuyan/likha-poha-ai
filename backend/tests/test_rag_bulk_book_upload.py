import json

from fastapi.testclient import TestClient

from app.main import app
from app.routes import rag


client = TestClient(app)


def test_parse_bulk_book_metadata_requires_one_record_per_file():
    """
    Bulk book uploads should fail early if metadata and files do not line up.

    This protects the RAG database from books being indexed under the wrong
    class or subject when admins upload many Class 1-10 books together.
    """
    metadata_json = json.dumps([
        {
            "grade": "Grade 1",
            "subject": "EVS",
            "title": "Grade 1 EVS Book",
        }
    ])

    try:
        rag.parse_bulk_book_metadata(metadata_json, file_count=2)
    except ValueError as exc:
        assert "count must match" in str(exc)
    else:
        raise AssertionError("Expected mismatched metadata count to fail.")


def test_bulk_book_upload_preserves_per_file_metadata(monkeypatch):
    """
    Uploading multiple books should pass each file's own grade and subject to
    RAG storage.
    """
    captured_uploads = []

    def fake_extract_text_from_uploaded_file(filename, file_bytes):
        return f"Extracted text from {filename}: {file_bytes.decode()}"

    def fake_upload_textbook_text(**kwargs):
        captured_uploads.append(kwargs)
        return {
            "success": True,
            "message": "Uploaded",
            "document_id": f"doc-{len(captured_uploads)}",
            "chunks_created": 1,
        }

    monkeypatch.setattr(
        rag,
        "extract_text_from_uploaded_file",
        fake_extract_text_from_uploaded_file,
    )
    monkeypatch.setattr(rag, "upload_textbook_text", fake_upload_textbook_text)

    metadata = [
        {
            "grade": "Grade 1",
            "subject": "EVS",
            "chapter": "Uploaded Book Content",
            "title": "Grade 1 EVS Full Book",
        },
        {
            "grade": "Grade 5",
            "subject": "Maths",
            "chapter": "Uploaded Book Content",
            "title": "Grade 5 Maths Full Book",
        },
    ]

    response = client.post(
        "/api/rag/bulk-book-upload",
        data={
            "username": "admin",
            "metadata_json": json.dumps(metadata),
        },
        files=[
            ("files", ("grade-1-evs.txt", b"plants and animals", "text/plain")),
            ("files", ("grade-5-maths.txt", b"fractions", "text/plain")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured_uploads[0]["grade"] == "Grade 1"
    assert captured_uploads[0]["subject"] == "EVS"
    assert captured_uploads[0]["title"] == "Grade 1 EVS Full Book"
    assert captured_uploads[1]["grade"] == "Grade 5"
    assert captured_uploads[1]["subject"] == "Maths"
    assert captured_uploads[1]["chapter"] == "Uploaded Book Content"


def test_book_set_upload_indexes_each_file_as_one_book_section(monkeypatch):
    """
    A book split into TOC/chapter PDFs should become multiple chapter-aware RAG
    documents under the same book title prefix.
    """
    captured_uploads = []

    def fake_extract_text_from_uploaded_file(filename, file_bytes):
        return f"Extracted {filename}: {file_bytes.decode()}"

    def fake_upload_textbook_text(**kwargs):
        captured_uploads.append(kwargs)
        return {
            "success": True,
            "message": "Uploaded",
            "document_id": f"doc-{len(captured_uploads)}",
            "chunks_created": 1,
        }

    monkeypatch.setattr(
        rag,
        "extract_text_from_uploaded_file",
        fake_extract_text_from_uploaded_file,
    )
    monkeypatch.setattr(rag, "upload_textbook_text", fake_upload_textbook_text)

    response = client.post(
        "/api/rag/book-set-upload",
        data={
            "username": "admin",
            "grade": "Grade 5",
            "subject": "Science",
            "book_title": "Grade 5 Science Textbook",
            "section_titles": "Table of Contents\nChapter 1: Plants",
        },
        files=[
            ("files", ("toc.pdf", b"contents", "application/pdf")),
            ("files", ("chapter-1.pdf", b"plants", "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured_uploads[0]["title"] == (
        "Grade 5 Science Textbook - Table of Contents"
    )
    assert captured_uploads[0]["chapter"] == "Table of Contents"
    assert captured_uploads[1]["title"] == (
        "Grade 5 Science Textbook - Chapter 1: Plants"
    )
    assert captured_uploads[1]["grade"] == "Grade 5"
    assert captured_uploads[1]["subject"] == "Science"


def test_analyze_book_set_suggests_titles_before_upload(monkeypatch):
    """
    Book-set analysis should suggest editable labels without creating RAG rows.
    """

    def fake_extract_text_from_uploaded_file(filename, file_bytes):
        if filename == "toc.pdf":
            return "Contents\nChapter 1 Plants\nChapter 2 Animals"
        return "Chapter 1: Plants\nRoots, stems, leaves and flowers"

    monkeypatch.setattr(
        rag,
        "extract_text_from_uploaded_file",
        fake_extract_text_from_uploaded_file,
    )

    response = client.post(
        "/api/rag/analyze-book-set",
        files=[
            ("files", ("toc.pdf", b"contents", "application/pdf")),
            ("files", ("chapter-1.pdf", b"plants", "application/pdf")),
        ],
    )

    data = response.json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["sections"][0]["suggested_title"] == "Table of Contents"
    assert data["sections"][1]["suggested_title"] == "Chapter 1: Plants"
    assert data["sections"][1]["word_count"] > 0


def test_infer_book_section_title_handles_title_before_chapter_number():
    """
    Many PDFs start with "Title Chapter N ..." instead of "Chapter N: Title".
    """
    title = rag.infer_book_section_title(
        "iesc104.pdf",
        "Describing Motion Around Us Chapter 4 Everything in nature is in motion.",
        1,
    )

    assert title == "Chapter 4: Describing Motion Around Us"


def test_analyze_book_set_uses_ai_for_filename_like_labels(monkeypatch):
    """
    If local heuristics only produce labels like iesc101, the analyzer should
    ask the LLM for cleaner admin-confirmable labels.
    """

    def fake_extract_text_from_uploaded_file(filename, file_bytes):
        return (
            "Exploration: Entering the World of Secondary Science 1 "
            "In the middle stage, science invited you to be curious."
        )

    captured_model = {}

    def fake_ask_llm(*args, **kwargs):
        captured_model["model"] = kwargs.get("model")
        return json.dumps({
            "sections": [
                {
                    "filename": "iesc101.pdf",
                    "suggested_title": "Chapter 1: Exploration - Entering the World of Secondary Science",
                }
            ]
        })

    monkeypatch.setattr(
        rag,
        "extract_text_from_uploaded_file",
        fake_extract_text_from_uploaded_file,
    )
    monkeypatch.setattr(rag, "ask_llm", fake_ask_llm)

    response = client.post(
        "/api/rag/analyze-book-set",
        files=[
            ("files", ("iesc101.pdf", b"chapter", "application/pdf")),
        ],
    )

    data = response.json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["sections"][0]["suggested_title"] == (
        "Chapter 1: Exploration - Entering the World of Secondary Science"
    )
    assert captured_model["model"] == rag.GPT5_TEXT_MODEL
