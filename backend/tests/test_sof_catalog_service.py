from app.services.sof_catalog_service import (
    build_sof_document_title,
    canonical_sof_chapter,
    canonical_sof_subject,
    get_sof_exam_paper_chapters,
    get_sof_support_chapters,
    normalize_sof_group,
)
from app.routes import rag


def test_canonical_sof_subject_maps_codes_to_subjects():
    assert canonical_sof_subject("SOF ISO") == "Science Olympiad"
    assert canonical_sof_subject("IMO model paper") == "Maths Olympiad"
    assert canonical_sof_subject("IEO prep book") == "English Olympiad"


def test_canonical_sof_chapter_handles_dash_and_apostrophe_variants():
    assert (
        canonical_sof_chapter(
            "Science Olympiad",
            "Cell - The Fundamental Unit of Life",
        )
        == "Cell – The Fundamental Unit of Life"
    )
    assert (
        canonical_sof_chapter(
            "Maths Olympiad",
            "Introduction to Euclid’s Geometry",
        )
        == "Introduction to Euclid's Geometry"
    )
    assert (
        canonical_sof_chapter(
            "English Olympiad",
            "Subject Verb Agreement",
        )
        == "Subject-Verb Agreement"
    )


def test_normalize_sof_group_uses_canonical_subject_chapter_and_title():
    group = normalize_sof_group(
        {
            "grade": "Grade 9",
            "subject": "science",
            "chapter": "Force & Laws of Motion",
            "title": "Force chapter",
            "combined_text": "Force and Laws of Motion chapter notes. Exercise questions follow.",
        }
    )

    assert group["subject"] == "Science Olympiad"
    assert group["chapter"] == "Force and Laws of Motion"
    assert group["content_type"] == "Exercise"
    assert group["title"] == "SOF-ISO Grade 9 - Force and Laws of Motion - Exercise"


def test_normalize_sof_group_preserves_model_paper_chapter_as_title():
    group = normalize_sof_group(
        {
            "grade": "Grade 9",
            "subject": "Maths",
            "chapter": "SOF IMO Model Test Paper 1",
            "title": "Maths paper",
            "combined_text": "SOF-IMO Model Test Paper-1 questions.",
        }
    )

    assert group["subject"] == "Maths Olympiad"
    assert group["chapter"] == "SOF-IMO Model Test Paper-1"
    assert group["content_type"] == "Mock Test Paper"
    assert group["title"] == "SOF-IMO Model Test Paper-1"


def test_workbook_toc_sections_are_canonical_upload_targets():
    assert (
        canonical_sof_chapter("Maths Olympiad", "Logical Reasoning")
        == "Logical Reasoning"
    )
    assert (
        canonical_sof_chapter("Science Olympiad", "SOF National Science Olympiad 2025")
        == "SOF National Science Olympiad - 2025"
    )
    assert (
        canonical_sof_chapter("English Olympiad", "Question Tags & Conditionals")
        == "Question Tags and Conditionals"
    )
    assert (
        canonical_sof_chapter("English Olympiad", "Collocations Homophones Homonyms")
        == "Collocations, Homophones/Homonyms"
    )


def test_workbook_exam_and_support_sections_are_available_for_mock_tests():
    assert "SOF International Mathematics Olympiad - 2025" in get_sof_exam_paper_chapters(
        "Maths Olympiad"
    )
    assert "SOF National Science Olympiad - 2025" in get_sof_exam_paper_chapters(
        "Science Olympiad"
    )
    assert "SOF International English Olympiad - 2025" in get_sof_exam_paper_chapters(
        "English Olympiad"
    )
    assert "Hints & Explanations" in get_sof_support_chapters("Science Olympiad")
    assert "Answer Keys" in get_sof_support_chapters("English Olympiad")


def test_build_sof_document_title_keeps_model_papers_exact():
    assert (
        build_sof_document_title(
            "English Olympiad",
            "SOF-IEO Model Test Paper-2",
            "Model Test Paper",
        )
        == "SOF-IEO Model Test Paper-2"
    )


def test_confirm_sof_upload_saves_canonical_metadata(monkeypatch):
    captured_upload = {}

    def fake_upload_textbook_text(**kwargs):
        captured_upload.update(kwargs)
        return {
            "success": True,
            "message": "Uploaded",
            "document_id": "doc-1",
            "chunks_created": 2,
        }

    monkeypatch.setattr(rag, "upload_textbook_text", fake_upload_textbook_text)

    result = rag.confirm_sof_upload(
        rag.ConfirmSofUploadRequest(
            username="admin",
            groups=[
                rag.SofRagGroup(
                    grade="Grade 9",
                    subject="SOF ISO",
                    chapter="Cell - The Fundamental Unit of Life",
                    title="Cell notes",
                    combined_text="Cell - The Fundamental Unit of Life chapter content.",
                )
            ],
        )
    )

    assert result["success"] is True
    assert captured_upload["subject"] == "Science Olympiad"
    assert captured_upload["chapter"] == "Cell – The Fundamental Unit of Life"
    assert captured_upload["title"] == (
        "SOF-ISO Grade 9 - Cell – The Fundamental Unit of Life - Chapter Content"
    )


def test_analyze_sof_images_keeps_good_files_when_one_file_fails(monkeypatch):
    """
    A bad SOF scan/PDF should not prevent other selected files from being
    analyzed and grouped.
    """

    def fake_extract_pages_from_uploaded_file(filename, file_bytes):
        if filename == "bad.pdf":
            raise ValueError("Unreadable PDF")
        return [
            {
                "page_number": 1,
                "filename": filename,
                "text": "Force and Laws of Motion chapter content with exercise questions.",
                "word_count": 9,
                "extraction_method": "pdf_text",
                "warnings": [],
            }
        ]

    captured_model = {}

    def fake_ask_llm(*args, **kwargs):
        captured_model["model"] = kwargs.get("model")
        return """
        {
          "groups": [
            {
              "grade": "Grade 9",
              "subject": "Science Olympiad",
              "chapter": "Force and Laws of Motion",
              "title": "Force exercise",
              "page_numbers": [1],
              "confidence": "High",
              "combined_text": "Force and Laws of Motion chapter content with exercise questions."
            }
          ]
        }
        """

    monkeypatch.setattr(
        rag,
        "extract_pages_from_uploaded_file",
        fake_extract_pages_from_uploaded_file,
    )
    monkeypatch.setattr(rag, "ask_llm", fake_ask_llm)

    import asyncio

    async def run_request():
        from fastapi import UploadFile
        from io import BytesIO

        return await rag.analyze_sof_images(
            grade="Grade 9",
            files=[
                UploadFile(filename="bad.pdf", file=BytesIO(b"bad")),
                UploadFile(filename="good.pdf", file=BytesIO(b"good")),
            ],
        )

    result = asyncio.run(run_request())

    assert result["success"] is True
    assert len(result["groups"]) == 1
    assert result["file_warnings"][0]["filename"] == "bad.pdf"
    assert captured_model["model"] == rag.GPT5_TEXT_MODEL


def test_analyze_sof_images_returns_raw_response_for_invalid_json(monkeypatch):
    """
    Invalid AI JSON should return the raw response so the admin can see what
    failed instead of only seeing a generic frontend error.
    """

    def fake_extract_pages_from_uploaded_file(filename, file_bytes):
        return [
            {
                "page_number": 1,
                "filename": filename,
                "text": "SOF ISO Cell chapter content.",
                "word_count": 5,
                "extraction_method": "image_ocr",
                "warnings": [],
            }
        ]

    monkeypatch.setattr(
        rag,
        "extract_pages_from_uploaded_file",
        fake_extract_pages_from_uploaded_file,
    )
    monkeypatch.setattr(rag, "ask_llm", lambda *args, **kwargs: "not-json")

    import asyncio

    async def run_request():
        from fastapi import UploadFile
        from io import BytesIO

        return await rag.analyze_sof_images(
            grade="Grade 9",
            files=[UploadFile(filename="sof.jpg", file=BytesIO(b"image"))],
        )

    result = asyncio.run(run_request())

    assert result["success"] is False
    assert "invalid JSON" in result["message"]
    assert result["raw_ai_response"] == "not-json"
