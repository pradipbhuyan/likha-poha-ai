"""
rag_bulk_book_upload.py  —  /api/rag/*
─────────────────────────────────────────────────────────────────────────────
Full-book / bulk-book RAG ingestion: background job orchestration plus the
synchronous upload routes for admin-driven batch textbook uploads.

Extracted from app/routes/rag.py (previously ~1,500 of that file's 2,031
lines) — see app/services/rag_book_title_inference.py for the chapter/section
title-inference heuristics this file calls into, and app/routes/rag.py for
the direct-upload/document-management/search routes that stayed there.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.file_extract_service import extract_text_from_uploaded_file
from app.services.full_book_split_service import (
    combine_pages_for_range,
    detect_full_book_chapters,
    extract_full_book_pages,
)
from app.services.rag_service import upload_textbook_text
from app.services.rag_job_service import (
    create_rag_job,
    get_rag_job,
    list_recent_rag_jobs,
    submit_rag_job,
    update_rag_job,
)
from app.services.auth_service import require_admin
from app.services.rag_book_title_inference import (
    improve_book_section_labels_with_ai,
    infer_book_section_title,
    parse_book_section_titles,
    parse_bulk_book_metadata,
    readable_title_from_filename,
)

router = APIRouter()


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


@router.post("/analyze-book-set")
async def analyze_book_set(
    files: list[UploadFile] = File(...),
    _admin=Depends(require_admin),
):
    """
    Extract text and suggest editable TOC/chapter labels before RAG upload.
    Admin-only.

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
    _admin=Depends(require_admin),
):
    """
    Analyze one full textbook PDF and suggest chapter page ranges. Admin-only.

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
    _admin=Depends(require_admin),
):
    """
    Persist reviewed full-book chapter ranges as separate RAG documents.
    Admin-only.

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


@router.post("/bulk-book-upload")
async def bulk_book_upload(
    username: str = Form(...),
    metadata_json: str = Form(...),
    files: list[UploadFile] = File(...),
    _admin=Depends(require_admin),
):
    """
    Upload Class 1-10 CBSE books with per-file grade and subject metadata.
    Admin-only.

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
    _admin=Depends(require_admin),
):
    """
    Upload one book that is split across multiple TOC/chapter files. Admin-only.

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
