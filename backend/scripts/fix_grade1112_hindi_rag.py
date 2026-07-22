#!/usr/bin/env python3
"""
Fix Grade 11 & 12 Hindi RAG content.
=====================================
Root cause fixed here:
  1. Book code typo: Aroh was coded "khah1"/"lhah1" (404s) instead of the
     real NCERT codes "khar1"/"lhar1" — Aroh (the main reader) was NEVER
     uploaded as a result.
  2. NCERT's Hindi PDFs for Grade 11/12 use a legacy non-Unicode font.
     Plain pdfplumber text extraction produces glyph-mapped mojibake, not
     real Devanagari — this corrupted every existing Grade 11/12 Hindi
     rag_chunks row (even the 3 Grade 12 Vitan docs that had a correct
     title). Fixed by rendering each page to an image and transcribing it
     with a vision model (bypasses the broken text layer entirely).
  3. Two of five "Hindi" docs (Grade 11, ids 275/276) were mislabeled with
     literary chapter names but actually contain unrelated "भारतीय कलाएँ"
     (Fine Arts) content served under the same khvt1 book code by NCERT —
     dropped, not real Hindi-literature chapters.

TOC (chapter number -> title/author) was read directly off the NCERT
ps.pdf front-matter pages for Aroh; Vitan Bhag-1 has no ps.pdf so its
titles were confirmed by decoding chunk content already in the DB plus
OCR of chapter-1 pages.

Usage:
    cd backend
    python3 scripts/fix_grade1112_hindi_rag.py --book khvt1 --dry-run
    python3 scripts/fix_grade1112_hindi_rag.py --book khvt1
    python3 scripts/fix_grade1112_hindi_rag.py --book lhvt1
    python3 scripts/fix_grade1112_hindi_rag.py --book khar1
    python3 scripts/fix_grade1112_hindi_rag.py --book lhar1
    python3 scripts/fix_grade1112_hindi_rag.py --cleanup-fine-arts   # delete docs 275, 276
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # PyMuPDF
from openai import OpenAI

from app.services.openai_service import get_effective_settings
from app.services.grade_db_router import get_content_db
from app.services.rag_service import create_embedding

NCERT_BASE = "https://ncert.nic.in/textbook/pdf"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ncert.nic.in/textbook.php",
}
BOARD = "CBSE"
UPLOADED_BY = "4f443815-66b3-49a3-a746-04cd34eb7abf"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
CACHE_DIR = Path(
    "/private/tmp/claude-501/-Users-pradipbhuyan-likha-poha-ai/"
    "faba8cd3-1c9e-44e5-9056-9a35860f5710/scratchpad/ncert_toc"
)
CACHE_DIR.mkdir(exist_ok=True, parents=True)

OCR_MODEL = "meta/llama-3.2-11b-vision-instruct"
OCR_PROMPT = (
    "Transcribe ALL the Hindi (Devanagari) text visible in this image exactly "
    "as written, in proper Unicode Devanagari script. Preserve paragraph "
    "breaks. Ignore page numbers, QR codes, and the faint 'not to be "
    "republished' watermark. Do not translate, summarize, or add commentary "
    "— output only the transcribed Hindi text. If the page has no readable "
    "Hindi text (e.g. a blank or purely decorative page), output nothing."
)

# ── Book catalogue ─────────────────────────────────────────────────────────
# chapters: ordered list of (file_num, chapter_title, author)
BOOKS = {
    "khar1": {  # Grade 11 Aroh Bhag-1 (16 ch: 8 prose + 8 poetry)
        "grade": "Grade 11", "subject": "Hindi",
        "chapters": [
            (1, "Namak Ka Daroga", "Premchand"),
            (2, "Miyan Nasiruddin", "Krishna Sobti"),
            (3, "Apu Ke Saath Dhai Saal", "Satyajit Ray"),
            (4, "Vidai Sambhashan", "Balmukund Gupt"),
            (5, "Galta Loha", "Shekhar Joshi"),
            (6, "Rajni", "Mannu Bhandari"),
            (7, "Jamun Ka Ped", "Krishan Chandar"),
            (8, "Bharat Mata", "Jawaharlal Nehru"),
            (9, "Hum Tau Ek Ek Kari Jaana", "Kabir"),
            (10, "Mere To Girdhar Gopal", "Meera"),
            (11, "Ghar Ki Yaad", "Bhawani Prasad Mishra"),
            (12, "Champa Kaale Kaale Achchar Nahi Cheenhti", "Trilochan"),
            (13, "Ghazal", "Dushyant Kumar"),
            (14, "Hey Bhookh Mat Machal", "Akka Mahadevi"),
            (15, "Sabse Khatarnak", "Avtar Singh Pash"),
            (16, "Aao Milkar Bachayen", "Nirmala Putul"),
        ],
    },
    "lhar1": {  # Grade 12 Aroh Bhag-2 (15 ch: 9 poetry + 6 prose)
        "grade": "Grade 12", "subject": "Hindi",
        "chapters": [
            (1, "Atmaparichay Ek Geet", "Harivansh Rai Bachchan"),
            (2, "Patang", "Alok Dhanwa"),
            (3, "Kavita Ke Bahane Baat Seedhi Thi Par", "Kunwar Narayan"),
            (4, "Camera Mein Band Apahij", "Raghuvir Sahay"),
            (5, "Usha", "Shamsher Bahadur Singh"),
            (6, "Baadal Raag", "Suryakant Tripathi Nirala"),
            (7, "Kavitavali Uttarkand Se", "Tulsidas"),
            (8, "Rubaiyan", "Firaq Gorakhpuri"),
            (9, "Chhota Mera Khet", "Umashankar Joshi"),
            (10, "Bhaktin", "Mahadevi Verma"),
            (11, "Bazaar Darshan", "Jainendra Kumar"),
            (12, "Kale Megha Pani De", "Dharamvir Bharati"),
            (13, "Pahalwan Ki Dholak", "Phanishwar Nath Renu"),
            (14, "Shirish Ke Phool", "Hazari Prasad Dwivedi"),
            (15, "Shram Vibhajan Aur Jati Pratha", "Baba Saheb Bhimrao Ambedkar"),
        ],
    },
    "khvt1": {  # Grade 11 Vitan Bhag-1 (only ch 1-3 are Hindi lit; 4-5 = unrelated Fine Arts, excluded)
        "grade": "Grade 11", "subject": "Hindi",
        "chapters": [
            (1, "Bharatiya Gayikaon Mein Bejod Lata Mangeshkar", "Kumar Gandharva (interview)"),
            (2, "Rajasthan Ki Rajat Boondein", "Anupam Mishra"),
            (3, "Alo-Aandhari", "Baby Halder"),
        ],
    },
    "lhvt1": {  # Grade 12 Vitan Bhag-2 (3 ch — the old 4th "Diary Ke Panne" is not in the current curriculum)
        "grade": "Grade 12", "subject": "Hindi",
        "chapters": [
            (1, "Silver Wedding", "Manohar Shyam Joshi"),
            (2, "Jooze", "Anand Yadav"),
            (3, "Ateet Mein Dab Paon", "Om Thanvi"),
        ],
    },
}


def download_pdf(book_code: str, file_num: int) -> Path | None:
    """Read a pre-downloaded PDF from CACHE_DIR.

    Downloading is intentionally NOT done from inside this process: importing
    the app's service modules (openai/supabase clients) breaks curl's SSL
    handshake for any subprocess spawned afterward in this same interpreter
    (reproducible, cause not fully isolated). Pre-fetch all PDFs with the
    sibling shell helper (see prefetch_pdfs()) before running this script.
    """
    path = CACHE_DIR / f"{book_code}{file_num:02d}.pdf"
    if path.exists() and path.stat().st_size > 100:
        return path
    print(f"    [warn] {path.name} not found in cache — run --prefetch first")
    return None


def get_nvidia_client() -> tuple[OpenAI, str]:
    s = get_effective_settings()
    key = s.get("nvidia_api_key")
    if not key:
        raise RuntimeError("No NVIDIA API key configured (get_effective_settings)")
    return OpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1", timeout=60.0), key


def ocr_page(client: OpenAI, png_bytes: bytes, retries: int = 3) -> str:
    b64 = base64.b64encode(png_bytes).decode()
    for attempt in range(retries):
        try:
            r = client.chat.completions.create(
                model=OCR_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }],
                max_tokens=1500,
                temperature=0.0,
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            wait = 3 * (attempt + 1)
            print(f"      [ocr retry {attempt+1}/{retries}] {e} -- waiting {wait}s")
            time.sleep(wait)
    return ""


def ocr_pdf_to_text(client: OpenAI, pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    page_texts = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=170)
        png_bytes = pix.tobytes("png")
        text = ocr_page(client, png_bytes)
        page_texts.append(text)
        print(f"      page {i+1}/{doc.page_count}: {len(text)} chars")
        time.sleep(0.3)
    doc.close()
    return "\n\n".join(t for t in page_texts if t)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    sentences = re.split(r"(?<=[।.!?])\s+", text)
    chunks, current, current_len = [], [], 0
    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > size and current:
            chunks.append(" ".join(current))
            tail = " ".join(current)
            current = [tail[-overlap:]] if overlap else []
            current_len = len(current[0]) if current else 0
        current.append(sentence)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return [c.strip() for c in chunks if len(c.strip()) > 20]


def upsert_chapter(db, grade: str, subject: str, chapter: str, author: str, chunks: list[str], dry_run: bool):
    existing = (
        db.table("rag_documents").select("id")
        .eq("grade", grade).eq("board", BOARD).eq("subject", subject).eq("chapter", chapter)
        .execute()
    )
    title = f"Hindi — {chapter}" + (f" ({author})" if author else "")
    if dry_run:
        action = "UPDATE" if existing.data else "INSERT"
        print(f"    [dry-run] would {action} doc chapter={chapter!r} with {len(chunks)} chunks")
        return

    if existing.data:
        doc_id = existing.data[0]["id"]
        db.table("rag_documents").update({"title": title}).eq("id", doc_id).execute()
    else:
        result = db.table("rag_documents").insert({
            "grade": grade, "board": BOARD, "subject": subject, "chapter": chapter,
            "title": title, "source_type": "pdf", "uploaded_by": UPLOADED_BY,
        }).execute()
        doc_id = result.data[0]["id"]

    db.table("rag_chunks").delete().eq("document_id", doc_id).execute()
    stored = 0
    for i, chunk in enumerate(chunks):
        try:
            embedding = create_embedding(chunk)
            db.table("rag_chunks").insert({
                "document_id": doc_id, "chunk_text": chunk, "chunk_index": i, "embedding": embedding,
            }).execute()
            stored += 1
        except Exception as e:
            print(f"      [embed error] chunk {i}: {e}")
    print(f"    doc_id={doc_id} chapter={chapter!r} -> {stored}/{len(chunks)} chunks stored")


def process_book(book_code: str, dry_run: bool, only_chapters: list[int] | None):
    spec = BOOKS[book_code]
    grade, subject = spec["grade"], spec["subject"]
    db = get_content_db(grade)
    client, _ = get_nvidia_client()

    print(f"\n{'='*70}\n  {book_code}  ({grade} / {subject})  {len(spec['chapters'])} chapters\n{'='*70}")

    for file_num, chapter, author in spec["chapters"]:
        if only_chapters and file_num not in only_chapters:
            continue
        print(f"\n  -- Chapter {file_num}: {chapter} ({author}) --")
        pdf_path = download_pdf(book_code, file_num)
        if not pdf_path:
            print(f"    [skip] could not download {book_code}{file_num:02d}.pdf")
            continue
        text = ocr_pdf_to_text(client, pdf_path)
        if len(text) < 50:
            print(f"    [warn] extracted text suspiciously short ({len(text)} chars) — skipping upsert")
            continue
        chunks = chunk_text(text)
        print(f"    extracted {len(text)} chars -> {len(chunks)} chunks")
        upsert_chapter(db, grade, subject, chapter, author, chunks, dry_run)


def cleanup_fine_arts(dry_run: bool):
    """Delete the 2 mislabeled Grade 11 Hindi docs that are actually unrelated Fine Arts content."""
    db = get_content_db("Grade 11")
    bad_titles = ["Mera Baap Bada Na Mera Chacha", "Anubhav"]
    for chapter in bad_titles:
        existing = (
            db.table("rag_documents").select("id")
            .eq("grade", "Grade 11").eq("subject", "Hindi").eq("chapter", chapter)
            .execute()
        )
        if not existing.data:
            print(f"  [skip] no doc found for chapter={chapter!r}")
            continue
        doc_id = existing.data[0]["id"]
        if dry_run:
            print(f"  [dry-run] would delete doc_id={doc_id} chapter={chapter!r}")
            continue
        db.table("rag_chunks").delete().eq("document_id", doc_id).execute()
        db.table("rag_documents").delete().eq("id", doc_id).execute()
        print(f"  deleted doc_id={doc_id} chapter={chapter!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", choices=list(BOOKS.keys()))
    parser.add_argument("--chapters", nargs="+", type=int, help="only process these file numbers")
    parser.add_argument("--cleanup-fine-arts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.cleanup_fine_arts:
        cleanup_fine_arts(args.dry_run)
        return

    if not args.book:
        parser.error("--book is required (or use --cleanup-fine-arts)")

    process_book(args.book, args.dry_run, args.chapters)


if __name__ == "__main__":
    main()
