from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from app.services.file_extract_service import (
    extract_pages_from_uploaded_file,
    extract_text_from_uploaded_file,
)
from app.services.openai_service import ask_llm
import json
from pydantic import BaseModel
from typing import List, Optional


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
    delete_rag_document,
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
    documents = list_rag_documents()

    return {
        "success": True,
        "documents": documents,
    }


@router.delete("/documents/{document_id}")
def remove_rag_document(document_id: str):
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


@router.post("/analyze-sof-images")
async def analyze_sof_images(
    grade: str = Form("Grade 9"),
    files: list[UploadFile] = File(...),
):
    try:
        if len(files) > 20:
            return {
                "success": False,
                "message": "You can analyze a maximum of 20 files at once.",
                "pages": [],
                "groups": [],
            }

        pages = []

        for file in files:
            file_bytes = await file.read()
            extracted_pages = extract_pages_from_uploaded_file(
                filename=file.filename,
                file_bytes=file_bytes,
            )

            if len(pages) + len(extracted_pages) > 60:
                return {
                    "success": False,
                    "message": "You can analyze a maximum of 60 extracted pages at once.",
                    "pages": pages,
                    "groups": [],
                }

            for extracted_page in extracted_pages:
                pages.append({
                    "page_number": len(pages) + 1,
                    "source_page_number": extracted_page["page_number"],
                    "filename": extracted_page["filename"],
                    "ocr_text": extracted_page["text"],
                    "word_count": extracted_page["word_count"],
                    "extraction_method": extracted_page["extraction_method"],
                    "warnings": extracted_page["warnings"],
                })

        combined_ocr = "\n\n".join(
            [
                (
                    f"PAGE {page['page_number']} - {page['filename']} "
                    f"(source page {page['source_page_number']}, "
                    f"{page['extraction_method']}, {page['word_count']} words)\n"
                    f"{page['ocr_text']}"
                )
                for page in pages
            ]
        )

        system_prompt = """
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

Use chapter names from the page text whenever possible.
"""

        user_prompt = f"""
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
- If a page is table of contents, extract chapter names but do not create RAG content unless useful.
- If uncertain, still create the best possible group with confidence "Low".
- combined_text must include the useful learning content from the matching pages.

OCR PAGES:

{combined_ocr[:18000]}
"""

        ai_response = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            username="admin",
            feature="rag_sof_bulk_analysis",
        )

        try:
            parsed = json.loads(ai_response)
            groups = parsed.get("groups", [])
        except Exception:
            groups = []

        return {
            "success": True,
            "pages": pages,
            "groups": groups,
            "raw_ai_response": ai_response,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"SOF image analysis failed: {str(e)}",
            "pages": [],
            "groups": [],
        }


@router.post("/confirm-sof-upload")
def confirm_sof_upload(data: ConfirmSofUploadRequest):
    try:
        results = []

        for group in data.groups:
            if group.subject not in [
                "Science Olympiad",
                "Maths Olympiad",
                "English Olympiad",
            ]:
                results.append({
                    "success": False,
                    "title": group.title,
                    "message": f"Invalid SOF subject: {group.subject}",
                    "document_id": None,
                    "chunks_created": 0,
                })
                continue

            result = upload_textbook_text(
                username=data.username,
                grade=group.grade,
                subject=group.subject,
                chapter=group.chapter,
                title=group.title,
                text=group.combined_text,
            )

            results.append({
                "success": result.get("success", False),
                "title": group.title,
                "subject": group.subject,
                "chapter": group.chapter,
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
