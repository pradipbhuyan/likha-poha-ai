from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from app.services.file_extract_service import (
    extract_pages_from_uploaded_file,
    extract_text_from_uploaded_file,
)
from app.services.full_book_split_service import (
    combine_pages_for_range,
    detect_full_book_chapters,
    extract_full_book_pages,
)
from app.services.openai_service import GPT5_TEXT_MODEL, ask_llm
import json
import re
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


from app.models.schemas import (
    RagTextUploadRequest,
    RagUploadResponse,
    RagSearchRequest,
    RagSearchResponse,
)

from app.services.rag_service import (
    upload_textbook_text,
    search_textbook_content,
    list_rag_documents,
    get_rag_document_preview,
    delete_rag_document,
)
from app.services.rag_job_service import (
    create_rag_job,
    get_rag_job,
    list_recent_rag_jobs,
    submit_rag_job,
    update_rag_job,
)
from app.services.rag_visual_service import (
    backfill_visual_assets_for_document,
    list_visual_assets_for_document,
    update_visual_asset,
)
from app.services.auth_service import admin_client, require_admin
from app.services.sof_catalog_service import (
    build_sof_catalog_prompt,
    get_sof_subjects,
    normalize_sof_group,
)

from app.services.ocr_service import extract_text_from_image_bytes

router = APIRouter()


class RagDocumentMetadataUpdate(BaseModel):
    """Editable RAG document metadata managed from the admin library."""

    title: str
    chapter: str


class RagVisualAssetUpdate(BaseModel):
    """Editable review metadata for textbook page visuals."""

    caption: Optional[str] = None
    nearby_text: Optional[str] = None
    status: Optional[str] = None


@router.post("/upload-text", response_model=RagUploadResponse)
def upload_text(data: RagTextUploadRequest):
    """Upload raw text as a RAG document and create searchable embeddings."""
    result = upload_textbook_text(
        username=data.username,
        grade=data.grade,
        board=data.board,
        subject=data.subject,
        chapter=data.chapter,
        title=data.title,
        text=data.text,
    )

    return RagUploadResponse(**result)


@router.post("/upload-image", response_model=RagUploadResponse)
async def upload_image(
    username: str = Form(...),
    grade: str = Form(...),
    board: str = Form("CBSE"),
    subject: str = Form(...),
    chapter: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """OCR one uploaded image and save the extracted text into RAG."""
    image_bytes = await file.read()

    extracted_text = extract_text_from_image_bytes(image_bytes)

    result = upload_textbook_text(
        username=username,
        grade=grade,
        board=board,
        subject=subject,
        chapter=chapter,
        title=title,
        text=extracted_text,
    )

    return RagUploadResponse(**result)


@router.post("/upload-file", response_model=RagUploadResponse)
async def upload_file(
    username: str = Form(...),
    grade: str = Form(...),
    board: str = Form("CBSE"),
    subject: str = Form(...),
    chapter: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """Extract text from one supported file type and save it into RAG."""
    try:
        file_bytes = await file.read()

        extracted_text = extract_text_from_uploaded_file(
            filename=file.filename,
            file_bytes=file_bytes,
        )

        result = upload_textbook_text(
            username=username,
            grade=grade,
            board=board,
            subject=subject,
            chapter=chapter,
            title=title,
            text=extracted_text,
        )

        return RagUploadResponse(**result)

    except Exception as e:
        return RagUploadResponse(
            success=False,
            message=f"File upload failed: {str(e)}",
            document_id=None,
            chunks_created=0,
        )


@router.post("/upload-files")
async def upload_files_batch(
    username: str = Form(...),
    grade: str = Form(...),
    board: str = Form("CBSE"),
    subject: str = Form(...),
    chapter: str = Form(...),
    titles: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """
    Upload up to 20 files into RAG as separate documents.

    Titles are supplied as a comma-separated list and must line up one-for-one
    with the uploaded files so each document has useful source attribution.
    """
    try:
        if len(files) > 20:
            return {
                "success": False,
                "message": "You can upload a maximum of 20 documents at once.",
                "results": [],
            }

        title_list = [
            title.strip()
            for title in titles.split(",")
            if title.strip()
        ]

        if len(title_list) != len(files):
            return {
                "success": False,
                "message": "Number of titles must match number of uploaded files.",
                "results": [],
            }

        upload_results = []

        for index, file in enumerate(files):
            try:
                file_bytes = await file.read()

                extracted_text = extract_text_from_uploaded_file(
                    filename=file.filename,
                    file_bytes=file_bytes,
                )

                result = upload_textbook_text(
                    username=username,
                    grade=grade,
                    board=board,
                    subject=subject,
                    chapter=chapter,
                    title=title_list[index],
                    text=extracted_text,
                )

                upload_results.append({
                    "filename": file.filename,
                    "title": title_list[index],
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "document_id": result.get("document_id"),
                    "chunks_created": result.get("chunks_created", 0),
                })

            except Exception as file_error:
                upload_results.append({
                    "filename": file.filename,
                    "title": title_list[index],
                    "success": False,
                    "message": f"Upload failed: {str(file_error)}",
                    "document_id": None,
                    "chunks_created": 0,
                })

        successful = [
            item for item in upload_results
            if item["success"]
        ]

        return {
            "success": len(successful) > 0,
            "message": f"{len(successful)} of {len(files)} documents uploaded successfully.",
            "results": upload_results,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Batch upload failed: {str(e)}",
            "results": [],
        }


@router.get("/documents")
def get_rag_documents():
    """Return uploaded RAG document metadata for the admin upload page."""
    documents = list_rag_documents()

    return {
        "success": True,
        "documents": documents,
    }


@router.get("/documents/{document_id}/preview")
def preview_rag_document(
    document_id: str,
    _admin=Depends(require_admin),
):
    """Return a short chunk preview so admins can verify title/content alignment."""
    chunks = get_rag_document_preview(document_id)

    return {
        "success": True,
        "chunks": chunks,
        "preview": "\n\n".join(chunk.get("chunk_text", "") for chunk in chunks),
    }


@router.get("/documents/{document_id}/visuals")
def get_rag_document_visuals(
    document_id: str,
    _admin=Depends(require_admin),
):
    """Return textbook visual pages linked to one RAG document."""
    return {
        "success": True,
        "visuals": list_visual_assets_for_document(document_id),
    }


@router.post("/documents/{document_id}/visuals/backfill")
async def backfill_rag_document_visuals(
    document_id: str,
    file: UploadFile = File(...),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
    admin=Depends(require_admin),
):
    """Render uploaded source PDF pages and link them to an existing RAG document."""
    file_bytes = await file.read()
    profile = admin.get("profile") or {}

    return backfill_visual_assets_for_document(
        document_id=document_id,
        file_bytes=file_bytes,
        filename=file.filename or "source.pdf",
        uploaded_by=profile.get("id"),
        start_page=start_page,
        end_page=end_page,
    )


@router.patch("/visuals/{visual_id}")
def patch_rag_visual_asset(
    visual_id: str,
    data: RagVisualAssetUpdate,
    _admin=Depends(require_admin),
):
    """Update review status/caption for one textbook visual asset."""
    payload = (
        data.model_dump(exclude_unset=True)
        if hasattr(data, "model_dump")
        else data.dict(exclude_unset=True)
    )

    return {
        "success": True,
        "visual": update_visual_asset(visual_id, payload),
        "message": "Textbook visual updated.",
    }


@router.patch("/documents/{document_id}/metadata")
def update_rag_document_metadata(
    document_id: str,
    data: RagDocumentMetadataUpdate,
    _admin=Depends(require_admin),
):
    """Update one RAG document's display title and retrieval chapter label."""
    title = data.title.strip()
    chapter = data.chapter.strip()

    if not title or not chapter:
        raise HTTPException(
            status_code=400,
            detail="Title and chapter are required.",
        )

    response = (
        admin_client
        .table("rag_documents")
        .update({
            "title": title,
            "chapter": chapter,
        })
        .eq("id", document_id)
        .execute()
    )

    return {
        "success": True,
        "document": response.data[0] if response.data else None,
        "message": "RAG document metadata updated.",
    }


@router.delete("/documents/{document_id}")
def remove_rag_document(document_id: str):
    """Delete a RAG document and all associated chunks by document id."""
    try:
        delete_rag_document(document_id)

        return {
            "success": True,
            "message": "Document deleted successfully.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to delete document: {str(e)}",
        )

@router.post("/analyze-image")
async def analyze_rag_image(
    file: UploadFile = File(...),
):
    """
    OCR and classify one textbook page image before upload.

    The endpoint suggests grade/subject/chapter metadata but does not persist
    anything; admins review the result before uploading.
    """
    try:
        image_bytes = await file.read()

        extracted_text = extract_text_from_image_bytes(image_bytes)

        prompt = f"""
You are analyzing a textbook page.

Determine whether the page is:

- Chapter page
- Table of Contents
- Worksheet
- Question Paper
- Notes

If the page contains a list of chapters,
return all chapters in the chapters array.

If the page is a chapter title page,
return only the current chapter.

Detect whether this belongs to:
- Mathematics
- Science
- English

Return ONLY valid JSON.

Format:

{{
  "page_type": "",
  "subject": "",
  "grade": "",
  "title": "",
  "chapter": "",
  "chapters": [],
  "confidence": ""
}}

OCR TEXT:

{extracted_text}
"""

        system_prompt = """
You are an educational OCR metadata extraction assistant.

Your job is to analyze textbook pages and identify:

- page type
- title
- chapter
- subject
- grade
- list of chapters if this is a contents page

Always return valid JSON.

Never return markdown.
Never return explanations.
Never return code fences.
"""

        ai_response = ask_llm(
            system_prompt=system_prompt,
            user_prompt=prompt,
            username="admin",
            feature="rag_analysis",
        )

        return {
            "success": True,
            "extracted_text": extracted_text,
            "suggestion": ai_response,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Image analysis failed: {str(e)}",
            "extracted_text": "",
            "suggestion": None,
        }


class SofRagGroup(BaseModel):
    grade: str
    subject: str
    chapter: str
    title: str
    combined_text: str


class ConfirmSofUploadRequest(BaseModel):
    username: str
    groups: List[SofRagGroup]


class BulkBookMetadata(BaseModel):
    board: str = "CBSE"
    grade: str
    subject: str
    title: str
    chapter: str = "Uploaded Book Content"


class FullBookChapterSelection(BaseModel):
    title: str
    start_page: int
    end_page: int
    include: bool = True


def build_full_book_analysis_payload(pages, warnings, chapters):
    """Shape full-book analysis output for sync and background endpoints."""
    return {
        "success": True,
        "message": "Full book analyzed. Review chapter ranges before upload.",
        "page_count": len(pages),
        "word_count": sum(page.word_count for page in pages),
        "extraction_methods": sorted(
            {page.extraction_method for page in pages}
        ),
        "warnings": warnings,
        "chapters": chapters,
    }


def calculate_page_progress(processed_pages: int, page_count: int, start: int, span: int) -> int:
    """Convert page extraction progress into one slice of a job progress bar."""
    if page_count <= 0:
        return start

    return start + int((processed_pages / page_count) * span)


def run_full_book_analysis_job(
    *,
    job_id: str,
    filename: str,
    file_bytes: bytes,
    ocr_scanned: bool,
):
    """Analyze one full-book PDF in the background and persist progress."""
    try:
        update_rag_job(
            job_id,
            status="running",
            phase="extracting_pages",
            percent=2,
            message="Starting full-book analysis.",
        )

        def progress_callback(**progress):
            update_rag_job(
                job_id,
                phase=progress.get("phase", "extracting_pages"),
                page_count=progress.get("page_count", 0),
                processed_pages=progress.get("processed_pages", 0),
                percent=calculate_page_progress(
                    progress.get("processed_pages", 0),
                    progress.get("page_count", 0),
                    5,
                    70,
                ),
                message=progress.get("message", "Extracting book pages."),
            )

        pages, warnings = extract_full_book_pages(
            filename=filename,
            file_bytes=file_bytes,
            ocr_scanned=ocr_scanned,
            progress_callback=progress_callback,
        )
        update_rag_job(
            job_id,
            phase="detecting_chapters",
            page_count=len(pages),
            processed_pages=len(pages),
            percent=82,
            message="Detecting chapter boundaries.",
        )
        chapters = detect_full_book_chapters(pages)
        payload = build_full_book_analysis_payload(pages, warnings, chapters)

        update_rag_job(
            job_id,
            status="completed",
            phase="ready_for_review",
            page_count=payload["page_count"],
            processed_pages=payload["page_count"],
            total_chapters=len(chapters),
            processed_chapters=len(chapters),
            percent=100,
            message=payload["message"],
            warnings=warnings,
            result=payload,
        )
    except Exception as exc:
        update_rag_job(
            job_id,
            status="failed",
            phase="failed",
            percent=100,
            error_message=str(exc),
            message=f"Full book analysis failed: {str(exc)}",
            result={
                "success": False,
                "message": f"Full book analysis failed: {str(exc)}",
                "page_count": 0,
                "word_count": 0,
                "extraction_methods": [],
                "warnings": [],
                "chapters": [],
            },
        )


def run_full_book_upload_job(
    *,
    job_id: str,
    username: str,
    grade: str,
    board: str,
    subject: str,
    book_title: str,
    chapters: list[FullBookChapterSelection],
    filename: str,
    file_bytes: bytes,
    ocr_scanned: bool,
):
    """Create reviewed full-book chapter RAG documents in the background."""
    try:
        included_chapters = [
            chapter for chapter in chapters
            if chapter.include and chapter.title.strip()
        ]

        if not included_chapters:
            raise ValueError("Select at least one chapter to upload.")

        update_rag_job(
            job_id,
            status="running",
            phase="extracting_pages",
            total_chapters=len(included_chapters),
            percent=2,
            message="Extracting pages before RAG upload.",
        )

        def page_progress_callback(**progress):
            update_rag_job(
                job_id,
                phase=progress.get("phase", "extracting_pages"),
                page_count=progress.get("page_count", 0),
                processed_pages=progress.get("processed_pages", 0),
                percent=calculate_page_progress(
                    progress.get("processed_pages", 0),
                    progress.get("page_count", 0),
                    5,
                    30,
                ),
                message=progress.get("message", "Extracting book pages."),
            )

        pages, extraction_warnings = extract_full_book_pages(
            filename=filename,
            file_bytes=file_bytes,
            ocr_scanned=ocr_scanned,
            progress_callback=page_progress_callback,
        )
        page_count = len(pages)
        upload_results = []
        cumulative_chunks = 0
        known_total_chunks = 0

        for chapter_index, chapter in enumerate(included_chapters):
            update_rag_job(
                job_id,
                phase="embedding_chunks",
                page_count=page_count,
                processed_pages=page_count,
                total_chapters=len(included_chapters),
                processed_chapters=chapter_index,
                percent=35 + int((chapter_index / len(included_chapters)) * 60),
                message=f"Preparing {chapter.title.strip()} for RAG.",
            )

            if chapter.start_page < 1 or chapter.end_page < chapter.start_page:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": "Invalid chapter page range.",
                    "chunks_created": 0,
                })
                continue

            if chapter.end_page > page_count:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": f"End page exceeds PDF page count ({page_count}).",
                    "chunks_created": 0,
                })
                continue

            chapter_text = combine_pages_for_range(
                pages,
                chapter.start_page,
                chapter.end_page,
            )

            if len(chapter_text.split()) < 30:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": "Too little readable text in this page range.",
                    "chunks_created": 0,
                })
                continue

            def chunk_progress_callback(**progress):
                nonlocal known_total_chunks
                total_chunks = int(progress.get("total_chunks", 0) or 0)
                processed_chunks = int(progress.get("processed_chunks", 0) or 0)

                if total_chunks and processed_chunks == 0:
                    known_total_chunks += total_chunks

                chapter_fraction = (
                    processed_chunks / total_chunks
                    if total_chunks
                    else 0
                )
                percent = 35 + int(
                    ((chapter_index + chapter_fraction) / len(included_chapters)) * 60
                )
                update_rag_job(
                    job_id,
                    phase="embedding_chunks",
                    processed_chapters=chapter_index,
                    total_chapters=len(included_chapters),
                    processed_chunks=cumulative_chunks + processed_chunks,
                    total_chunks=max(
                        known_total_chunks,
                        cumulative_chunks + total_chunks,
                    ),
                    percent=percent,
                    message=progress.get("message", "Embedding RAG chunks."),
                )

            document_title = f"{book_title.strip()} - {chapter.title.strip()}"
            result = upload_textbook_text(
                username=username,
                board=board,
                grade=grade.strip(),
                subject=subject.strip(),
                chapter=chapter.title.strip(),
                title=document_title,
                text=chapter_text,
                progress_callback=chunk_progress_callback,
            )

            created_chunks = result.get("chunks_created", 0)
            cumulative_chunks += created_chunks
            upload_results.append({
                "title": document_title,
                "chapter": chapter.title.strip(),
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "document_id": result.get("document_id"),
                "chunks_created": created_chunks,
            })
            update_rag_job(
                job_id,
                processed_chapters=chapter_index + 1,
                processed_chunks=cumulative_chunks,
                total_chunks=max(known_total_chunks, cumulative_chunks),
                percent=35 + int(((chapter_index + 1) / len(included_chapters)) * 60),
                message=f"Uploaded {chapter.title.strip()} to RAG.",
            )

        successful = [
            item for item in upload_results
            if item.get("success")
        ]
        payload = {
            "success": len(successful) > 0,
            "message": f"{len(successful)} of {len(included_chapters)} chapters uploaded.",
            "warnings": extraction_warnings,
            "results": upload_results,
        }

        update_rag_job(
            job_id,
            status="completed",
            phase="completed",
            processed_chapters=len(included_chapters),
            processed_chunks=cumulative_chunks,
            total_chunks=max(known_total_chunks, cumulative_chunks),
            percent=100,
            message=payload["message"],
            warnings=extraction_warnings,
            result=payload,
        )
    except Exception as exc:
        update_rag_job(
            job_id,
            status="failed",
            phase="failed",
            percent=100,
            error_message=str(exc),
            message=f"Full book chapter upload failed: {str(exc)}",
            result={
                "success": False,
                "message": f"Full book chapter upload failed: {str(exc)}",
                "results": [],
            },
        )


def parse_bulk_book_metadata(metadata_json: str, file_count: int) -> List[BulkBookMetadata]:
    """
    Validate the per-file book metadata supplied by the admin bulk upload UI.

    Each uploaded book must have an explicit grade, subject, and title so the
    resulting RAG documents can be filtered correctly for Class 1-10 students.
    """
    try:
        raw_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Book metadata must be valid JSON.") from exc

    if not isinstance(raw_metadata, list):
        raise ValueError("Book metadata must be a list.")

    if len(raw_metadata) != file_count:
        raise ValueError("Book metadata count must match uploaded file count.")

    metadata = [BulkBookMetadata(**item) for item in raw_metadata]

    for index, item in enumerate(metadata, start=1):
        if not item.grade.strip():
            raise ValueError(f"Book {index} is missing a grade.")
        if not item.subject.strip():
            raise ValueError(f"Book {index} is missing a subject.")
        if not item.title.strip():
            raise ValueError(f"Book {index} is missing a title.")

    return metadata


def parse_book_section_titles(section_titles: str, files: list[UploadFile]) -> list[str]:
    """
    Resolve one TOC/chapter label per uploaded book-section file.

    Admins can paste one title per line. Commas are preserved because textbook
    chapters often include comma-separated titles such as "Pressure, Winds,
    Storms, and Cyclones". If a label is missing, readable file names are used
    so a multi-file book can still be indexed safely.
    """
    titles = [
        title.strip()
        for title in section_titles.splitlines()
        if title.strip()
    ]

    resolved_titles = []

    for index, file in enumerate(files):
        fallback_title = (
            Path(file.filename or f"Section {index + 1}").stem
            .replace("_", " ")
            .replace("-", " ")
            .strip()
            or f"Section {index + 1}"
        )
        resolved_titles.append(titles[index] if index < len(titles) else fallback_title)

    return resolved_titles


def readable_title_from_filename(filename: str, index: int) -> str:
    """Convert a raw file name into a readable fallback section title."""
    return (
        Path(filename or f"Section {index + 1}").stem
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        or f"Section {index + 1}"
    )


def clean_pdf_label_text(text: str) -> str:
    """Remove PDF/export artifacts before chapter-label extraction."""
    cleaned = re.sub(r"\b[\w-]+\.indd\b", " ", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:AM|PM)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def contains_devanagari(text: str) -> bool:
    """Return true when text includes Hindi/Devanagari characters."""
    return bool(re.search(r"[\u0900-\u097F]", text or ""))


def normalize_hindi_section_title(prefix: str, number: str, title: str) -> str:
    """Format Hindi chapter labels while preserving the original script."""
    clean_title = clean_pdf_label_text(title).strip(" :-–—।")
    clean_title = re.sub(r"\s+", " ", clean_title)

    if clean_title:
        return f"{prefix} {number}: {clean_title}"

    return f"{prefix} {number}"


def infer_chapter_number_from_filename(filename: str) -> str:
    """
    Infer common textbook chapter numbers from filenames like hecu106.pdf.

    NCERT split PDFs often encode chapter 1 as 101, chapter 6 as 106, etc.
    This is only a fallback when OCR text does not expose a clean heading.
    """
    match = re.search(r"(\d{3})(?=\D*$)", Path(filename or "").stem)

    if not match:
        return ""

    number = int(match.group(1))

    if 101 <= number <= 130:
        return str(number - 100)

    return ""


def normalize_suggested_section_title(title: str, filename: str, preview: str = "") -> str:
    """Keep AI/local labels readable and strip publishing metadata artifacts."""
    cleaned = clean_pdf_label_text(title)
    cleaned = re.sub(r"\s*[:.-]?\s*z\s+why\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[:.-]?\s+why\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[:.-]?\s+probe\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-–—")

    chapter_with_bad_tail = re.match(
        r"^chapter\s+(\d{1,2})\b(?:\s+\d+)?(?:\s+chapter\s+\1\b)?\s*(.*)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if chapter_with_bad_tail:
        chapter_number = chapter_with_bad_tail.group(1)
        title_tail = chapter_with_bad_tail.group(2).strip(" :-–—")

        if title_tail and not re.search(r"\d{1,2}/\d{1,2}/\d{4}|\.indd", title_tail, flags=re.IGNORECASE):
            return f"Chapter {chapter_number}: {title_tail}"

        clean_preview_title = infer_title_from_grade_heading(preview)
        if clean_preview_title:
            return clean_preview_title

        return f"Chapter {chapter_number}"

    if ".indd" in (title or "").lower():
        clean_preview_title = infer_title_from_grade_heading(preview)
        if clean_preview_title:
            return clean_preview_title

    return cleaned or readable_title_from_filename(filename, 0)


def infer_hindi_section_title(extracted_text: str) -> str:
    """Extract Hindi chapter labels without translating them to English."""
    raw_lines = [
        line.strip()
        for line in (extracted_text or "").splitlines()
        if line.strip()
    ]
    lines = []

    for raw_line in raw_lines:
        cleaned_line = clean_pdf_label_text(raw_line).strip(" \t:-–—।")

        if cleaned_line:
            lines.append(cleaned_line)

    for line in lines[:16]:
        if re.search(r"विषय\s*सूची|अनुक्रमणिका|सामग्री", line):
            return "विषय सूची"

    for line in lines[:36]:
        chapter_match = re.match(
            r"^(पाठ|अध्याय)\s*([०-९0-9]+)\s*[:：.\-–—]?\s+(.{2,90})$",
            line,
        )
        if chapter_match:
            return normalize_hindi_section_title(
                chapter_match.group(1),
                chapter_match.group(2),
                chapter_match.group(3),
            )

        title_before_chapter = re.match(
            r"^(.{2,90}?)\s+(पाठ|अध्याय)\s*([०-९0-9]+)\b",
            line,
        )
        if title_before_chapter and contains_devanagari(title_before_chapter.group(1)):
            return normalize_hindi_section_title(
                title_before_chapter.group(2),
                title_before_chapter.group(3),
                title_before_chapter.group(1),
            )

        numbered_title = re.match(r"^([०-९0-9]+)\s+(.{2,90})$", line)
        if numbered_title and contains_devanagari(numbered_title.group(2)):
            return normalize_hindi_section_title(
                "पाठ",
                numbered_title.group(1),
                numbered_title.group(2),
            )

    return ""


def infer_title_from_grade_heading(extracted_text: str) -> str:
    """
    Extract chapter labels from single-line NCERT PDF text.

    Some PDFs flatten the first page into one long line like:
    "Curiosity Textbook of Science for Grade 8 Pressure, Winds... 6 z Why..."
    This recovers the chapter title before the exercise/opening question text.
    """
    normalized_text = clean_pdf_label_text(extracted_text)
    match = re.search(
        (
            r"\bgrade\s+\d+\s+"
            r"(?P<title>[A-Z][A-Za-z0-9,()'’&/\- ]{4,110}?)"
            r"\s+(?P<number>\d{1,2})\s+"
            r"(?=z\b|why\b|probe\b|chapter\b|let\b|in\b)"
        ),
        normalized_text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    title = match.group("title").strip(" :-–—")
    chapter_number = match.group("number")
    title = re.sub(r"\s+", " ", title)

    if len(title.split()) < 2:
        return ""

    return f"Chapter {chapter_number}: {title}"


def infer_book_section_title(filename: str, extracted_text: str, index: int) -> str:
    """
    Suggest a TOC/chapter label from extracted file text before RAG upload.

    The heuristic intentionally stays simple and predictable: it detects table
    of contents pages and common chapter-heading lines, then falls back to the
    original file name for admin review.
    """
    fallback = readable_title_from_filename(filename, index)
    raw_lines = [
        line.strip()
        for line in (extracted_text or "").splitlines()
        if line.strip()
    ]
    lines = []

    for raw_line in raw_lines:
        if re.search(r"\.indd\b|\d{1,2}/\d{1,2}/\d{4}", raw_line, flags=re.IGNORECASE):
            continue

        cleaned_line = clean_pdf_label_text(raw_line).strip(" \t:-–—")

        if cleaned_line:
            lines.append(cleaned_line)

    for line in lines[:12]:
        lower_line = line.lower()
        if "contents" in lower_line or "table of contents" in lower_line:
            return "Table of Contents"

    if contains_devanagari(extracted_text):
        hindi_title = infer_hindi_section_title(extracted_text)

        if hindi_title:
            return hindi_title

    grade_heading_title = infer_title_from_grade_heading(extracted_text)

    if grade_heading_title:
        return grade_heading_title

    for line_index, line in enumerate(lines[:24]):
        words = line.split()
        lower_line = line.lower()

        # ---- Chapter N: Title patterns ----
        title_before_chapter = re.match(
            r"^(.{4,90}?)\s+chapter\s+(\d{1,2})\b",
            line,
            flags=re.IGNORECASE,
        )
        if title_before_chapter:
            title = title_before_chapter.group(1).strip(" :-–—")
            chapter_number = title_before_chapter.group(2)
            return f"Chapter {chapter_number}: {title}"

        chapter_with_title = re.match(
            r"^chapter\s+(\d{1,2})\s*[:.-]?\s+(.{4,90})",
            line,
            flags=re.IGNORECASE,
        )
        if chapter_with_title:
            chapter_number = chapter_with_title.group(1)
            title = chapter_with_title.group(2).strip(" :-–—")
            return f"Chapter {chapter_number}: {title}"

        # ---- Unit N: Title patterns (textbooks that use Units instead of Chapters) ----
        title_before_unit = re.match(
            r"^(.{4,90}?)\s+unit\s+(\d{1,2})\b",
            line,
            flags=re.IGNORECASE,
        )
        if title_before_unit:
            title = title_before_unit.group(1).strip(" :-–—")
            unit_number = title_before_unit.group(2)
            return f"Unit {unit_number}: {title}"

        unit_with_title = re.match(
            r"^unit\s+(\d{1,2})\s*[:.-]?\s+(.{4,90})",
            line,
            flags=re.IGNORECASE,
        )
        if unit_with_title:
            unit_number = unit_with_title.group(1)
            title = unit_with_title.group(2).strip(" :-–—")
            return f"Unit {unit_number}: {title}"

        # ---- Bare "Chapter N" or "Unit N" — peek at the next line for the title ----
        if lower_line.startswith("chapter") and len(words) <= 4:
            chapter_match = re.search(r"chapter\s+(\d{1,2})", line, flags=re.IGNORECASE)
            if chapter_match:
                next_lines = lines[line_index + 1 : line_index + 3]
                for next_line in next_lines:
                    next_clean = next_line.strip(" :-–—")
                    if (
                        2 <= len(next_clean.split()) <= 12
                        and not re.search(
                            r"^\d+$|let us|activities|listen|read|watch|look|do these",
                            next_clean,
                            flags=re.IGNORECASE,
                        )
                    ):
                        return f"Chapter {chapter_match.group(1)}: {next_clean}"
            return line

        if lower_line.startswith("unit") and len(words) <= 4:
            unit_match = re.search(r"unit\s+(\d{1,2})", line, flags=re.IGNORECASE)
            if unit_match:
                next_lines = lines[line_index + 1 : line_index + 3]
                for next_line in next_lines:
                    next_clean = next_line.strip(" :-–—")
                    if (
                        2 <= len(next_clean.split()) <= 12
                        and not re.search(
                            r"^\d+$|let us|activities|listen|read|watch|look|do these",
                            next_clean,
                            flags=re.IGNORECASE,
                        )
                    ):
                        return f"Unit {unit_match.group(1)}: {next_clean}"
            return line

    chapter_number = infer_chapter_number_from_filename(filename)

    if chapter_number:
        return f"Chapter {chapter_number}"

    return fallback


def is_weak_section_title(title: str, filename: str) -> bool:
    """Identify labels that need AI help before admin confirmation."""
    normalized_title = (title or "").strip().lower()
    filename_title = readable_title_from_filename(filename, 0).strip().lower()

    return (
        not normalized_title
        or normalized_title == "chapter"
        or normalized_title == "unit"
        or bool(re.fullmatch(r"chapter\s+\d{1,2}", normalized_title))
        or bool(re.fullmatch(r"unit\s+\d{1,2}", normalized_title))
        or normalized_title == filename_title
        or bool(re.fullmatch(r"[a-z]{2,}\d+", normalized_title))
    )


def parse_ai_section_labels(raw_response: str) -> list[dict]:
    """Parse AI-suggested section labels from JSON, tolerating code fences."""
    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    parsed = json.loads(cleaned)

    if isinstance(parsed, dict):
        return parsed.get("sections", [])

    if isinstance(parsed, list):
        return parsed

    return []


def improve_book_section_labels_with_ai(sections: list[dict]) -> list[dict]:
    """
    Use a lightweight AI pass when local chapter-label heuristics are weak.

    The AI receives only short previews and returns one label per filename; the
    admin still reviews and confirms before anything is stored in RAG.
    """
    weak_sections = [
        section for section in sections
        if is_weak_section_title(
            section.get("suggested_title", ""),
            section.get("filename", ""),
        )
    ]

    if not weak_sections:
        return sections

    section_payload = [
        {
            "filename": section.get("filename", ""),
            "current_label": normalize_suggested_section_title(
                section.get("suggested_title", ""),
                section.get("filename", ""),
                section.get("preview", ""),
            ),
            "preview": clean_pdf_label_text(section.get("preview", ""))[:700],
        }
        for section in sections
    ]

    system_prompt = """
You label school textbook PDF files before RAG upload.
Return only valid JSON. Do not explain.
"""

    user_prompt = f"""
For each file, infer the clearest chapter/section label from filename and preview.

Rules:
- Prefer format "Chapter N: Title" when a chapter number is visible.
- If the preview is in Hindi/Devanagari, preserve Hindi script and prefer "पाठ N: शीर्षक" or "अध्याय N: शीर्षक".
- Do not translate Indian-language chapter titles to English.
- Use "Table of Contents" for contents pages.
- Do not return raw filenames like iesc101.
- Keep labels short and readable for an admin to confirm.
- Return exactly this JSON shape:
{{"sections":[{{"filename":"","suggested_title":""}}]}}

Files:
{json.dumps(section_payload, ensure_ascii=False)}
"""

    try:
        ai_response = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            username="admin",
            feature="rag_book_label_analysis",
            model=GPT5_TEXT_MODEL,
        )
        ai_sections = parse_ai_section_labels(ai_response)
        ai_title_by_filename = {
            item.get("filename"): item.get("suggested_title", "").strip()
            for item in ai_sections
            if isinstance(item, dict)
        }
    except Exception:
        return sections

    improved_sections = []

    for section in sections:
        ai_title = ai_title_by_filename.get(section.get("filename", ""))
        if ai_title:
            section = {
                **section,
                "suggested_title": normalize_suggested_section_title(
                    ai_title,
                    section.get("filename", ""),
                    section.get("preview", ""),
                ),
            }
        else:
            section = {
                **section,
                "suggested_title": normalize_suggested_section_title(
                    section.get("suggested_title", ""),
                    section.get("filename", ""),
                    section.get("preview", ""),
                ),
            }
        improved_sections.append(section)

    return improved_sections


@router.post("/analyze-book-set")
async def analyze_book_set(
    files: list[UploadFile] = File(...),
):
    """
    Extract text and suggest editable TOC/chapter labels before RAG upload.

    Nothing is persisted here. The admin reviews the suggestions and the final
    upload still happens through /book-set-upload.
    """
    try:
        if len(files) > 20:
            return {
                "success": False,
                "message": "You can analyze a maximum of 20 book files at once.",
                "sections": [],
            }

        sections = []

        for index, file in enumerate(files, start=1):
            try:
                file_bytes = await file.read()
                extracted_text = extract_text_from_uploaded_file(
                    filename=file.filename,
                    file_bytes=file_bytes,
                )
                word_count = len(extracted_text.split())

                sections.append({
                    "filename": file.filename,
                    "suggested_title": infer_book_section_title(
                        file.filename,
                        extracted_text,
                        index,
                    ),
                    "word_count": word_count,
                    "preview": extracted_text[:500],
                    "warnings": (
                        ["Low text detected. Review scan quality before upload."]
                        if word_count < 12
                        else []
                    ),
                })

            except Exception as file_error:
                sections.append({
                    "filename": file.filename,
                    "suggested_title": readable_title_from_filename(
                        file.filename,
                        index,
                    ),
                    "word_count": 0,
                    "preview": "",
                    "warnings": [f"Analysis failed: {str(file_error)}"],
                })

        sections = improve_book_section_labels_with_ai(sections)

        return {
            "success": True,
            "message": "Book files analyzed. Review suggested labels before upload.",
            "sections": sections,
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Book set analysis failed: {str(exc)}",
            "sections": [],
        }


@router.post("/jobs/analyze-full-book")
async def start_full_book_analysis_job(
    ocr_scanned: bool = Form(False),
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    """Start background full-book analysis and return a pollable job id."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Full book splitter currently supports PDF files only.",
        )

    file_bytes = await file.read()
    job = create_rag_job(
        job_type="full_book_analysis",
        filename=file.filename,
        file_size=len(file_bytes),
        created_by=_admin["profile"].get("id"),
        message="Full-book analysis queued.",
    )
    submit_rag_job(
        run_full_book_analysis_job,
        job_id=job["id"],
        filename=file.filename,
        file_bytes=file_bytes,
        ocr_scanned=ocr_scanned,
    )

    return {
        "success": True,
        "job_id": job["id"],
        "job": job,
        "message": "Full-book analysis started.",
    }


@router.post("/jobs/upload-full-book-sections")
async def start_full_book_upload_job(
    username: str = Form(...),
    grade: str = Form(...),
    board: str = Form("CBSE"),
    subject: str = Form(...),
    book_title: str = Form(...),
    chapters_json: str = Form(...),
    ocr_scanned: bool = Form(False),
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    """Start background chapter upload/embedding and return a pollable job id."""
    try:
        raw_chapters = json.loads(chapters_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chapter selections must be valid JSON.",
        ) from exc

    if not isinstance(raw_chapters, list):
        raise HTTPException(
            status_code=400,
            detail="Chapter selections must be a list.",
        )

    chapters = [FullBookChapterSelection(**item) for item in raw_chapters]
    included_chapters = [
        chapter for chapter in chapters
        if chapter.include and chapter.title.strip()
    ]

    if not included_chapters:
        raise HTTPException(
            status_code=400,
            detail="Select at least one chapter to upload.",
        )

    file_bytes = await file.read()
    job = create_rag_job(
        job_type="full_book_upload",
        filename=file.filename,
        file_size=len(file_bytes),
        created_by=_admin["profile"].get("id"),
        message="Full-book RAG upload queued.",
    )
    update_rag_job(
        job["id"],
        total_chapters=len(included_chapters),
    )
    submit_rag_job(
        run_full_book_upload_job,
        job_id=job["id"],
        username=username,
        grade=grade,
        board=board,
        subject=subject,
        book_title=book_title,
        chapters=chapters,
        filename=file.filename,
        file_bytes=file_bytes,
        ocr_scanned=ocr_scanned,
    )

    return {
        "success": True,
        "job_id": job["id"],
        "job": get_rag_job(job["id"]) or job,
        "message": "Full-book RAG upload started.",
    }


@router.get("/jobs/{job_id}")
def read_rag_upload_job(
    job_id: str,
    _admin=Depends(require_admin),
):
    """Return current status/progress for one RAG upload job."""
    job = get_rag_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="RAG upload job not found.",
        )

    return {
        "success": True,
        "job": job,
    }


@router.get("/jobs")
def read_recent_rag_upload_jobs(
    _admin=Depends(require_admin),
):
    """Return recent RAG jobs so admins can monitor parallel batches."""
    return {
        "success": True,
        "jobs": list_recent_rag_jobs(),
    }


@router.post("/analyze-full-book")
async def analyze_full_book(
    ocr_scanned: bool = Form(False),
    file: UploadFile = File(...),
):
    """
    Analyze one full textbook PDF and suggest chapter page ranges.

    Nothing is persisted here. Admins review/correct the page ranges before the
    confirm endpoint creates one RAG document per chapter.
    """
    try:
        file_bytes = await file.read()
        pages, warnings = extract_full_book_pages(
            filename=file.filename,
            file_bytes=file_bytes,
            ocr_scanned=ocr_scanned,
        )
        chapters = detect_full_book_chapters(pages)

        return build_full_book_analysis_payload(pages, warnings, chapters)

    except Exception as exc:
        return {
            "success": False,
            "message": f"Full book analysis failed: {str(exc)}",
            "page_count": 0,
            "word_count": 0,
            "extraction_methods": [],
            "warnings": [],
            "chapters": [],
        }


@router.post("/upload-full-book-sections")
async def upload_full_book_sections(
    username: str = Form(...),
    grade: str = Form(...),
    board: str = Form("CBSE"),
    subject: str = Form(...),
    book_title: str = Form(...),
    chapters_json: str = Form(...),
    ocr_scanned: bool = Form(False),
    file: UploadFile = File(...),
):
    """
    Persist reviewed full-book chapter ranges as separate RAG documents.

    Each included chapter becomes its own RAG document so student dropdowns and
    retrieval stay chapter-aware even when the source was one complete PDF.
    """
    try:
        raw_chapters = json.loads(chapters_json)

        if not isinstance(raw_chapters, list):
            raise ValueError("Chapter selections must be a list.")

        chapters = [FullBookChapterSelection(**item) for item in raw_chapters]
        included_chapters = [
            chapter for chapter in chapters
            if chapter.include and chapter.title.strip()
        ]

        if not included_chapters:
            return {
                "success": False,
                "message": "Select at least one chapter to upload.",
                "results": [],
            }

        file_bytes = await file.read()
        pages, extraction_warnings = extract_full_book_pages(
            filename=file.filename,
            file_bytes=file_bytes,
            ocr_scanned=ocr_scanned,
        )
        page_count = len(pages)
        upload_results = []

        for chapter in included_chapters:
            if chapter.start_page < 1 or chapter.end_page < chapter.start_page:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": "Invalid chapter page range.",
                    "chunks_created": 0,
                })
                continue

            if chapter.end_page > page_count:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": f"End page exceeds PDF page count ({page_count}).",
                    "chunks_created": 0,
                })
                continue

            chapter_text = combine_pages_for_range(
                pages,
                chapter.start_page,
                chapter.end_page,
            )

            if len(chapter_text.split()) < 30:
                upload_results.append({
                    "title": chapter.title,
                    "success": False,
                    "message": "Too little readable text in this page range.",
                    "chunks_created": 0,
                })
                continue

            document_title = f"{book_title.strip()} - {chapter.title.strip()}"
            result = upload_textbook_text(
                username=username,
                board=board,
                grade=grade.strip(),
                subject=subject.strip(),
                chapter=chapter.title.strip(),
                title=document_title,
                text=chapter_text,
            )

            upload_results.append({
                "title": document_title,
                "chapter": chapter.title.strip(),
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "document_id": result.get("document_id"),
                "chunks_created": result.get("chunks_created", 0),
            })

        successful = [
            item for item in upload_results
            if item.get("success")
        ]

        return {
            "success": len(successful) > 0,
            "message": (
                f"{len(successful)} of {len(included_chapters)} chapters uploaded."
            ),
            "warnings": extraction_warnings,
            "results": upload_results,
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Full book chapter upload failed: {str(exc)}",
            "results": [],
        }


def run_sof_analysis_job(
    *,
    job_id: str,
    grade: str,
    files_data: list,
) -> None:
    """
    Background worker: OCR all SOF image/photo files, then use the LLM
    organizer to group pages by subject and chapter for RAG upload.
    Progress is persisted to rag_upload_jobs so the admin can poll for status.
    """
    total_files = len(files_data)
    try:
        update_rag_job(
            job_id,
            status="running",
            phase="extracting_pages",
            percent=2,
            page_count=total_files,
            message=f"Starting OCR for {total_files} file(s).",
        )

        pages: list[dict] = []
        file_warnings: list[dict] = []

        for i, fd in enumerate(files_data):
            filename = fd["filename"]
            file_bytes = fd["file_bytes"]
            try:
                extracted_pages = extract_pages_from_uploaded_file(
                    filename=filename,
                    file_bytes=file_bytes,
                )
            except Exception as file_error:
                file_warnings.append({
                    "filename": filename,
                    "message": f"Could not extract text: {str(file_error)}",
                })
                continue

            if len(pages) + len(extracted_pages) > 60:
                file_warnings.append({
                    "filename": filename,
                    "message": "Skipped — 60-page limit reached.",
                })
                continue

            for ep in extracted_pages:
                pages.append({
                    "page_number": len(pages) + 1,
                    "source_page_number": ep["page_number"],
                    "filename": ep["filename"],
                    "ocr_text": ep["text"],
                    "word_count": ep["word_count"],
                    "extraction_method": ep["extraction_method"],
                    "warnings": ep["warnings"],
                })

            pct = 2 + int((i + 1) / total_files * 68)
            update_rag_job(
                job_id,
                phase="extracting_pages",
                processed_pages=len(pages),
                percent=pct,
                message=f"OCR: {i + 1}/{total_files} files done — {len(pages)} pages extracted.",
            )

        if not pages:
            update_rag_job(
                job_id,
                status="failed",
                phase="failed",
                percent=100,
                error_message="No readable text extracted.",
                message="No readable text could be extracted from the selected SOF files.",
                result={"success": False, "pages": [], "groups": [], "file_warnings": file_warnings},
                warnings=file_warnings,
            )
            return

        update_rag_job(
            job_id,
            phase="organizing",
            percent=72,
            message=f"Organizing {len(pages)} pages with AI.",
        )

        combined_ocr = "\n\n".join(
            f"PAGE {p['page_number']} - {p['filename']} "
            f"(source page {p['source_page_number']}, "
            f"{p['extraction_method']}, {p['word_count']} words)\n"
            f"{p['ocr_text']}"
            for p in pages
        )
        canonical_toc = build_sof_catalog_prompt(grade)

        sof_system_prompt = """
You are an educational OCR organizer for SOF Olympiad books.

Your job:
- Read OCR text from up to 20 uploaded SOF files.
- Group pages by SOF subject and chapter.
- Return ONLY valid JSON.
- Never return markdown.
- Never return explanations.

Important subject rules:
For SOF content, subject must be exactly one of:
- Science Olympiad
- Maths Olympiad
- English Olympiad

Never return Science, Maths, or English for SOF content.

Use canonical TOC chapter names when a canonical chapter is provided. For
uploaded Class 1-10 books without a canonical TOC, preserve the clearest chapter
or section title visible in OCR. If OCR shows ISO, IMO, or IEO, map it to the
matching SOF subject and model paper title.
"""

        sof_user_prompt = f"""
Analyze these OCR pages and organize them for SOF RAG upload.

Return JSON in this exact format:

{{
  "groups": [
    {{
      "grade": "{grade}",
      "subject": "Science Olympiad or Maths Olympiad or English Olympiad",
      "chapter": "",
      "title": "",
      "page_numbers": [],
      "confidence": "",
      "combined_text": ""
    }}
  ]
}}

Rules:
- If multiple pages belong to the same chapter, combine them into one group.
- If a page is table of contents, use it to identify the subject/book but do not create RAG content unless useful.
- If uncertain, still create the best possible group with confidence "Low".
- subject must exactly match one canonical SOF subject.
- chapter should match a canonical chapter when available; otherwise preserve the clearest OCR chapter or section title.
- title should clearly identify the SOF subject, chapter, and whether the content is chapter content, exercise, or model test paper.
- combined_text must include the useful learning content from the matching pages.

{canonical_toc}

OCR PAGES:

{combined_ocr[:18000]}
"""

        ai_response = ask_llm(
            system_prompt=sof_system_prompt,
            user_prompt=sof_user_prompt,
            username="admin",
            feature="rag_sof_bulk_analysis",
            model=GPT5_TEXT_MODEL,
        )

        update_rag_job(job_id, phase="parsing_result", percent=90, message="Parsing AI response.")

        try:
            parsed = json.loads(ai_response)
            raw_groups = parsed.get("groups", [])
        except Exception as parse_error:
            update_rag_job(
                job_id,
                status="failed",
                phase="failed",
                percent=100,
                error_message=f"Invalid JSON from organizer: {str(parse_error)}",
                message="SOF organizer returned invalid JSON.",
                result={
                    "success": False,
                    "pages": pages,
                    "groups": [],
                    "raw_ai_response": ai_response,
                    "file_warnings": file_warnings,
                },
            )
            return

        if not isinstance(raw_groups, list):
            raw_groups = []

        groups = []
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            normalized_group = normalize_sof_group(group, fallback_grade=grade)
            if normalized_group["combined_text"]:
                groups.append(normalized_group)

        final_message = (
            "SOF files analyzed with warnings."
            if file_warnings
            else "SOF files analyzed successfully."
        )
        update_rag_job(
            job_id,
            status="completed",
            phase="ready_for_review",
            page_count=len(pages),
            processed_pages=len(pages),
            percent=100,
            message=final_message,
            warnings=file_warnings,
            result={
                "success": True,
                "pages": pages,
                "groups": groups,
                "file_warnings": file_warnings,
                "message": final_message,
            },
        )

    except Exception as exc:
        update_rag_job(
            job_id,
            status="failed",
            phase="failed",
            percent=100,
            error_message=str(exc),
            message=f"SOF analysis failed: {str(exc)}",
            result={"success": False, "pages": [], "groups": [], "error": str(exc)},
        )


@router.post("/analyze-sof-images")
async def analyze_sof_images(
    grade: str = Form("Grade 9"),
    files: list[UploadFile] = File(...),
):
    """
    Submit SOF camera photos or PDFs for background OCR and AI organization.

    Returns a job_id immediately — no waiting. Poll GET /api/rag/jobs/{job_id}
    for progress. When status is "completed", the result contains pages and
    groups ready for /confirm-sof-upload.
    """
    if len(files) > 20:
        return {
            "success": False,
            "message": "You can analyze a maximum of 20 files at once.",
            "pages": [],
            "groups": [],
        }

    # Read file bytes now (fast - just memory copy, no OCR yet)
    files_data = []
    for f in files:
        file_bytes = await f.read()
        files_data.append({
            "filename": f.filename or "upload.jpg",
            "file_bytes": file_bytes,
        })

    if not files_data:
        return {"success": False, "message": "No files received.", "pages": [], "groups": []}

    total_size = sum(len(fd["file_bytes"]) for fd in files_data)
    job = create_rag_job(
        job_type="sof_analysis",
        filename=f"{len(files_data)} SOF file(s)",
        file_size=total_size,
        message="SOF OCR analysis queued.",
    )

    submit_rag_job(
        run_sof_analysis_job,
        job_id=job["id"],
        grade=grade,
        files_data=files_data,
    )

    return {
        "success": True,
        "async": True,
        "job_id": job["id"],
        "job": job,
        "message": (
            f"{len(files_data)} SOF file(s) queued for background analysis. "
            f"Poll /api/rag/jobs/{job['id']} for progress."
        ),
    }


@router.post("/bulk-book-upload")
async def bulk_book_upload(
    username: str = Form(...),
    metadata_json: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """
    Upload Class 1-10 CBSE books with per-file grade and subject metadata.

    This endpoint is for full subject books or large book PDFs. The content is
    stored under the stable "Uploaded Book Content" chapter unless the admin
    supplies a more specific chapter label in the metadata.
    """
    try:
        if len(files) > 20:
            return {
                "success": False,
                "message": "You can upload a maximum of 20 books at once.",
                "results": [],
            }

        metadata = parse_bulk_book_metadata(metadata_json, len(files))
        upload_results = []

        for index, file in enumerate(files):
            item = metadata[index]

            try:
                file_bytes = await file.read()
                extracted_text = extract_text_from_uploaded_file(
                    filename=file.filename,
                    file_bytes=file_bytes,
                )

                result = upload_textbook_text(
                    username=username,
                    board=item.board,
                    grade=item.grade.strip(),
                    subject=item.subject.strip(),
                    chapter=(item.chapter or "Uploaded Book Content").strip(),
                    title=item.title.strip(),
                    text=extracted_text,
                )

                upload_results.append({
                    "filename": file.filename,
                    "grade": item.grade,
                    "subject": item.subject,
                    "chapter": item.chapter,
                    "title": item.title,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "document_id": result.get("document_id"),
                    "chunks_created": result.get("chunks_created", 0),
                })

            except Exception as file_error:
                upload_results.append({
                    "filename": file.filename,
                    "grade": item.grade,
                    "subject": item.subject,
                    "chapter": item.chapter,
                    "title": item.title,
                    "success": False,
                    "message": f"Upload failed: {str(file_error)}",
                    "document_id": None,
                    "chunks_created": 0,
                })

        successful = [
            item for item in upload_results
            if item["success"]
        ]

        return {
            "success": len(successful) > 0,
            "message": f"{len(successful)} of {len(files)} books uploaded successfully.",
            "results": upload_results,
        }

    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "results": [],
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Bulk book upload failed: {str(exc)}",
            "results": [],
        }


@router.post("/book-set-upload")
async def book_set_upload(
    username: str = Form(...),
    board: str = Form("CBSE"),
    grade: str = Form(...),
    subject: str = Form(...),
    book_title: str = Form(...),
    section_titles: str = Form(""),
    files: list[UploadFile] = File(...),
):
    """
    Upload one book that is split across multiple TOC/chapter files.

    Each file becomes a separate RAG document under the same grade, subject, and
    book title prefix, while the chapter field stores the section title. This
    keeps retrieval chapter-aware without needing a new database table.
    """
    try:
        if len(files) > 20:
            return {
                "success": False,
                "message": "You can upload a maximum of 20 book files at once.",
                "results": [],
            }

        clean_book_title = book_title.strip()
        if not clean_book_title:
            return {
                "success": False,
                "message": "Book title is required.",
                "results": [],
            }

        if not grade.strip() or not subject.strip():
            return {
                "success": False,
                "message": "Grade and subject are required.",
                "results": [],
            }

        resolved_titles = parse_book_section_titles(section_titles, files)
        upload_results = []

        for index, file in enumerate(files):
            section_title = resolved_titles[index]
            document_title = f"{clean_book_title} - {section_title}"

            try:
                file_bytes = await file.read()
                extracted_text = extract_text_from_uploaded_file(
                    filename=file.filename,
                    file_bytes=file_bytes,
                )

                result = upload_textbook_text(
                    username=username,
                    board=board,
                    grade=grade.strip(),
                    subject=subject.strip(),
                    chapter=section_title,
                    title=document_title,
                    text=extracted_text,
                )

                upload_results.append({
                    "filename": file.filename,
                    "grade": grade,
                    "subject": subject,
                    "chapter": section_title,
                    "title": document_title,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "document_id": result.get("document_id"),
                    "chunks_created": result.get("chunks_created", 0),
                })

            except Exception as file_error:
                upload_results.append({
                    "filename": file.filename,
                    "grade": grade,
                    "subject": subject,
                    "chapter": section_title,
                    "title": document_title,
                    "success": False,
                    "message": f"Upload failed: {str(file_error)}",
                    "document_id": None,
                    "chunks_created": 0,
                })

        successful = [
            item for item in upload_results
            if item["success"]
        ]

        return {
            "success": len(successful) > 0,
            "message": f"{len(successful)} of {len(files)} book files uploaded successfully.",
            "results": upload_results,
        }

    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "results": [],
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Book set upload failed: {str(exc)}",
            "results": [],
        }


@router.post("/confirm-sof-upload")
def confirm_sof_upload(data: ConfirmSofUploadRequest):
    """
    Validate normalized SOF groups and upload each accepted group into RAG.

    Groups with subject/chapter normalization warnings are rejected rather than
    silently filed under the wrong canonical document title.
    """
    try:
        results = []

        for group in data.groups:
            group_data = (
                group.model_dump()
                if hasattr(group, "model_dump")
                else group.dict()
            )
            normalized_group = normalize_sof_group(
                group_data,
                fallback_grade=group.grade,
            )

            if normalized_group.get("subject") not in get_sof_subjects():
                results.append({
                    "success": False,
                    "title": normalized_group.get("title") or group.title,
                    "message": f"Invalid SOF subject: {group.subject}",
                    "document_id": None,
                    "chunks_created": 0,
                })
                continue

            if normalized_group.get("normalization_warning"):
                results.append({
                    "success": False,
                    "title": normalized_group.get("title") or group.title,
                    "subject": normalized_group.get("subject") or group.subject,
                    "chapter": normalized_group.get("chapter") or group.chapter,
                    "message": normalized_group["normalization_warning"],
                    "document_id": None,
                    "chunks_created": 0,
                })
                continue

            result = upload_textbook_text(
                username=data.username,
                board="CBSE",
                grade=normalized_group["grade"],
                subject=normalized_group["subject"],
                chapter=normalized_group["chapter"],
                title=normalized_group["title"],
                text=normalized_group["combined_text"],
            )

            results.append({
                "success": result.get("success", False),
                "title": normalized_group["title"],
                "subject": normalized_group["subject"],
                "chapter": normalized_group["chapter"],
                "message": result.get("message", ""),
                "document_id": result.get("document_id"),
                "chunks_created": result.get("chunks_created", 0),
            })

        successful = [
            item for item in results
            if item["success"]
        ]

        return {
            "success": len(successful) > 0,
            "message": f"{len(successful)} of {len(results)} SOF groups uploaded.",
            "results": results,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"SOF upload failed: {str(e)}",
            "results": [],
        }

@router.post("/search", response_model=RagSearchResponse)
def search_rag(data: RagSearchRequest):
    """Run a manual RAG search for admin/debug verification."""
    try:
        results = search_textbook_content(
            query=data.query,
            board=data.board,
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            match_count=data.match_count,
        )

        return RagSearchResponse(
            success=True,
            results=results,
            message="RAG search completed successfully",
        )

    except Exception as e:
        return RagSearchResponse(
            success=False,
            results=[],
            message=f"RAG search failed: {str(e)}",
        )
