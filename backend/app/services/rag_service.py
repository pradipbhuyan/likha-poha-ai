from app.services.openai_service import get_openai_client
from app.services.board_service import normalize_board
from app.services.grade_db_router import get_content_db
import re


# Embedding model used for both indexing and querying.
# Must be the same model for all stored chunks — changing this requires
# deleting all rag_chunks rows and re-uploading every RAG document.
EMBEDDING_MODEL = "text-embedding-3-small"

ADMIN_USERS = {"admin", "pradip", "pradip admin"}


def is_admin_upload_user(username) -> bool:
    normalized_username = str(username or "").strip().lower()
    return normalized_username in ADMIN_USERS


def split_text_into_chunks(text, chunk_size=1200):
    words = text.split()
    chunks = []
    current = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= chunk_size:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def create_embedding(text: str):
    response = get_openai_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def strip_chapter_display_prefix(chapter):
    return re.sub(
        r"^\s*part\s*\d+\s*[-:]\s*",
        "",
        str(chapter or ""),
        flags=re.IGNORECASE,
    ).strip()


def upload_textbook_text(
    username,
    grade,
    subject,
    chapter,
    title,
    text,
    board="CBSE",
    progress_callback=None,
):
    """
    Store one RAG document, split its text, and persist embeddings for search.
    Routes to the Grade 11/12 Supabase project when grade is 11 or 12.
    """
    if not is_admin_upload_user(username):
        return {
            "success": False,
            "message": "Only an admin user can upload RAG content.",
            "document_id": None,
            "chunks_created": 0,
        }

    db = get_content_db(grade)

    document_row = {
        "uploaded_by": username,
        "board": normalize_board(board),
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "title": title,
        "source_type": "text",
    }

    try:
        doc_response = db.table("rag_documents").insert(document_row).execute()
    except Exception as exc:
        if "board" not in str(exc).lower():
            raise
        legacy_row = dict(document_row)
        legacy_row.pop("board", None)
        doc_response = db.table("rag_documents").insert(legacy_row).execute()

    if not doc_response.data:
        return {
            "success": False,
            "message": "Could not create RAG document.",
            "document_id": None,
            "chunks_created": 0,
        }

    document_id = doc_response.data[0]["id"]
    chunks = split_text_into_chunks(text)

    if progress_callback:
        progress_callback(
            processed_chunks=0,
            total_chunks=len(chunks),
            message=f"Creating embeddings for {len(chunks)} chunks.",
        )

    rows = []
    for index, chunk in enumerate(chunks):
        embedding = create_embedding(chunk)
        rows.append({
            "document_id": document_id,
            "chunk_text": chunk,
            "chunk_index": index,
            "embedding": embedding,
        })
        if progress_callback:
            progress_callback(
                processed_chunks=index + 1,
                total_chunks=len(chunks),
                message=f"Embedded chunk {index + 1} of {len(chunks)}.",
            )

    if rows:
        db.table("rag_chunks").insert(rows).execute()

    return {
        "success": True,
        "message": "Text uploaded, chunked, and embedded successfully.",
        "document_id": document_id,
        "chunks_created": len(rows),
    }


def search_textbook_content(
    query,
    board=None,
    grade=None,
    subject=None,
    chapter=None,
    match_count=5,
):
    """
    Search uploaded RAG chunks using vector similarity and optional metadata.
    Automatically targets the correct Supabase project based on grade.

    Returns [] on any DB error (e.g. Grade 11/12 Supabase key rotation) so
    the AI tutor falls back to LLM-only generation rather than crashing.
    """
    db = get_content_db(grade)
    try:
        query_embedding = create_embedding(query)
    except Exception:
        return []

    requested_board = normalize_board(board)
    rpc_match_count = match_count * 4 if board else match_count

    try:
        response = db.rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": rpc_match_count,
                "filter_grade": grade,
                "filter_subject": subject,
                "filter_chapter": strip_chapter_display_prefix(chapter) if chapter else chapter,
            },
        ).execute()
        results = response.data or []
    except Exception:
        # DB unavailable (e.g. Grade 11/12 key rotation) — return empty so
        # the tutor falls back to LLM generation rather than crashing.
        return []

    for item in results:
        doc_id = item.get("document_id")
        if doc_id:
            try:
                doc_response = (
                    db.table("rag_documents")
                    .select("title, board, subject, chapter, grade")
                    .eq("id", doc_id)
                    .execute()
                )
            except Exception as exc:
                if "board" not in str(exc).lower():
                    raise
                doc_response = (
                    db.table("rag_documents")
                    .select("title, subject, chapter, grade")
                    .eq("id", doc_id)
                    .execute()
                )

            if doc_response.data:
                document = doc_response.data[0]
                item["document"] = document
                document_board = normalize_board(document.get("board"))
                if board and document_board != requested_board:
                    item["_board_mismatch"] = True

    filtered_results = [r for r in results if not r.get("_board_mismatch")]
    return filtered_results[:match_count]


def list_rag_documents(grade: str | None = None):
    """
    Return uploaded RAG document metadata in newest-first order.

    When grade is None, returns documents from BOTH the primary and Grade 11/12
    databases so the admin panel shows all uploaded content at once.
    When grade is 'Grade 11' or 'Grade 12', returns only from that database.
    """
    def _fetch(db):
        try:
            r = (
                db.table("rag_documents")
                .select("id, title, board, grade, subject, chapter, uploaded_by, source_type, created_at")
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            if "board" not in str(exc).lower():
                raise
            r = (
                db.table("rag_documents")
                .select("id, title, grade, subject, chapter, uploaded_by, source_type, created_at")
                .order("created_at", desc=True)
                .execute()
            )
        return r.data or []

    if grade is not None:
        return _fetch(get_content_db(grade))

    # No grade filter — merge both databases for the admin overview
    from app.services.auth_service import admin_client
    primary_docs = _fetch(admin_client)

    # Grade 11/12 DB may be unavailable during key rotation — import safely
    grade_1112_docs: list = []
    try:
        from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
        grade_1112_docs = _fetch(grade_1112_client)
    except (SystemExit, Exception):
        pass  # Grade 11/12 temporarily unavailable — show primary docs only

    # Combine and sort by created_at descending
    all_docs = primary_docs + grade_1112_docs
    all_docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return all_docs


def get_rag_document_preview(document_id: str, limit: int = 2, grade: str | None = None):
    """Return the first few stored chunks so admins can validate document content."""
    db = get_content_db(grade)
    response = (
        db.table("rag_chunks")
        .select("chunk_text, chunk_index")
        .eq("document_id", document_id)
        .order("chunk_index")
        .limit(limit)
        .execute()
    )
    return response.data or []


def delete_rag_document(document_id: str, grade: str | None = None):
    """
    Delete a RAG document and its chunks.
    Pass grade='Grade 11' or 'Grade 12' to delete from the second database.
    """
    db = get_content_db(grade)
    db.table("rag_chunks").delete().eq("document_id", document_id).execute()
    response = db.table("rag_documents").delete().eq("id", document_id).execute()
    return response.data
