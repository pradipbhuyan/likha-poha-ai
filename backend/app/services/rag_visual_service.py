import re
import tempfile
from pathlib import Path

from fastapi import HTTPException

from app.services.auth_service import admin_client
from app.services.board_service import normalize_board


RAG_VISUAL_BUCKET = "rag-visuals"
MAX_VISUAL_PAGES_PER_BACKFILL = 80
RAG_VISUAL_ENABLED_CONTEXTS = {
    ("CBSE", "Grade 9"),
    ("CBSE", "Grade 10"),
    # Grade 5 added 2026-07-29 per direct user request — user reported no
    # textbook images appearing for the newly-ingested Grade 5 English
    # chapters and asked for this specifically, understanding the
    # Supabase Storage cost implication of enabling image storage for an
    # additional grade band.
    ("CBSE", "Grade 5"),
    # Grade 6 added 2026-07-30 per direct user request (Grade 6 English
    # ingestion session): 'add text book images, add reference pdfs
    # wherever applicable' -- same cost trade-off acknowledged as Grade 5.
    ("CBSE", "Grade 6"),
    # Grade 7 added 2026-07-30 per direct user request (Grade 7 Maths
    # ingestion session): 'ensure that text book images are added for
    # each chapter from 1 to 15 along with reference pdf viewer without
    # fail' -- same cost trade-off acknowledged as Grade 5/6.
    ("CBSE", "Grade 7"),
    # Grade 8 added 2026-07-30 per direct user confirmation (Grade 8
    # English ingestion session, asked explicitly via AskUserQuestion
    # before extending the allow-list) -- same cost trade-off acknowledged
    # as Grade 5/6/7.
    ("CBSE", "Grade 8"),
    # Grade 11 added 2026-07-31 per direct user request (Grade 11 Maths
    # ingestion session): "process Grade 11 Maths as per GPT55 doc
    # guideline. Ensure that images exist for each chapter and also pdf
    # ref link." -- same cost trade-off acknowledged as Grade 5/6/7/8.
    # This unblocked a real live bug: without this entry,
    # backfill_visual_assets_for_document() silently returned 0 visuals
    # created for every Grade 11 chapter, which made downstream curation
    # find "No rag_visual_assets rows found" and skip images entirely
    # even for figure-heavy chapters like Straight Lines and Conic
    # Sections.
    ("CBSE", "Grade 11"),
    # Grade 12 added 2026-08-01 per direct user request (Grade 12 English
    # remaining-chapters ingestion session): "process these remaining
    # Grade 12 English lessons. Text book images and reference pdf popup
    # is a must have." -- same cost trade-off acknowledged as
    # Grade 5/6/7/8/11. Without this entry, the 10 Grade 12 English
    # chapters processed earlier the same day (The Last Lesson, Lost
    # Spring, etc.) had backfill_visual_assets_for_document() silently
    # return 0 visuals for every chapter, forcing the plain-text
    # extract_text citation fallback -- this entry is required before
    # any Grade 12 chapter can get real page-image citations.
    ("CBSE", "Grade 12"),
}
VISUAL_REQUEST_TERMS = {
    "diagram",
    "visual",
    "image",
    "picture",
    "photo",
    "figure",
    "draw",
    "drawing",
    "show",
    "map",
    "graph",
    "chart",
    "flowchart",
    "depict",
    "illustration",
}
VISUAL_QUERY_STOPWORDS = {
    "the",
    "and",
    "for",
    "from",
    "this",
    "that",
    "with",
    "about",
    "chapter",
    "textbook",
    "visuals",
    "images",
    "pictures",
    "please",
}


def _slug(value: str) -> str:
    """Create a stable storage path segment without losing readability."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip())
    return cleaned.strip("-").lower() or "unknown"


def is_rag_visual_context_enabled(board: str, grade: str) -> bool:
    """Central allow-list for textbook visual storage/retrieval by class."""
    return (normalize_board(board), str(grade or "").strip()) in RAG_VISUAL_ENABLED_CONTEXTS


def _get_rag_document(document_id: str) -> dict:
    response = (
        admin_client
        .table("rag_documents")
        .select("id,title,board,grade,subject,chapter")
        .eq("id", document_id)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="RAG document not found.")

    return response.data


def _render_pdf_page_to_jpeg(page, scale: float = 1.6) -> bytes:
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise RuntimeError(
            "Textbook visual extraction requires PyMuPDF. Install backend "
            "requirement PyMuPDF and redeploy."
        ) from exc

    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return pixmap.tobytes("jpeg")


def _delete_existing_visual_rows(document_id: str, start_page: int, end_page: int):
    """Avoid duplicate page assets when an admin re-runs the same backfill."""
    response = (
        admin_client
        .table("rag_visual_assets")
        .select("id,storage_path")
        .eq("document_id", document_id)
        .gte("page_number", start_page)
        .lte("page_number", end_page)
        .execute()
    )

    for row in response.data or []:
        storage_path = row.get("storage_path")
        if storage_path:
            try:
                admin_client.storage.from_(RAG_VISUAL_BUCKET).remove([storage_path])
            except Exception:
                pass

    (
        admin_client
        .table("rag_visual_assets")
        .delete()
        .eq("document_id", document_id)
        .gte("page_number", start_page)
        .lte("page_number", end_page)
        .execute()
    )


def list_visual_assets_for_document(document_id: str) -> list[dict]:
    response = (
        admin_client
        .table("rag_visual_assets")
        .select("*")
        .eq("document_id", document_id)
        .order("page_number")
        .execute()
    )

    return response.data or []


def question_requests_visual(question: str) -> bool:
    """Detect whether the student explicitly asked for visual support."""
    normalized = str(question or "").lower()
    return any(term in normalized for term in VISUAL_REQUEST_TERMS)


def _visual_score(visual: dict, query: str) -> int:
    """Rank approved textbook visuals using simple caption/nearby-text overlap."""
    query_terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", str(query or "").lower())
        if (
            len(token) > 2
            and token not in VISUAL_REQUEST_TERMS
            and token not in VISUAL_QUERY_STOPWORDS
        )
    }
    haystack = " ".join([
        visual.get("caption") or "",
        visual.get("nearby_text") or "",
        visual.get("title") or "",
    ]).lower()

    return sum(1 for token in query_terms if token in haystack)


def find_visual_assets_for_question(
    *,
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    question: str,
    limit: int = 3,
) -> list[dict]:
    """Return approved textbook visuals for the exact selected context."""
    if not is_rag_visual_context_enabled(board, grade):
        return []

    if not question_requests_visual(question):
        return []

    try:
        response = (
            admin_client
            .table("rag_visual_assets")
            .select(
                "id,document_id,board,grade,subject,chapter,title,page_number,"
                "asset_url,caption,nearby_text,status"
            )
            .eq("status", "active")
            .eq("board", normalize_board(board))
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .order("page_number")
            .limit(25)
            .execute()
        )
    except Exception:
        return []

    visuals = response.data or []
    visuals.sort(key=lambda item: (-_visual_score(item, question), item.get("page_number") or 0))

    return visuals[:limit]


def list_active_visual_assets_for_context(
    *,
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    limit: int = 12,
) -> list[dict]:
    """List approved textbook visuals for the exact selected lesson context."""
    if not is_rag_visual_context_enabled(board, grade):
        return []

    try:
        response = (
            admin_client
            .table("rag_visual_assets")
            .select(
                "id,document_id,board,grade,subject,chapter,title,page_number,"
                "asset_url,caption,nearby_text,status"
            )
            .eq("status", "active")
            .eq("board", normalize_board(board))
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("chapter", chapter)
            .order("page_number")
            .limit(limit)
            .execute()
        )
    except Exception:
        return []

    return response.data or []


def search_visual_assets_for_context(
    *,
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    query: str,
    limit: int = 6,
) -> list[dict]:
    """Search approved visuals inside one lesson; return empty for off-context text."""
    if not is_rag_visual_context_enabled(board, grade):
        return []

    visuals = list_active_visual_assets_for_context(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        limit=25,
    )
    if not visuals:
        return []

    query_terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", str(query or "").lower())
        if (
            len(token) > 2
            and token not in VISUAL_REQUEST_TERMS
            and token not in VISUAL_QUERY_STOPWORDS
        )
    }

    if not query_terms:
        return visuals[:limit]

    scored_visuals = [
        (visual, _visual_score(visual, query))
        for visual in visuals
    ]
    matched_visuals = [
        visual
        for visual, score in sorted(
            scored_visuals,
            key=lambda item: (-(item[1]), item[0].get("page_number") or 0),
        )
        if score > 0
    ]

    return matched_visuals[:limit]


def get_lesson_step_visual_assets(
    *,
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    lesson_context: str = "",
    limit: int = 3,
) -> list[dict]:
    """
    Pick approved textbook visuals that can support a generated lesson step.

    This intentionally stays inside the exact board/grade/subject/chapter. If
    no page has strong keyword overlap, it falls back to the first active pages
    from the same chapter so the frontend can still show safe textbook context
    instead of asking the model to invent an image.
    """
    if not is_rag_visual_context_enabled(board, grade):
        return []

    query = " ".join([
        str(chapter or ""),
        str(step_title or ""),
        str(lesson_context or "")[:2500],
    ])

    visuals = search_visual_assets_for_context(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        query=query,
        limit=limit,
    )

    if visuals:
        return visuals

    return list_active_visual_assets_for_context(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        limit=limit,
    )


def update_visual_asset(visual_id: str, data: dict) -> dict | None:
    allowed = {
        key: value
        for key, value in data.items()
        if key in {"caption", "status", "nearby_text"}
    }

    if "status" in allowed and allowed["status"] not in {
        "active",
        "hidden",
        "needs_review",
    }:
        raise HTTPException(status_code=400, detail="Invalid visual status.")

    response = (
        admin_client
        .table("rag_visual_assets")
        .update(allowed)
        .eq("id", visual_id)
        .execute()
    )

    return response.data[0] if response.data else None


def backfill_visual_assets_for_document(
    *,
    document_id: str,
    file_bytes: bytes,
    filename: str,
    uploaded_by: str | None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> dict:
    """Render PDF pages to Supabase Storage and link them to one RAG document."""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload the source PDF for visual extraction.")

    document_row = _get_rag_document(document_id)
    board = normalize_board(document_row.get("board"))
    grade = document_row.get("grade") or ""

    if not is_rag_visual_context_enabled(board, grade):
        return {
            "success": True,
            "message": (
                "Textbook visual extraction is currently enabled only for "
                "CBSE Grade 9 and Grade 10 to protect storage quota."
            ),
            "document_id": document_row["id"],
            "page_count": 0,
            "visuals_created": 0,
            "visuals": [],
        }

    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Textbook visual extraction requires PyMuPDF. Install backend "
                "requirement PyMuPDF and redeploy."
            ),
        ) from exc

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    pdf_document = None
    try:
        pdf_document = fitz.open(tmp_path)
        page_count = pdf_document.page_count

        first_page = max(1, int(start_page or 1))
        last_page = min(page_count, int(end_page or page_count))

        if first_page > last_page:
            raise HTTPException(status_code=400, detail="Invalid page range.")

        pages_to_render = last_page - first_page + 1
        if pages_to_render > MAX_VISUAL_PAGES_PER_BACKFILL:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Visual backfill is limited to {MAX_VISUAL_PAGES_PER_BACKFILL} "
                    "pages per run. Use a smaller page range."
                ),
            )

        _delete_existing_visual_rows(document_id, first_page, last_page)

        subject = document_row.get("subject") or ""
        chapter = document_row.get("chapter") or ""
        title = document_row.get("title") or ""
        storage_prefix = "/".join([
            _slug(board),
            _slug(grade),
            _slug(subject),
            str(document_row["id"]),
        ])

        rows = []

        for page_number in range(first_page, last_page + 1):
            page = pdf_document.load_page(page_number - 1)
            image_bytes = _render_pdf_page_to_jpeg(page)
            storage_path = f"{storage_prefix}/page-{page_number:04d}.jpg"

            try:
                admin_client.storage.from_(RAG_VISUAL_BUCKET).upload(
                    path=storage_path,
                    file=image_bytes,
                    file_options={
                        "content-type": "image/jpeg",
                        "upsert": "true",
                    },
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unable to upload textbook visual to Supabase Storage bucket "
                        f"'{RAG_VISUAL_BUCKET}'. Create this public bucket and try again. "
                        f"Original error: {str(exc)}"
                    ),
                ) from exc

            public_url = admin_client.storage.from_(RAG_VISUAL_BUCKET).get_public_url(
                storage_path,
            )
            page_text = (page.get_text("text") or "").strip()

            rows.append({
                "document_id": document_row["id"],
                "board": board,
                "grade": grade,
                "subject": subject,
                "chapter": chapter,
                "title": title,
                "page_number": page_number,
                "asset_url": public_url,
                "storage_path": storage_path,
                "caption": f"{chapter or title} - page {page_number}",
                # Store the FULL page text, not a truncated slice.
                # 1200 chars was found to silently cut off genuine figure
                # captions that appear partway through a page's extracted
                # text -- confirmed live for Grade 11 Biology's "Chemical
                # Coordination and Integration" chapter: kebo119.pdf page
                # 2's real caption "Figure 19.1 Location of endocrine
                # glands" sits at character ~1250 of the raw PDF text
                # (the multi-column NCERT layout interleaves the caption
                # into the middle of body text), so every one of this
                # chapter's 5 genuine figures was invisible to the
                # caption-detection regex in curate_textbook_visuals.py,
                # and all 14 pages were stuck at "needs_review" with 0
                # active images despite the PDF being genuinely
                # image-rich. A full NCERT page's extracted text is
                # rarely more than a few thousand characters, so storing
                # it in full costs negligible extra storage while fixing
                # this class of bug for every future backfill.
                "nearby_text": page_text,
                "status": "needs_review",
                "uploaded_by": uploaded_by,
            })

        inserted_rows = []
        if rows:
            insert_response = admin_client.table("rag_visual_assets").insert(rows).execute()
            inserted_rows = insert_response.data or rows

        return {
            "success": True,
            "message": f"Extracted {len(rows)} textbook visual page(s).",
            "document_id": document_row["id"],
            "page_count": page_count,
            "visuals_created": len(rows),
            "visuals": inserted_rows,
        }
    finally:
        if pdf_document is not None:
            pdf_document.close()
        Path(tmp_path).unlink(missing_ok=True)
