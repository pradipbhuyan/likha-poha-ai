#!/usr/bin/env python3
"""
Upload Advanced Grade 9 Maths & Science PDFs as RAG documents.

PDFs:
  - Maths: /Users/a0247716/Downloads/6a2befcd02ffe-1781264333.pdf
  - Science: /Users/a0247716/Downloads/6a2befcd0e0d4-1781264333.pdf

Creates rag_documents + rag_chunks with embeddings for each chapter.
Run: cd backend && python3 scripts/upload_advanced_grade9_rag.py
"""

import sys, os, re, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber
from app.services.auth_service import admin_client as supabase
from app.services.rag_service import create_embedding

GRADE = "Grade 9"
BOARD = "CBSE"
CHUNK_SIZE = 400       # characters per chunk (overlap handled below)
CHUNK_OVERLAP = 50

# -----------------------------------------------------------------------
# Chapter → page ranges in each PDF  (0-indexed pages)
# -----------------------------------------------------------------------

MATHS_PDF = "/Users/a0247716/Downloads/6a2befcd02ffe-1781264333.pdf"
MATHS_CHAPTERS = [
    # (chapter_name, start_page_0indexed, end_page_0indexed_inclusive)
    ("Advanced - Sets",                              2,  20),
    ("Advanced - Logarithms",                        21, 36),
    ("Advanced - Relations and Functions",           37, 53),
    ("Advanced - Coordinate Geometry",              54, 69),
    ("Advanced - Combinatorics",                     70, 82),
    ("Advanced - Exploring some more Progressions", 83, 93),
]
MATHS_SUBJECT = "Advanced Mathematics"

SCIENCE_PDF = "/Users/a0247716/Downloads/6a2befcd0e0d4-1781264333.pdf"
SCIENCE_CHAPTERS = [
    ("Advanced - Measurement: Foundation of Science",                  3,  8),
    ("Advanced - Understanding Motion through Experience",              9, 14),
    ("Advanced - Newton's Laws of Motion",                            15, 24),
    ("Advanced - The Geometry of Power: Advanced Simple Machines",    25, 29),
    ("Advanced - Work and Energy",                                     30, 33),
    ("Advanced - Structure of Atom",                                   34, 41),
    ("Advanced - Chemical Bonding",                                    42, 48),
    ("Advanced - Mixtures and their Separation",                       49, 53),
    ("Advanced - Microscope and Microscopy",                           54, 68),
    ("Advanced - Engineering Life: Miracles in Biotechnology",        69, 85),
]
SCIENCE_SUBJECT = "Advanced Science"


def extract_text_pages(pdf_path: str, start: int, end: int) -> str:
    """Extract and clean text from page range (0-indexed)."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for i in range(start, min(end + 1, len(pdf.pages))):
            text = pdf.pages[i].extract_text() or ""
            # Clean headers/footers (page numbers, chapter titles repeated)
            text = re.sub(r"\bPage\s*\|\s*\d+\b", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\n{3,}", "\n\n", text)
            pages.append(text.strip())
    return "\n\n".join(p for p in pages if p)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping chunks by sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > size and current:
            chunks.append(" ".join(current))
            # Keep last few sentences for overlap
            overlap_text = " ".join(current)
            current = [overlap_text[-overlap:]] if overlap else []
            current_len = len(current[0]) if current else 0
        current.append(sentence)
        current_len += s_len

    if current:
        chunks.append(" ".join(current))

    return [c.strip() for c in chunks if len(c.strip()) > 30]


def create_rag_document(subject: str, chapter: str) -> str:
    """Create a rag_documents record and return its ID."""
    # Check if already exists
    existing = (
        supabase.table("rag_documents")
        .select("id")
        .eq("grade", GRADE)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .execute()
    )
    if existing.data:
        doc_id = existing.data[0]["id"]
        print(f"  [exists] doc_id={str(doc_id)[:8]}")
        return doc_id

    result = supabase.table("rag_documents").insert({
        "grade": GRADE,
        "board": BOARD,
        "subject": subject,
        "chapter": chapter,
        "title": f"{chapter} — Grade 9 Advanced",
        "source_type": "pdf",
        "uploaded_by": "4f443815-66b3-49a3-a746-04cd34eb7abf",  # Pradip Admin
    }).execute()

    doc_id = result.data[0]["id"]
    print(f"  [created] doc_id={str(doc_id)[:8]}")
    return doc_id


def upload_chunks(doc_id: str, chunks: list[str], chapter: str):
    """Embed each chunk and store in rag_chunks."""
    # Remove existing chunks for this document
    supabase.table("rag_chunks").delete().eq("document_id", doc_id).execute()

    stored = 0
    for i, chunk in enumerate(chunks):
        try:
            embedding = create_embedding(chunk)
            supabase.table("rag_chunks").insert({
                "document_id": doc_id,
                "chunk_text": chunk,
                "chunk_index": i,
                "embedding": embedding,
            }).execute()
            stored += 1
            time.sleep(0.1)   # rate limit embeddings
        except Exception as e:
            print(f"    chunk {i} FAILED: {e}")

    return stored


def process_pdf(pdf_path: str, subject: str, chapters: list):
    """Process one PDF: all chapters → RAG documents + chunks."""
    print(f"\n{'='*60}")
    print(f"Processing: {subject}")
    print(f"PDF: {os.path.basename(pdf_path)}")
    print(f"{'='*60}")

    for (chapter, start, end) in chapters:
        print(f"\n► {chapter} (pages {start+1}–{end+1})")

        # Extract text
        text = extract_text_pages(pdf_path, start, end)
        if not text:
            print("  WARNING: no text extracted — skipping")
            continue
        print(f"  Extracted {len(text):,} chars")

        # Chunk
        chunks = chunk_text(text)
        print(f"  Chunked into {len(chunks)} pieces")

        # Create/get document record
        doc_id = create_rag_document(subject, chapter)

        # Upload chunks with embeddings
        stored = upload_chunks(doc_id, chunks, chapter)
        print(f"  Stored {stored}/{len(chunks)} chunks with embeddings")


if __name__ == "__main__":
    print("Grade 9 Advanced RAG Upload")
    print(f"Target: {GRADE} / {BOARD}")
    print()

    process_pdf(MATHS_PDF, MATHS_SUBJECT, MATHS_CHAPTERS)
    process_pdf(SCIENCE_PDF, SCIENCE_SUBJECT, SCIENCE_CHAPTERS)

    # Verify
    print("\n\n=== VERIFICATION ===")
    for subject in [MATHS_SUBJECT, SCIENCE_SUBJECT]:
        r = supabase.table("rag_documents").select("chapter").eq("grade", GRADE).eq("subject", subject).execute()
        c = supabase.table("rag_chunks").select("id", count="exact").execute()
        docs = r.data or []
        print(f"\n{subject}: {len(docs)} chapters uploaded")
        for d in docs:
            print(f"  ✅ {d['chapter']}")

    print("\nDone! Run prewarm to generate lessons for the new chapters.")
