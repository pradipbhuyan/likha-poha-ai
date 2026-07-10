#!/usr/bin/env python3
"""
Chunk Quality Auditor — RAG Vector DB Chunk QA Tool
=====================================================
Audits the quality of RAG chunks stored in the vector DB by comparing each
stored chunk against its original source (PDF or reconstructed document text).

Evaluates three dimensions for every chunk:
  - Fidelity      : how closely the stored chunk matches the re-extracted source
  - Completeness  : whether the chunk contains full sentences / formulas
  - Boundary      : whether the chunk starts/ends at logical text breaks

Flags low-scoring chunks for review and optionally runs a lightweight LLM
analysis on them to surface semantic errors.

READ-ONLY: This script makes NO changes to any database.

Usage:
    cd backend
    python3 scripts/audit_chunk_quality.py
    python3 scripts/audit_chunk_quality.py --grade 9 --subject Maths
    python3 scripts/audit_chunk_quality.py --document-id <uuid>
    python3 scripts/audit_chunk_quality.py --pdf-dir "../RAG DB"
    python3 scripts/audit_chunk_quality.py --sample 20
    python3 scripts/audit_chunk_quality.py --use-llm --llm-threshold 55
    python3 scripts/audit_chunk_quality.py --grade 9 --output reports/my_run

Modes:
    (no flags)           All documents, deterministic only (fast)
    --sample N           Audit N randomly sampled documents
    --grade G            Filter by grade, e.g. --grade 9 or "Grade 9"
    --subject S          Filter by subject, e.g. --subject Maths
    --document-id UUID   Audit one specific document
    --pdf-dir PATH       Path to folder with source PDFs (enables fidelity check)
    --use-llm            Enable LLM review of low-scoring chunks (cached)
    --llm-threshold N    Score threshold for LLM review (default 60)
    --output DIR         Output directory (default: reports/chunk_quality/)
    --fail-below N       Exit 1 when avg overall score < N (CI gate)
    --verbose            Print per-chunk details to stdout

Output:
    reports/chunk_quality/chunk_quality_report.json
    reports/chunk_quality/chunk_quality_report.md
    reports/chunk_quality/chunk_quality_summary.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import logging
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db, is_grade_1112  # noqa: E402
from app.services.auth_service import admin_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger("audit_chunk_quality")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 1200           # mirrors rag_service.split_text_into_chunks
MIN_CHUNK_WORDS = 5
MIN_CHUNK_CHARS = 30
LLM_REVIEW_THRESHOLD_DEFAULT = 60
LLM_CACHE_FILE = Path("reports/chunk_quality/.llm_cache.json")

_LATEX_UNCLOSED_RE = re.compile(r"\$[^$]*$|\\\([^\)]*$|\\\[[^\]]*$")
_OPEN_BRACKET_RE = re.compile(r"[\(\[\{]")
_CLOSE_BRACKET_RE = re.compile(r"[\)\]\}]")
_TRUNCATED_URL_RE = re.compile(r"https?://\S+$")
_WORD_RE = re.compile(r"\b\w+\b")
_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_END_RE = re.compile(r"[.!?;:\u0964]\s*$")
_SENTENCE_START_RE = re.compile(r"^[\(\[\"'\u2018\u201CA-Z\u0900-\u097F\d]")

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "").strip()).lower()


def _word_freq(text: str) -> collections.Counter:
    return collections.Counter(_WORD_RE.findall(normalize_text(text)))


# ---------------------------------------------------------------------------
# Similarity metrics
# ---------------------------------------------------------------------------

def cosine_similarity(text_a: str, text_b: str) -> float:
    """Word-frequency cosine similarity. No external ML dependencies."""
    fa, fb = _word_freq(text_a), _word_freq(text_b)
    if not fa or not fb:
        return 0.0
    vocab = set(fa) | set(fb)
    va = [fa.get(w, 0) for w in vocab]
    vb = [fb.get(w, 0) for w in vocab]
    dot = sum(a * b for a, b in zip(va, vb))
    mag_a = math.sqrt(sum(a * a for a in va))
    mag_b = math.sqrt(sum(b * b for b in vb))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-set Jaccard overlap."""
    wa = set(_WORD_RE.findall(normalize_text(text_a)))
    wb = set(_WORD_RE.findall(normalize_text(text_b)))
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


# ---------------------------------------------------------------------------
# Chunking  (must stay in sync with rag_service.split_text_into_chunks)
# ---------------------------------------------------------------------------

def split_text_into_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= chunk_size:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def _extract_via_pypdf(pdf_path: Path) -> tuple[list[str], str]:
    try:
        from pypdf import PdfReader  # noqa: PLC0415
        reader = PdfReader(str(pdf_path))
        return [p.extract_text() or "" for p in reader.pages], "pypdf"
    except Exception as exc:
        _log.debug("pypdf failed for %s: %s", pdf_path.name, exc)
        return [], ""


def _extract_via_pymupdf(pdf_path: Path) -> tuple[list[str], str]:
    try:
        import fitz  # noqa: PLC0415
        doc = fitz.open(str(pdf_path))
        pages = [doc.load_page(i).get_text("text") or "" for i in range(doc.page_count)]
        doc.close()
        return pages, "pymupdf"
    except Exception as exc:
        _log.debug("PyMuPDF failed for %s: %s", pdf_path.name, exc)
        return [], ""


def extract_pdf_pages(pdf_path: Path) -> tuple[list[str], str]:
    pages, method = _extract_via_pypdf(pdf_path)
    total_words = sum(len(p.split()) for p in pages)
    if total_words < 50:
        fb_pages, fb_method = _extract_via_pymupdf(pdf_path)
        fb_words = sum(len(p.split()) for p in fb_pages)
        if fb_words > total_words:
            return fb_pages, fb_method
    return pages, method


def extract_pdf_full_text(pdf_path: Path) -> tuple[str, str]:
    pages, method = extract_pdf_pages(pdf_path)
    return "\n\n".join(p.strip() for p in pages if p.strip()), method


def segment_into_paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text)
    segments: list[str] = []
    for seg in raw:
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) > 3000:
            sub = re.split(
                r"\n(?=[A-Z][A-Z\s]{3,}$|\d+\.\s+[A-Z])",
                seg,
                flags=re.MULTILINE,
            )
            segments.extend(s.strip() for s in sub if s.strip())
        else:
            segments.append(seg)
    return segments


# ---------------------------------------------------------------------------
# PDF index / source-PDF lookup
# ---------------------------------------------------------------------------

def build_pdf_index(pdf_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for p in pdf_dir.rglob("*.pdf"):
        index[p.stem.lower()] = p
    _log.info("PDF index built: %d files under %s", len(index), pdf_dir)
    return index


def find_source_pdf(doc: dict, pdf_index: dict[str, Path], pdf_dir: Path) -> Path | None:
    """
    Heuristically locate the source PDF for a rag_document row.
    Tries grade/subject sub-folder, then title-word match, then broad chapter match.
    """
    grade = (doc.get("grade") or "").lower().replace(" ", "_")
    subject = (doc.get("subject") or "").lower()
    chapter = (doc.get("chapter") or "").lower()
    title = (doc.get("title") or "").lower()

    ch_words = [w for w in re.split(r"\W+", chapter) if len(w) >= 4]
    title_words = [w for w in re.split(r"\W+", title) if len(w) >= 4]
    grade_num = re.sub(r"\D", "", grade)

    candidate_dirs = [
        d for d in pdf_dir.rglob("*")
        if d.is_dir() and grade_num and grade_num in d.name.lower()
    ]
    subject_dirs = [
        d for d in candidate_dirs
        if any(part in d.name.lower() for part in subject.split())
    ]
    search_dirs = subject_dirs or candidate_dirs or [pdf_dir]

    if ch_words:
        for search_dir in search_dirs:
            for pdf_path in search_dir.rglob("*.pdf"):
                path_lower = str(pdf_path).lower()
                stem_lower = pdf_path.stem.lower()
                if all(w in path_lower or w in stem_lower for w in ch_words[:2]):
                    return pdf_path

    if title_words:
        for stem, path in pdf_index.items():
            if all(w in stem for w in title_words[:2]):
                return path

    if ch_words:
        for stem, path in pdf_index.items():
            path_lower = str(path).lower()
            if all(w in path_lower for w in ch_words[:2]):
                return path

    return None


# ---------------------------------------------------------------------------
# Finding class
# ---------------------------------------------------------------------------

class Finding:
    __slots__ = ("severity", "category", "message", "detail")

    def __init__(self, severity: str, category: str, message: str, detail: str = ""):
        self.severity = severity
        self.category = category
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "detail": self.detail[:200] if self.detail else "",
        }


# ---------------------------------------------------------------------------
# Completeness checks
# ---------------------------------------------------------------------------

def check_completeness(chunk_text: str, chunk_index: int) -> list[Finding]:
    """
    Detect incomplete or truncated content.
    Checks: min size, unclosed LaTeX, unbalanced brackets, truncated URLs,
    ends mid-word.
    """
    findings: list[Finding] = []
    text = (chunk_text or "").strip()
    label = f"Chunk #{chunk_index}"

    if not text:
        findings.append(Finding("critical", "completeness", f"{label} is empty."))
        return findings

    if len(text) < MIN_CHUNK_CHARS:
        findings.append(Finding(
            "critical", "completeness",
            f"{label} is extremely short ({len(text)} chars) — likely a fragment.",
            text,
        ))
        return findings

    word_count = len(text.split())
    if word_count < MIN_CHUNK_WORDS:
        findings.append(Finding(
            "high", "completeness",
            f"{label} has only {word_count} words — likely a fragment.",
            text[:80],
        ))

    # Unclosed LaTeX
    if _LATEX_UNCLOSED_RE.search(text):
        findings.append(Finding(
            "high", "completeness",
            f"{label} contains an unclosed LaTeX expression.",
            text[-100:],
        ))

    # Unbalanced brackets
    opens = len(_OPEN_BRACKET_RE.findall(text))
    closes = len(_CLOSE_BRACKET_RE.findall(text))
    if opens != closes:
        findings.append(Finding(
            "medium", "completeness",
            f"{label} has unbalanced brackets (opens={opens}, closes={closes}).",
            text[-100:],
        ))

    # Truncated URL
    if _TRUNCATED_URL_RE.search(text):
        findings.append(Finding(
            "low", "completeness",
            f"{label} ends with a potentially truncated URL.",
            text[-80:],
        ))

    # Ends mid-word (hyphen at end = truncation)
    if text.endswith("-"):
        findings.append(Finding(
            "high", "completeness",
            f"{label} ends with a hyphen — likely a mid-word split.",
            text[-80:],
        ))

    return findings


# ---------------------------------------------------------------------------
# Boundary checks
# ---------------------------------------------------------------------------

def check_boundaries(chunk_text: str, chunk_index: int, is_first: bool, is_last: bool) -> list[Finding]:
    """
    Evaluate whether the chunk starts and ends at logical text boundaries.

    Checks:
      - Starts with a capital letter, digit, or opening bracket (not mid-sentence)
      - Ends with sentence-ending punctuation (not mid-sentence)
      - Not-first chunks that start mid-sentence (lower-case continuation word)
      - Not-last chunks that end without punctuation
    """
    findings: list[Finding] = []
    text = (chunk_text or "").strip()
    label = f"Chunk #{chunk_index}"

    if not text:
        return findings

    # Check start boundary (skip first chunk — can start anywhere)
    if not is_first:
        first_char = text[0] if text else ""
        if first_char.islower():
            findings.append(Finding(
                "medium", "boundary",
                f"{label} starts with a lower-case character — may begin mid-sentence.",
                text[:80],
            ))

    # Check end boundary (skip last chunk — may end anywhere)
    if not is_last:
        if not _SENTENCE_END_RE.search(text):
            findings.append(Finding(
                "medium", "boundary",
                f"{label} does not end with sentence-ending punctuation — may cut mid-sentence.",
                text[-80:],
            ))

    return findings


# ---------------------------------------------------------------------------
# Fidelity check (idempotency: re-chunk stored text, compare at same index)
# ---------------------------------------------------------------------------

def check_fidelity_idempotency(
    stored_chunks: list[str],
    chunk_index: int,
) -> tuple[float, float, list[Finding]]:
    """
    Re-chunk the concatenation of all stored chunks and compare chunk at
    chunk_index to the stored value.

    Returns (cosine_score, jaccard_score, findings).

    This is the idempotency test: if the original text was properly extracted
    and chunked, re-chunking the stored text should reproduce the same chunks.
    Significant drift means the stored text diverged from what a fresh
    extraction would produce.
    """
    if not stored_chunks:
        return 0.0, 0.0, [Finding("critical", "fidelity", "No stored chunks to compare.")]

    # Reconstruct the document text from stored chunks
    full_text = " ".join(chunk.strip() for chunk in stored_chunks)
    rechunked = split_text_into_chunks(full_text)

    if chunk_index >= len(rechunked):
        return 0.0, 0.0, [Finding(
            "high", "fidelity",
            f"Chunk #{chunk_index} index out of bounds after re-chunking "
            f"(rechunked count={len(rechunked)}, stored count={len(stored_chunks)}).",
        )]

    stored_text = stored_chunks[chunk_index]
    fresh_text = rechunked[chunk_index]

    cos = cosine_similarity(stored_text, fresh_text)
    jac = jaccard_similarity(stored_text, fresh_text)

    findings: list[Finding] = []
    if cos < 0.70:
        findings.append(Finding(
            "high", "fidelity",
            f"Chunk #{chunk_index} has low idempotency cosine similarity ({cos:.2f}). "
            "Stored text may have been corrupted or mis-chunked.",
            f"Stored[:80]: {stored_text[:80]!r}  |  Fresh[:80]: {fresh_text[:80]!r}",
        ))
    elif cos < 0.90:
        findings.append(Finding(
            "medium", "fidelity",
            f"Chunk #{chunk_index} has moderate idempotency drift (cosine={cos:.2f}).",
        ))

    return cos, jac, findings


def check_fidelity_best_match(
    stored_chunk: str,
    chunk_index: int,
    pdf_words: list[str],
) -> tuple[float, float, list[Finding]]:
    """
    Slide a window over the full PDF word list and find the best-matching
    segment for this stored chunk using cosine similarity.

    This approach is chunking-algorithm agnostic: it works correctly whether
    the original upload used word-based, sentence-based, or any other chunking.
    The window size is proportional to the stored chunk length so we compare
    like-sized text spans.

    Returns (best_cosine, best_jaccard, findings).
    """
    findings: list[Finding] = []
    if not pdf_words:
        return 0.0, 0.0, [Finding(
            "high", "fidelity",
            f"Chunk #{chunk_index}: source PDF yielded no extractable text.",
        )]

    chunk_word_count = max(len(stored_chunk.split()), 10)
    # Window = 1.5x stored chunk size (gives context slack)
    window_words = min(int(chunk_word_count * 1.5) + 20, len(pdf_words))
    # Step = 25% of window for dense overlap
    step = max(1, window_words // 4)

    best_cos = 0.0
    best_jac = 0.0

    for start in range(0, len(pdf_words) - window_words + 1, step):
        window_text = " ".join(pdf_words[start: start + window_words])
        cos = cosine_similarity(stored_chunk, window_text)
        if cos > best_cos:
            best_cos = cos
            best_jac = jaccard_similarity(stored_chunk, window_text)

    if best_cos < 0.40:
        findings.append(Finding(
            "critical", "fidelity",
            f"Chunk #{chunk_index}: no closely matching text found in source PDF "
            f"(best cosine={best_cos:.2f}). Chunk may not belong to this document "
            "or text was heavily transformed during extraction.",
            stored_chunk[:100],
        ))
    elif best_cos < 0.60:
        findings.append(Finding(
            "high", "fidelity",
            f"Chunk #{chunk_index}: poor match to source PDF (best cosine={best_cos:.2f}).",
            stored_chunk[:80],
        ))
    elif best_cos < 0.80:
        findings.append(Finding(
            "medium", "fidelity",
            f"Chunk #{chunk_index}: moderate match to source PDF (best cosine={best_cos:.2f}).",
        ))

    return best_cos, best_jac, findings


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_chunk_scores(
    findings: list[Finding],
    cosine_fidelity: float | None,
    jaccard_fidelity: float | None,
    has_pdf_source: bool,
) -> dict:
    """
    Compute 0–100 quality scores from findings and similarity metrics.

    Weight scheme:
      With PDF source  : fidelity 40%, completeness 35%, boundary 25%
      Without PDF      : completeness 55%, boundary 35%, idempotency 10%
    """
    severity_deductions = {"critical": 30, "high": 15, "medium": 7, "low": 2}

    def _score_from_findings(category_filter: list[str]) -> int:
        base = 100
        for f in findings:
            if f.category in category_filter:
                base -= severity_deductions.get(f.severity, 0)
        return max(0, base)

    completeness_score = _score_from_findings(["completeness"])
    boundary_score = _score_from_findings(["boundary"])
    fidelity_score = _score_from_findings(["fidelity"])

    # Blend similarity metric into fidelity score when available
    if cosine_fidelity is not None:
        metric_score = int(cosine_fidelity * 100)
        # Average the metric-based score with the findings-based score
        fidelity_score = (fidelity_score + metric_score) // 2

    if has_pdf_source:
        overall = round(
            fidelity_score * 0.40
            + completeness_score * 0.35
            + boundary_score * 0.25
        )
    else:
        # No PDF: use idempotency-adjusted fidelity at lower weight
        overall = round(
            completeness_score * 0.55
            + boundary_score * 0.35
            + fidelity_score * 0.10
        )

    return {
        "completeness_score": completeness_score,
        "boundary_score": boundary_score,
        "fidelity_score": fidelity_score,
        "overall_score": overall,
        "cosine_similarity": round(cosine_fidelity, 4) if cosine_fidelity is not None else None,
        "jaccard_similarity": round(jaccard_fidelity, 4) if jaccard_fidelity is not None else None,
    }


# ---------------------------------------------------------------------------
# LLM review (optional, cached)
# ---------------------------------------------------------------------------

def _llm_cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def llm_review_chunk(
    chunk_text: str,
    chunk_index: int,
    doc_meta: dict,
    model: str = "gpt-4o-mini",
) -> list[Finding]:
    """
    Optional LLM review for a low-scoring chunk.
    Results are cached by content hash to avoid repeat API calls.

    Returns a list of additional Findings from the LLM.
    """
    cache_key = _llm_cache_key(chunk_text)
    LLM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    if LLM_CACHE_FILE.exists():
        try:
            cache = json.loads(LLM_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    if cache_key in cache:
        raw = cache[cache_key]
    else:
        try:
            import openai  # noqa: PLC0415
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                _log.warning("OPENAI_API_KEY not set — skipping LLM review for chunk #%d", chunk_index)
                return []
            client = openai.OpenAI(api_key=api_key, timeout=30.0)
            grade = doc_meta.get("grade", "?")
            subject = doc_meta.get("subject", "?")
            chapter = doc_meta.get("chapter", "?")
            prompt = (
                f"You are a CBSE educational content quality auditor.\n"
                f"Review this RAG chunk from a {grade} {subject} textbook, "
                f"chapter '{chapter}'.\n\n"
                f"CHUNK #{chunk_index}:\n{chunk_text[:1500]}\n\n"
                "Identify semantic quality issues: incomplete concepts, "
                "garbled formulas, missing context, factual errors, or "
                "encoding corruption.\n\n"
                "Return ONLY a JSON array of findings. Each finding must be:\n"
                '{"severity": "critical|high|medium|low", '
                '"category": "completeness|boundary|fidelity|structure", '
                '"message": "short description", "detail": "optional snippet"}\n'
                "Return [] if no issues. No markdown, just raw JSON array."
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
            )
            raw_text = (resp.choices[0].message.content or "[]").strip()
            # Strip accidental markdown fences
            raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE)
            raw = json.loads(raw_text)
            cache[cache_key] = raw
            LLM_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            _log.warning("LLM returned non-JSON for chunk #%d", chunk_index)
            return []
        except Exception as exc:
            _log.warning("LLM review failed for chunk #%d: %s", chunk_index, exc)
            return []

    return [
        Finding(
            f.get("severity", "low"),
            f.get("category", "structure"),
            f.get("message", ""),
            f.get("detail", ""),
        )
        for f in raw
        if isinstance(f, dict) and f.get("message")
    ]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def fetch_documents(
    grade: str | None,
    subject: str | None,
    document_id: str | None,
) -> list[dict]:
    """Fetch rag_documents matching filters from the correct DB(s)."""

    def _query(db, grade_hint: str | None) -> list[dict]:
        try:
            q = db.table("rag_documents").select(
                "id, grade, subject, chapter, title, source_type, created_at"
            ).order("created_at", desc=True)
            if document_id:
                q = q.eq("id", document_id)
            if grade_hint:
                q = q.eq("grade", grade_hint)
            if subject:
                q = q.eq("subject", subject)
            return q.execute().data or []
        except Exception as exc:
            _log.error("Failed to fetch documents: %s", exc)
            return []

    if document_id:
        # Try primary first, then grade-1112 DB
        docs = _query(admin_client, None)
        if not docs:
            try:
                from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
                docs = _query(grade_1112_client, None)
            except Exception:
                pass
        return docs

    if grade and is_grade_1112(grade):
        try:
            from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
            return _query(grade_1112_client, grade)
        except Exception:
            return []

    if grade:
        return _query(get_content_db(grade), grade)

    # No grade filter — query both DBs
    docs = _query(admin_client, None)
    try:
        from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
        docs += _query(grade_1112_client, None)
    except Exception:
        pass
    return docs


def fetch_chunks_for_document(document_id: str, grade: str | None) -> list[dict]:
    """Return all rag_chunks for a document, ordered by chunk_index."""
    db = get_content_db(grade)
    try:
        resp = (
            db.table("rag_chunks")
            .select("id, chunk_index, chunk_text")
            .eq("document_id", document_id)
            .order("chunk_index")
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        _log.error("Failed to fetch chunks for doc %s: %s", document_id, exc)
        return []


# ---------------------------------------------------------------------------
# Per-document audit
# ---------------------------------------------------------------------------

def audit_document(
    doc: dict,
    chunks: list[dict],
    pdf_path: Path | None,
    use_llm: bool,
    llm_threshold: int,
    verbose: bool,
) -> dict:
    """
    Audit all chunks for one rag_document.

    When pdf_path is provided, performs a full PDF fidelity check by
    re-extracting the PDF text, re-chunking it, and comparing each stored
    chunk against the corresponding re-extracted chunk using cosine + Jaccard
    similarity.

    When no pdf_path, performs an idempotency check: reconstructs the document
    text from stored chunks, re-chunks it, and checks for drift.

    Always runs completeness and boundary checks on every chunk.
    Optionally runs LLM review on chunks with overall_score < llm_threshold.
    """
    doc_id = doc.get("id", "?")
    grade = doc.get("grade", "")
    subject = doc.get("subject", "")
    chapter = doc.get("chapter", "")
    title = doc.get("title", "")

    has_pdf_source = pdf_path is not None
    pdf_words: list[str] = []
    pdf_extraction_method = "none"

    # --- Extract PDF word list for best-match fidelity check ---
    if pdf_path:
        try:
            full_text, pdf_extraction_method = extract_pdf_full_text(pdf_path)
            pdf_words = full_text.split()
            _log.debug(
                "PDF re-extracted: %d words via %s for doc %s",
                len(pdf_words), pdf_extraction_method, doc_id,
            )
        except Exception as exc:
            _log.warning("Failed to extract PDF %s: %s", pdf_path, exc)
            has_pdf_source = False

    # --- Sort chunks by index ---
    chunks_sorted = sorted(chunks, key=lambda c: c.get("chunk_index", 0))
    stored_texts = [c.get("chunk_text", "") for c in chunks_sorted]
    total = len(chunks_sorted)

    chunk_results: list[dict] = []
    all_findings: list[Finding] = []

    for pos, chunk_row in enumerate(chunks_sorted):
        idx = chunk_row.get("chunk_index", pos)
        text = chunk_row.get("chunk_text", "")
        is_first = pos == 0
        is_last = pos == total - 1

        chunk_findings: list[Finding] = []

        # 1. Completeness
        chunk_findings.extend(check_completeness(text, idx))

        # 2. Boundary
        chunk_findings.extend(check_boundaries(text, idx, is_first, is_last))

        # 3. Fidelity
        cos_score: float | None = None
        jac_score: float | None = None

        if has_pdf_source and pdf_words:
            cos_score, jac_score, fid_findings = check_fidelity_best_match(
                text, idx, pdf_words
            )
            chunk_findings.extend(fid_findings)
        else:
            cos_score, jac_score, fid_findings = check_fidelity_idempotency(
                stored_texts, idx
            )
            chunk_findings.extend(fid_findings)

        # 4. Scores
        scores = compute_chunk_scores(
            chunk_findings, cos_score, jac_score, has_pdf_source
        )

        # 5. Optional LLM review for low-scoring chunks
        llm_findings: list[Finding] = []
        if use_llm and scores["overall_score"] < llm_threshold:
            try:
                llm_findings = llm_review_chunk(text, idx, doc)
                chunk_findings.extend(llm_findings)
                # Recompute scores after LLM findings
                scores = compute_chunk_scores(
                    chunk_findings, cos_score, jac_score, has_pdf_source
                )
            except Exception as exc:
                _log.warning("LLM review failed for chunk #%d: %s", idx, exc)

        all_findings.extend(chunk_findings)

        chunk_result = {
            "chunk_id": chunk_row.get("id", ""),
            "chunk_index": idx,
            "chunk_text_preview": text[:120] + ("..." if len(text) > 120 else ""),
            "char_count": len(text),
            "word_count": len(text.split()),
            "scores": scores,
            "finding_count": len(chunk_findings),
            "llm_finding_count": len(llm_findings),
            "findings": [f.to_dict() for f in chunk_findings],
            "needs_review": scores["overall_score"] < llm_threshold,
        }
        chunk_results.append(chunk_result)

        if verbose:
            flag = "FLAG" if chunk_result["needs_review"] else "ok"
            _log.info(
                "  [%s] chunk #%d score=%d complete=%d boundary=%d fidelity=%d cos=%s",
                flag, idx,
                scores["overall_score"],
                scores["completeness_score"],
                scores["boundary_score"],
                scores["fidelity_score"],
                f"{cos_score:.2f}" if cos_score is not None else "n/a",
            )

    # --- Aggregate document scores ---
    if chunk_results:
        avg_overall = round(
            sum(r["scores"]["overall_score"] for r in chunk_results) / len(chunk_results)
        )
        avg_completeness = round(
            sum(r["scores"]["completeness_score"] for r in chunk_results) / len(chunk_results)
        )
        avg_boundary = round(
            sum(r["scores"]["boundary_score"] for r in chunk_results) / len(chunk_results)
        )
        avg_fidelity = round(
            sum(r["scores"]["fidelity_score"] for r in chunk_results) / len(chunk_results)
        )
        flagged_count = sum(1 for r in chunk_results if r["needs_review"])
    else:
        avg_overall = avg_completeness = avg_boundary = avg_fidelity = 0
        flagged_count = 0

    findings_summary = {
        "critical": sum(1 for f in all_findings if f.severity == "critical"),
        "high": sum(1 for f in all_findings if f.severity == "high"),
        "medium": sum(1 for f in all_findings if f.severity == "medium"),
        "low": sum(1 for f in all_findings if f.severity == "low"),
    }

    return {
        "document_id": doc_id,
        "grade": grade,
        "subject": subject,
        "chapter": chapter,
        "title": title,
        "chunk_count": total,
        "flagged_chunk_count": flagged_count,
        "has_pdf_source": has_pdf_source,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_extraction_method": pdf_extraction_method,
        "scores": {
            "overall": avg_overall,
            "completeness": avg_completeness,
            "boundary": avg_boundary,
            "fidelity": avg_fidelity,
        },
        "findings_summary": findings_summary,
        "total_findings": len(all_findings),
        "chunks": chunk_results,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _write_json(results: list[dict], out_dir: Path) -> Path:
    p = out_dir / "chunk_quality_report.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(results),
        "documents": results,
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("JSON report: %s", p)
    return p


def _write_markdown(results: list[dict], out_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_chunks = sum(r["chunk_count"] for r in results)
    total_flagged = sum(r["flagged_chunk_count"] for r in results)
    avg_score = round(
        sum(r["scores"]["overall"] for r in results) / max(len(results), 1)
    )

    lines = [
        "# Chunk Quality Audit Report",
        "",
        f"_Generated: {ts}_",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Documents audited | {len(results)} |",
        f"| Total chunks | {total_chunks} |",
        f"| Flagged chunks | {total_flagged} |",
        f"| Average overall score | {avg_score}/100 |",
        "",
        "---",
        "",
        "## Score Distribution",
        "",
        "| Grade | Subject | Chapter | Chunks | Overall | Completeness | Boundary | Fidelity | Flagged |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for r in sorted(results, key=lambda x: x["scores"]["overall"]):
        sc = r["scores"]
        lines.append(
            f"| {r['grade']} | {r['subject']} | {r['chapter'][:35]} "
            f"| {r['chunk_count']} | {sc['overall']} "
            f"| {sc['completeness']} | {sc['boundary']} | {sc['fidelity']} "
            f"| {r['flagged_chunk_count']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Flagged Chunks (needs review)",
        "",
    ]

    flagged_any = False
    for r in results:
        flagged = [c for c in r["chunks"] if c["needs_review"]]
        if not flagged:
            continue
        flagged_any = True
        lines.append(
            f"### {r['grade']} — {r['subject']} — {r['chapter']} "
            f"(doc: `{r['document_id'][:8]}...`)"
        )
        lines.append("")
        for c in flagged:
            sc = c["scores"]
            lines.append(
                f"**Chunk #{c['chunk_index']}** "
                f"score={sc['overall_score']} | "
                f"complete={sc['completeness_score']} | "
                f"boundary={sc['boundary_score']} | "
                f"fidelity={sc['fidelity_score']}"
            )
            lines.append(f"> {c['chunk_text_preview']}")
            for f in c["findings"]:
                if f["severity"] in ("critical", "high"):
                    lines.append(
                        f"  - **[{f['severity'].upper()}]** {f['category']}: {f['message']}"
                    )
            lines.append("")

    if not flagged_any:
        lines.append("_No chunks flagged. All chunks are above the review threshold._")
        lines.append("")

    lines += [
        "---",
        "",
        "## Critical & High Findings by Document",
        "",
    ]

    for r in results:
        crit_high = [
            f for c in r["chunks"]
            for f in c["findings"]
            if f["severity"] in ("critical", "high")
        ]
        if not crit_high:
            continue
        lines.append(f"### {r['grade']} / {r['subject']} / {r['chapter']}")
        for f in crit_high[:20]:
            detail = f" — `{f['detail'][:80]}`" if f.get("detail") else ""
            lines.append(f"- **[{f['severity'].upper()}]** `{f['category']}`: {f['message']}{detail}")
        lines.append("")

    lines += [
        "---",
        "",
        "_Generated by `audit_chunk_quality.py`._",
    ]

    p = out_dir / "chunk_quality_report.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    _log.info("Markdown report: %s", p)
    return p


def _write_csv(results: list[dict], out_dir: Path) -> Path:
    p = out_dir / "chunk_quality_summary.csv"
    fieldnames = [
        "document_id", "grade", "subject", "chapter", "title",
        "chunk_count", "flagged_count", "has_pdf_source",
        "avg_overall", "avg_completeness", "avg_boundary", "avg_fidelity",
        "critical_findings", "high_findings", "medium_findings", "low_findings",
        "audited_at",
    ]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            sc = r["scores"]
            fs = r["findings_summary"]
            writer.writerow({
                "document_id": r["document_id"],
                "grade": r["grade"],
                "subject": r["subject"],
                "chapter": r["chapter"],
                "title": r["title"],
                "chunk_count": r["chunk_count"],
                "flagged_count": r["flagged_chunk_count"],
                "has_pdf_source": r["has_pdf_source"],
                "avg_overall": sc["overall"],
                "avg_completeness": sc["completeness"],
                "avg_boundary": sc["boundary"],
                "avg_fidelity": sc["fidelity"],
                "critical_findings": fs["critical"],
                "high_findings": fs["high"],
                "medium_findings": fs["medium"],
                "low_findings": fs["low"],
                "audited_at": r["audited_at"],
            })
    _log.info("CSV report: %s", p)
    return p


def _write_flagged_chunks_csv(results: list[dict], out_dir: Path) -> Path:
    """Write a detailed CSV of every flagged chunk for direct triage."""
    p = out_dir / "flagged_chunks.csv"
    fieldnames = [
        "document_id", "grade", "subject", "chapter",
        "chunk_id", "chunk_index",
        "overall_score", "completeness_score", "boundary_score", "fidelity_score",
        "cosine_similarity", "jaccard_similarity",
        "finding_count", "top_finding_severity", "top_finding_message",
        "chunk_text_preview",
    ]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for r in results:
            for c in r["chunks"]:
                if not c["needs_review"]:
                    continue
                sc = c["scores"]
                findings_sorted = sorted(
                    c["findings"], key=lambda f: sev_rank.get(f["severity"], 9)
                )
                top = findings_sorted[0] if findings_sorted else {}
                writer.writerow({
                    "document_id": r["document_id"],
                    "grade": r["grade"],
                    "subject": r["subject"],
                    "chapter": r["chapter"],
                    "chunk_id": c["chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "overall_score": sc["overall_score"],
                    "completeness_score": sc["completeness_score"],
                    "boundary_score": sc["boundary_score"],
                    "fidelity_score": sc["fidelity_score"],
                    "cosine_similarity": sc.get("cosine_similarity", ""),
                    "jaccard_similarity": sc.get("jaccard_similarity", ""),
                    "finding_count": c["finding_count"],
                    "top_finding_severity": top.get("severity", ""),
                    "top_finding_message": top.get("message", ""),
                    "chunk_text_preview": c["chunk_text_preview"],
                })
    _log.info("Flagged chunks CSV: %s", p)
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:  # noqa: C901
    parser = argparse.ArgumentParser(
        description="Chunk Quality Auditor — RAG Vector DB QA tool (read-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--grade", help="Filter by grade, e.g. 9 or 'Grade 9'")
    parser.add_argument("--subject", help="Filter by subject, e.g. Maths")
    parser.add_argument("--document-id", dest="document_id", help="Audit a single document UUID")
    parser.add_argument("--pdf-dir", dest="pdf_dir", help="Path to folder with source PDFs")
    parser.add_argument("--sample", type=int, metavar="N", help="Sample N documents randomly")
    parser.add_argument("--use-llm", dest="use_llm", action="store_true",
                        help="Enable LLM review of low-scoring chunks (cached)")
    parser.add_argument("--llm-threshold", dest="llm_threshold", type=int,
                        default=LLM_REVIEW_THRESHOLD_DEFAULT,
                        help=f"Score threshold for LLM review (default {LLM_REVIEW_THRESHOLD_DEFAULT})")
    parser.add_argument("--output", default="reports/chunk_quality",
                        help="Output directory (default: reports/chunk_quality/)")
    parser.add_argument("--fail-below", dest="fail_below", type=int,
                        help="Exit 1 if average overall score < N (CI gate)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-chunk detail to stdout")
    args = parser.parse_args()

    # Normalise grade
    grade = args.grade
    if grade and not grade.startswith("Grade ") and not grade.startswith("grade "):
        grade = "Grade " + grade

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # PDF index
    pdf_dir: Path | None = None
    pdf_index: dict[str, Path] = {}
    if args.pdf_dir:
        pdf_dir = Path(args.pdf_dir).expanduser().resolve()
        if not pdf_dir.exists():
            _log.error("--pdf-dir path does not exist: %s", pdf_dir)
            sys.exit(1)
        pdf_index = build_pdf_index(pdf_dir)

    # Fetch documents
    _log.info(
        "Fetching documents (grade=%s, subject=%s, doc_id=%s)...",
        grade, args.subject, args.document_id,
    )
    docs = fetch_documents(grade, args.subject, args.document_id)

    if not docs:
        _log.warning("No documents found matching filters. Nothing to audit.")
        sys.exit(0)

    # Optional sampling
    if args.sample and len(docs) > args.sample:
        import random
        random.shuffle(docs)
        docs = docs[: args.sample]
        _log.info("Sampling %d documents.", args.sample)

    _log.info("Auditing %d document(s)...", len(docs))

    results: list[dict] = []
    for doc in docs:
        doc_id = doc.get("id", "?")
        doc_grade = doc.get("grade", "")
        doc_label = f"{doc_grade} / {doc.get('subject')} / {doc.get('chapter')}"

        # Fetch chunks
        chunks = fetch_chunks_for_document(str(doc_id), doc_grade)
        if not chunks:
            _log.warning("  No chunks for doc %s (%s) — skipping.", str(doc_id)[:8], doc_label)
            continue

        # Find source PDF if pdf_dir was given
        pdf_path: Path | None = None
        if pdf_dir and pdf_index:
            pdf_path = find_source_pdf(doc, pdf_index, pdf_dir)
            if pdf_path:
                _log.info("  PDF found: %s", pdf_path.name)
            else:
                _log.debug("  No source PDF found for %s", doc_label)

        _log.info(
            "  Auditing %s (%d chunks, pdf=%s)",
            doc_label, len(chunks), pdf_path.name if pdf_path else "none",
        )

        result = audit_document(
            doc=doc,
            chunks=chunks,
            pdf_path=pdf_path,
            use_llm=args.use_llm,
            llm_threshold=args.llm_threshold,
            verbose=args.verbose,
        )
        results.append(result)

        sc = result["scores"]
        _log.info(
            "  Done: score=%d complete=%d boundary=%d fidelity=%d flagged=%d/%d",
            sc["overall"], sc["completeness"], sc["boundary"], sc["fidelity"],
            result["flagged_chunk_count"], result["chunk_count"],
        )

    if not results:
        _log.warning("No documents were audited (all had empty chunk lists).")
        sys.exit(0)

    # Write reports
    _write_json(results, out_dir)
    _write_markdown(results, out_dir)
    _write_csv(results, out_dir)
    _write_flagged_chunks_csv(results, out_dir)

    # Summary
    total_chunks = sum(r["chunk_count"] for r in results)
    total_flagged = sum(r["flagged_chunk_count"] for r in results)
    total_critical = sum(r["findings_summary"]["critical"] for r in results)
    avg_overall = round(sum(r["scores"]["overall"] for r in results) / len(results))
    avg_completeness = round(sum(r["scores"]["completeness"] for r in results) / len(results))
    avg_boundary = round(sum(r["scores"]["boundary"] for r in results) / len(results))
    avg_fidelity = round(sum(r["scores"]["fidelity"] for r in results) / len(results))
    pct_flagged = round(total_flagged / max(total_chunks, 1) * 100, 1)

    sep = "=" * 65
    print("")
    print(sep)
    print("  CHUNK QUALITY AUDIT COMPLETE")
    print(sep)
    print(f"  Documents audited   : {len(results)}")
    print(f"  Total chunks        : {total_chunks}")
    print(f"  Flagged for review  : {total_flagged}  ({pct_flagged}%)")
    print(f"  Critical findings   : {total_critical}")
    print(f"  Avg overall score   : {avg_overall}/100")
    print(f"  Avg completeness    : {avg_completeness}/100")
    print(f"  Avg boundary        : {avg_boundary}/100")
    print(f"  Avg fidelity        : {avg_fidelity}/100")
    print(f"  Reports in          : {out_dir}/")
    print(sep)
    print("")

    if total_flagged > 0:
        print(f"  {total_flagged} chunk(s) need review. See:")
        print(f"    {out_dir}/flagged_chunks.csv")
        print(f"    {out_dir}/chunk_quality_report.md")
        print("")

    if args.fail_below is not None and avg_overall < args.fail_below:
        _log.error(
            "Average overall score %d is below --fail-below threshold %d. Exiting 1.",
            avg_overall, args.fail_below,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
