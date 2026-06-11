from app.services.supabase_client import supabase
from app.services.openai_service import client
from app.services.board_service import normalize_board
import re


# Embedding model used for both indexing and querying.
# Must be the same model for all stored chunks — changing this requires
# deleting all rag_chunks rows and re-uploading every RAG document.
EMBEDDING_MODEL = "text-embedding-ada-002"

ADMIN_USERS = {"admin", "pradip", "pradip admin"}


def is_admin_upload_user(username) -> bool:
    """
    Check whether a RAG upload request came from a trusted admin identity.

    The frontend may pass the profile display name, such as "Pradip Admin",
    rather than the short username "admin", so comparison is normalized.
    """
    normalized_username = str(username or "").strip().lower()

    return normalized_username in ADMIN_USERS


def split_text_into_chunks(text, chunk_size=1200):
    """
    Split uploaded textbook text into embedding-sized word chunks.

    Chunking by approximate character length keeps retrieved context small
    enough for prompts while preserving paragraph-like continuity.
    """
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
    """Create a vector embedding for text using the configured OpenAI client."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def strip_chapter_display_prefix(chapter):
    """Remove display-only book part prefixes before querying RAG metadata."""
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

    Only trusted admin upload usernames are accepted here because inserted RAG
    content directly influences student answers and SOF mock-test generation.
    """
    if not is_admin_upload_user(username):
        return {
            "success": False,
            "message": "Only an admin user can upload RAG content.",
            "document_id": None,
            "chunks_created": 0,
        }

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
        doc_response = (
            supabase
            .table("rag_documents")
            .insert(document_row)
            .execute()
        )
    except Exception as exc:
        if "board" not in str(exc).lower():
            raise

        # Rollout compatibility: allow old databases to keep accepting uploads
        # until the add_board_support.sql migration has been applied.
        legacy_row = dict(document_row)
        legacy_row.pop("board", None)
        doc_response = (
            supabase
            .table("rag_documents")
            .insert(legacy_row)
            .execute()
        )

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
        # Embeddings are stored beside each chunk so the Supabase RPC can run
        # vector similarity search without calling OpenAI at query time.
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
        supabase.table("rag_chunks").insert(rows).execute()

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

    The document metadata lookup enriches each matching chunk with title,
    subject, chapter, and grade so UI/source attribution can be shown.
    """
    query_embedding = create_embedding(query)

    requested_board = normalize_board(board)
    rpc_match_count = match_count * 4 if board else match_count
    response = (
        supabase
        .rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": rpc_match_count,
                "filter_grade": grade,
                "filter_subject": subject,
                "filter_chapter": strip_chapter_display_prefix(chapter) if chapter else chapter,
            },
        )
        .execute()
    )

    results = response.data or []

    for item in results:
        doc_id = item.get("document_id")

        if doc_id:
            try:
                doc_response = (
                    supabase
                    .table("rag_documents")
                    .select("title, board, subject, chapter, grade")
                    .eq("id", doc_id)
                    .execute()
                )
            except Exception as exc:
                if "board" not in str(exc).lower():
                    raise

                doc_response = (
                    supabase
                    .table("rag_documents")
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

    filtered_results = [
        item for item in results
        if not item.get("_board_mismatch")
    ]

    return filtered_results[:match_count]

def list_rag_documents():
    """Return uploaded RAG document metadata in newest-first order."""
    try:
        response = (
            supabase
            .table("rag_documents")
            .select("id, title, board, grade, subject, chapter, uploaded_by, source_type, created_at")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        if "board" not in str(exc).lower():
            raise

        response = (
            supabase
            .table("rag_documents")
            .select("id, title, grade, subject, chapter, uploaded_by, source_type, created_at")
            .order("created_at", desc=True)
            .execute()
        )

    return response.data or []


def get_rag_document_preview(document_id: str, limit: int = 2):
    """Return the first few stored chunks so admins can validate document content."""
    response = (
        supabase
        .table("rag_chunks")
        .select("chunk_text, chunk_index")
        .eq("document_id", document_id)
        .order("chunk_index")
        .limit(limit)
        .execute()
    )

    return response.data or []


def delete_rag_document(document_id: str):
    """
    Delete a RAG document and its chunks.

    Chunks are removed first to avoid orphaned vector rows if cascading deletes
    are not configured in the database.
    """
    supabase.table("rag_chunks").delete().eq("document_id", document_id).execute()

    response = (
        supabase
        .table("rag_documents")
        .delete()
        .eq("id", document_id)
        .execute()
    )

    return response.data
