import json

from fastapi.testclient import TestClient

from app.main import app
from app.routes import rag
from app.services.auth_service import require_admin


client = TestClient(app)


class FakeUpdateQuery:
    """Minimal Supabase update query stub for RAG metadata tests."""

    def __init__(self):
        self.updated_payload = None
        self.filters = []

    def update(self, payload):
        self.updated_payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        return type("Response", (), {"data": [{"id": "doc-1", **self.updated_payload}]})()


class FakeAdminClient:
    """Fake admin client that records table update calls."""

    def __init__(self):
        self.query = FakeUpdateQuery()

    def table(self, table_name):
        assert table_name == "rag_documents"
        return self.query


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


def test_book_set_upload_fills_missing_section_titles_from_filenames(monkeypatch):
    """
    Book-set upload should not fail if admins provide fewer labels than files.

    This commonly happens on mobile when one analyzed title is blank or hard to
    edit. Missing labels should fall back to readable file names.
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
            "section_titles": "Table of Contents",
        },
        files=[
            ("files", ("toc.pdf", b"contents", "application/pdf")),
            ("files", ("chapter-1.pdf", b"plants", "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured_uploads[0]["chapter"] == "Table of Contents"
    assert captured_uploads[1]["chapter"] == "chapter 1"
    assert captured_uploads[1]["title"] == "Grade 5 Science Textbook - chapter 1"


def test_book_set_upload_preserves_commas_inside_chapter_titles(monkeypatch):
    """
    Chapter titles with commas must remain one label during RAG upload.

    This protects labels such as "Pressure, Winds, Storms, and Cyclones" from
    being split into separate RAG documents/chapter links.
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
            "grade": "Grade 8",
            "subject": "Science",
            "book_title": "Science Text Book",
            "section_titles": (
                "Chapter 6: Pressure, Winds, Storms, and Cyclones\n"
                "Chapter 7: Particulate Nature of Matter"
            ),
        },
        files=[
            ("files", ("hecu106.pdf", b"pressure", "application/pdf")),
            ("files", ("hecu107.pdf", b"matter", "application/pdf")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured_uploads[0]["chapter"] == (
        "Chapter 6: Pressure, Winds, Storms, and Cyclones"
    )
    assert captured_uploads[0]["title"] == (
        "Science Text Book - Chapter 6: Pressure, Winds, Storms, and Cyclones"
    )
    assert captured_uploads[1]["chapter"] == "Chapter 7: Particulate Nature of Matter"


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


def test_infer_book_section_title_handles_ncert_flattened_grade_heading():
    """
    NCERT PDFs can flatten the heading into one line with page numbers.
    """
    title = rag.infer_book_section_title(
        "hecu106.pdf",
        (
            "80 Curiosity — Textbook of Science for Grade 8 Pressure, Winds, "
            "Storms, and Cyclones 6 z Why are winds stronger on some days "
            "than on others?"
        ),
        1,
    )

    assert title == "Chapter 6: Pressure, Winds, Storms, and Cyclones"


def test_infer_book_section_title_ignores_ncert_indesign_footer():
    """
    NCERT chapter PDFs include .indd footer metadata that must not become labels.
    """
    title = rag.infer_book_section_title(
        "hecu106.pdf",
        """
80
Curiosity — Textbook of Science for Grade 8
Pressure, Winds,
Storms, and Cyclones
6

 z Why are winds stronger on some days than on others?
Probe and ponder
Chapter 6.indd   80Chapter 6.indd   80 6/28/2025   3:59:54 PM
Reprint 2026-27
""",
        1,
    )

    assert title == "Chapter 6: Pressure, Winds, Storms, and Cyclones"


def test_normalize_suggested_section_title_removes_pdf_export_artifacts():
    """
    AI cleanup should remove .indd timestamps and recover the clean preview title.
    """
    title = rag.normalize_suggested_section_title(
        "Chapter 6.indd 80Chapter 6.indd 80 6/28/2025 3:59:54 PM",
        "hecu106.pdf",
        (
            "80 Curiosity — Textbook of Science for Grade 8 Pressure, Winds, "
            "Storms, and Cyclones 6 z Why are winds stronger on some days?"
        ),
    )

    assert title == "Chapter 6: Pressure, Winds, Storms, and Cyclones"


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


def test_rag_document_preview_returns_stored_chunks(monkeypatch):
    """
    Admin preview should show the actual stored chunks behind a document label.

    This lets admins catch cases where a corrected chapter title points to the
    wrong uploaded content before students use that dropdown entry.
    """
    app.dependency_overrides[require_admin] = lambda: {
        "profile": {
            "id": "admin-id",
            "role": "admin",
        }
    }

    monkeypatch.setattr(
        rag,
        "get_rag_document_preview",
        lambda document_id: [
            {
                "chunk_index": 0,
                "chunk_text": "Pressure, winds, storms, and cyclones content.",
            },
            {
                "chunk_index": 1,
                "chunk_text": "Air pressure changes create winds.",
            },
        ],
    )

    response = client.get("/api/rag/documents/doc-1/preview")
    data = response.json()

    assert response.status_code == 200
    assert data["success"] is True
    assert "Pressure, winds, storms" in data["preview"]
    assert "Air pressure changes" in data["preview"]


def test_update_rag_document_metadata_updates_title_and_chapter(monkeypatch):
    """
    Metadata repair should update both the visible title and retrieval chapter.
    """
    app.dependency_overrides[require_admin] = lambda: {
        "profile": {
            "id": "admin-id",
            "role": "admin",
        }
    }
    fake_admin = FakeAdminClient()

    monkeypatch.setattr(rag, "admin_client", fake_admin)

    response = client.patch(
        "/api/rag/documents/doc-1/metadata",
        json={
            "title": "Science Text Book - Chapter 6: Pressure, Winds, Storms, and Cyclones",
            "chapter": "Chapter 6: Pressure, Winds, Storms, and Cyclones",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["success"] is True
    assert fake_admin.query.updated_payload == {
        "title": "Science Text Book - Chapter 6: Pressure, Winds, Storms, and Cyclones",
        "chapter": "Chapter 6: Pressure, Winds, Storms, and Cyclones",
    }
    assert ("id", "doc-1") in fake_admin.query.filters
