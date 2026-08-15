from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from app.services.file_extract_service import extract_text_from_uploaded_file
from app.services.openai_service import ask_llm
from pydantic import BaseModel
from typing import Optional


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
from app.services.rag_visual_service import (
    backfill_visual_assets_for_document,
    list_visual_assets_for_document,
    update_visual_asset,
)
from app.services.auth_service import admin_client, require_admin

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
def upload_text(data: RagTextUploadRequest, _admin=Depends(require_admin)):
    """Upload raw text as a RAG document and create searchable embeddings.

    Admin-only: this writes into the corpus that grounds every student-facing
    lesson and doubt answer, so it carries the same guard as the read routes
    below rather than trusting the client-supplied username for identity.
    """
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
    _admin=Depends(require_admin),
):
    """OCR one uploaded image and save the extracted text into RAG. Admin-only."""
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
    _admin=Depends(require_admin),
):
    """Extract text from one supported file type and save it into RAG. Admin-only."""
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
    _admin=Depends(require_admin),
):
    """
    Upload up to 20 files into RAG as separate documents. Admin-only.

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
def get_rag_documents(_admin=Depends(require_admin)):
    """Return uploaded RAG document metadata for the admin upload page. Admin-only."""
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
    """
    Return a short chunk preview so admins can verify title/content alignment.

    The document's grade must be resolved first so get_content_db() routes
    to the correct Supabase project (Supabase 1 for Grade 1-10,
    Supabase 2 for Grade 11-12). Without passing grade, the preview always
    reads from Supabase 1 which makes Grade 11/12 previews show wrong content.
    """
    # Step 1: Resolve the document grade by checking both databases.
    # We check Supabase 1 first (most documents), then Supabase 2 (Grade 11/12).
    from app.services.grade_db_router import get_content_db  # noqa: PLC0415

    grade = None
    for candidate_grade in (None, "Grade 11", "Grade 12"):
        db = get_content_db(candidate_grade)
        try:
            doc_resp = (
                db.table("rag_documents")
                .select("grade")
                .eq("id", document_id)
                .limit(1)
                .execute()
            )
            if doc_resp.data:
                grade = doc_resp.data[0].get("grade")
                break
        except Exception:
            continue

    chunks = get_rag_document_preview(document_id, grade=grade)

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
def remove_rag_document(document_id: str, _admin=Depends(require_admin)):
    """Delete a RAG document and all associated chunks by document id. Admin-only."""
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
    _admin=Depends(require_admin),
):
    """
    OCR and classify one textbook page image before upload. Admin-only.

    The endpoint suggests grade/subject/chapter metadata but does not persist
    anything; admins review the result before uploading. It still runs OCR and
    an LLM call per request, so it is guarded as a billable operation too.
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


@router.post("/search", response_model=RagSearchResponse)
def search_rag(data: RagSearchRequest, _admin=Depends(require_admin)):
    """Run a manual RAG search for admin/debug verification. Admin-only.

    Student-facing retrieval does not come through here — it runs inside the
    lesson/doubt services — so guarding this route does not affect learners.
    """
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
