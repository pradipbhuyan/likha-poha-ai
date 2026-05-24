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


@router.post("/upload-files")
async def upload_files_batch(
    username: str = Form(...),
    grade: str = Form(...),
    subject: str = Form(...),
    chapter: str = Form(...),
    titles: str = Form(...),
    files: list[UploadFile] = File(...),
):
    try:
        if len(files) > 10:
            return {
                "success": False,
                "message": "You can upload a maximum of 10 documents at once.",
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