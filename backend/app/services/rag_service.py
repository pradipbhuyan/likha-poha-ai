from app.services.supabase_client import supabase
from app.services.openai_service import client


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
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding


def upload_textbook_text(
    username,
    grade,
    subject,
    chapter,
    title,
    text,
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

    doc_response = (
        supabase
        .table("rag_documents")
        .insert({
            "uploaded_by": username,
            "grade": grade,
            "subject": subject,
            "chapter": chapter,
            "title": title,
            "source_type": "text",
        })
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

    response = (
        supabase
        .rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_grade": grade,
                "filter_subject": subject,
                "filter_chapter": chapter,
            },
        )
        .execute()
    )

    results = response.data or []

    for item in results:
        doc_id = item.get("document_id")

        if doc_id:
            doc_response = (
                supabase
                .table("rag_documents")
                .select("title, subject, chapter, grade")
                .eq("id", doc_id)
                .execute()
            )

            if doc_response.data:
                item["document"] = doc_response.data[0]

    return results

def list_rag_documents():
    """Return uploaded RAG document metadata in newest-first order."""
    response = (
        supabase
        .table("rag_documents")
        .select("id, title, grade, subject, chapter, uploaded_by, source_type, created_at")
        .order("created_at", desc=True)
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
