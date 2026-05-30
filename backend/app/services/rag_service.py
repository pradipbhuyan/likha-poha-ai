from app.services.supabase_client import supabase
from app.services.openai_service import client


ADMIN_USERS = ["admin", "pradip"]


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
    if username not in ADMIN_USERS:
        return {
            "success": False,
            "message": "Only admin/pradip can upload RAG content.",
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
    response = (
        supabase
        .table("rag_documents")
        .select("id, title, grade, subject, chapter, uploaded_by, source_type, created_at")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


def delete_rag_document(document_id: str):
    supabase.table("rag_chunks").delete().eq("document_id", document_id).execute()

    response = (
        supabase
        .table("rag_documents")
        .delete()
        .eq("id", document_id)
        .execute()
    )

    return response.data