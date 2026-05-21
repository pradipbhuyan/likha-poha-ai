from fastapi import APIRouter, File, Form, UploadFile
from app.services.file_extract_service import extract_text_from_uploaded_file


from app.models.schemas import (
    RagTextUploadRequest,
    RagUploadResponse,
    RagSearchRequest,
    RagSearchResponse,
)

from app.services.rag_service import (
    upload_textbook_text,
    search_textbook_content,
)

from app.services.ocr_service import extract_text_from_image_bytes

router = APIRouter()


@router.post("/upload-text", response_model=RagUploadResponse)
def upload_text(data: RagTextUploadRequest):
    result = upload_textbook_text(
        username=data.username,
        grade=data.grade,
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
    subject: str = Form(...),
    chapter: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    image_bytes = await file.read()

    extracted_text = extract_text_from_image_bytes(image_bytes)

    result = upload_textbook_text(
        username=username,
        grade=grade,
        subject=subject,
        chapter=chapter,
        title=title,
        text=extracted_text,
    )

    return RagUploadResponse(**result)

@router.post("/search", response_model=RagSearchResponse)
def search_rag(data: RagSearchRequest):
    try:
        results = search_textbook_content(
            query=data.query,
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
    
@router.post("/upload-file", response_model=RagUploadResponse)
async def upload_file(
    username: str = Form(...),
    grade: str = Form(...),
    subject: str = Form(...),
    chapter: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()

        extracted_text = extract_text_from_uploaded_file(
            filename=file.filename,
            file_bytes=file_bytes,
        )

        result = upload_textbook_text(
            username=username,
            grade=grade,
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
