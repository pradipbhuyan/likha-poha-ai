"""
Doubt Knowledge Base Service (DKB)
===================================
Internal semantic Q&A cache for the Ask Doubt feature.

Design goals
------------
- Students are always served an answer — either instantly from the DB or via
  LLM fallback.  The source is never disclosed to students.
- Every LLM-generated answer is stored back in the DB so the same question
  (or semantically equivalent) never triggers an LLM call again.
- Lesson suggestion cards show ONLY questions that have pre-cached answers in
  the DKB, so every card click is zero-token-cost.
- Admins can see hit rates, growth, and estimated savings in the admin console.

Usage
-----
Run backend/sql/add_doubt_kb.sql in Supabase before enabling.
Pre-warm via the admin cache management panel:
  POST /api/cache/prewarm/doubt-kb/{grade-slug}
"""

import logging

from app.services.grade_db_router import get_content_db
from app.services.auth_service import admin_client as _primary_client
from app.services.rag_service import create_embedding

logger = logging.getLogger(__name__)

# Module-level flag: set to False after the first embedding 401/auth failure
# so we don't make a failing OpenAI API call for every subsequent DKB entry
# during the same process lifetime.  Resets on process restart.
_embedding_available: bool = True

# Minimum cosine similarity to consider a DB match acceptable.
# 0.50 is calibrated from live Supabase pgvector data:
#   - Exact card clicks (same text): ~1.000 — always found
#   - Paraphrased questions ("what is a tissue"): 0.50-0.58 — found at 0.50
#   - Semantically related but different: 0.45-0.50 — borderline
#   - Unrelated questions: < 0.45 — correctly excluded
# NOTE: UI command chips ("Show a diagram", "Explain in simpler words")
# score < 0.45 for Science content questions and will correctly MISS.
SIMILARITY_THRESHOLD = 0.50

# How many DKB questions to show as lesson suggestion cards.
LESSON_SUGGESTION_LIMIT = 6


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------

def search_doubt_kb(
    question: str,
    grade: str,
    subject: str,
    chapter: str | None,
    mode: str = "CBSE",
    board: str = "CBSE",
    threshold: float = SIMILARITY_THRESHOLD,
) -> dict | None:
    """
    Semantic search for a matching Q&A pair in the Doubt Knowledge Base.

    Returns the best-matching answer dict if similarity >= threshold, else None.
    The caller falls back to LLM when None is returned.

    Search strategy:
    1. Try exact chapter filter (fastest, most relevant).
    2. If no match, broaden to subject-level search (no chapter filter).
       DKB prewarm may store chapters with prefixes like "Chapter 2: Cell..."
       while the request sends "Cell: The Building Block of Life" — subject-level
       search handles this naming inconsistency gracefully.

    Return shape:
        {"answer": str, "question": str, "source_type": "DOUBT_KB",
         "id": str, "similarity": float}
    """
    supabase = get_content_db(grade)
    try:
        # Pass 0: text match — works for suggestion chip questions and
        # databases that don't have the match_doubt_kb pgvector RPC function.
        # Try: (a) exact ILIKE, (b) contains ILIKE on first 50 chars,
        # (c) retry (a) and (b) without status filter if status column missing.
        _q_clean = question.strip().rstrip("?").strip()
        _q_prefix = _q_clean[:50]  # first 50 chars as prefix for contains match
        for _with_status in (True, False):
            try:
                def _base():
                    b = (supabase.table("doubt_kb")
                         .select("id, question, answer, hit_count")
                         .eq("grade", grade))
                    if _with_status:
                        b = b.eq("status", "active")
                    if subject:
                        b = b.eq("subject", subject)
                    return b

                # (a) exact case-insensitive match
                exact_rows = _base().ilike("question", question).limit(1).execute().data or []

                # (b) contains match — handles trailing punctuation / whitespace variants
                if not exact_rows and _q_prefix:
                    exact_rows = _base().ilike("question", f"%{_q_prefix}%").order("hit_count", desc=True).limit(1).execute().data or []

                if exact_rows:
                    row = exact_rows[0]
                    try:
                        supabase.table("doubt_kb").update({
                            "hit_count": (row.get("hit_count") or 0) + 1,
                            "last_hit_at": "now()",
                        }).eq("id", row["id"]).execute()
                    except Exception:
                        pass
                    return {
                        "answer": row["answer"],
                        "question": row["question"],
                        "source_type": "DOUBT_KB",
                        "id": row["id"],
                        "similarity": 1.0,
                    }
                break  # query ran OK (0 rows), no need to retry
            except Exception as pass0_exc:
                if _with_status:
                    logger.debug("DKB Pass 0 with status filter failed, retrying: %s", pass0_exc)
                    continue
                logger.warning("DKB Pass 0 text match failed: %s", pass0_exc)
                break

        embedding = create_embedding(question)

        # Pass 1: try with exact chapter filter
        result = supabase.rpc(
            "match_doubt_kb",
            {
                "query_embedding": embedding,
                "match_count": 1,
                "similarity_threshold": threshold,
                "filter_grade": grade,
                "filter_subject": subject,
                "filter_chapter": chapter,
                "filter_mode": mode,
            },
        ).execute()

        rows = result.data or []

        # Pass 2: if no match with chapter filter, broaden to subject-level.
        # Chapter names stored in DKB may include number prefixes (e.g. "Chapter 2: Cell…")
        # that don't match the display name used in the lesson/doubt request.
        if not rows and chapter:
            result = supabase.rpc(
                "match_doubt_kb",
                {
                    "query_embedding": embedding,
                    "match_count": 1,
                    "similarity_threshold": threshold,
                    "filter_grade": grade,
                    "filter_subject": subject,
                    "filter_chapter": None,   # no chapter filter
                    "filter_mode": mode,
                },
            ).execute()
            rows = result.data or []

        if not rows:
            return None

        row = rows[0]

        # Increment hit count fire-and-forget
        try:
            supabase.table("doubt_kb").update({
                "hit_count": (row.get("hit_count") or 0) + 1,
                "last_hit_at": "now()",
            }).eq("id", row["id"]).execute()
        except Exception:
            pass

        return {
            "answer": row["answer"],
            "question": row["question"],
            "source_type": "DOUBT_KB",
            "id": row["id"],
            "similarity": row.get("similarity", 1.0),
        }

    except Exception as exc:
        logger.warning("DKB search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Storage (auto-called after every LLM answer)
# ---------------------------------------------------------------------------

def store_in_doubt_kb(
    question: str,
    answer: str,
    grade: str,
    subject: str,
    chapter: str | None,
    mode: str = "CBSE",
    board: str = "CBSE",
    source: str = "llm",
) -> str | None:
    """
    Store a new Q&A pair in the Doubt Knowledge Base with its embedding.

    Called automatically after every LLM-generated doubt answer so the DB
    grows with each new question that wasn't already covered.

    Returns the new row id, or None on failure.
    """
    supabase = get_content_db(grade)
    try:
        # Attempt to generate a vector embedding for semantic search.
        # If the OpenAI embedding API is unavailable or the key is invalid,
        # we store the Q&A pair without an embedding rather than losing the
        # entry entirely. Keyword/exact-match lookups still work; vector
        # similarity search is skipped for this entry.
        #
        # _embedding_available is a module-level short-circuit: after the first
        # 401/auth failure we skip the API call entirely for the rest of the
        # process lifetime so we don't make a failing network call per entry.
        global _embedding_available
        embedding = None
        if _embedding_available:
            try:
                embedding = create_embedding(question)
            except Exception as emb_exc:
                err_str = str(emb_exc)
                # Permanent auth/key failure — disable for this process
                if "401" in err_str or "invalid_api_key" in err_str or "Incorrect API key" in err_str:
                    _embedding_available = False
                    logger.warning(
                        "DKB embedding disabled (invalid OpenAI key) — "
                        "storing without vectors. Update the OpenAI key in "
                        "Admin Console → AI Studio to re-enable. Error: %s", emb_exc
                    )
                else:
                    logger.warning(
                        "DKB embedding failed (storing without vector): %s", emb_exc
                    )

        row = {
            "grade": grade,
            "board": board,
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
            "question": question,
            "answer": answer,
            "source": source,
            "hit_count": 0,
            "status": "active",
        }
        if embedding is not None:
            row["embedding"] = embedding

        result = supabase.table("doubt_kb").insert(row).execute()

        rows = result.data or []
        return rows[0]["id"] if rows else None

    except Exception as exc:
        logger.warning("DKB store failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Lesson suggestion cards
# ---------------------------------------------------------------------------

def get_lesson_doubt_suggestions(
    grade: str,
    subject: str,
    chapter: str,
    mode: str = "CBSE",
    limit: int = LESSON_SUGGESTION_LIMIT,
) -> list[dict]:
    """
    Return pre-answered questions for a lesson chapter to show as card prompts.

    Only questions that already have answers in the DKB are returned so every
    card click is served instantly at zero token cost.

    The DKB prewarm stores chapters using RAG document names which may include
    "Chapter N:" prefixes (e.g. "Chapter 2: Cell: The Building Block of Life").
    The lesson route sends chapter names without this prefix.  We try both
    forms so suggestions appear regardless of the naming convention used at
    prewarm time.

    Returns list of {"id": str, "question": str} ordered by popularity.
    """
    import re as _re  # noqa: PLC0415
    supabase = get_content_db(grade)

    def _call_rpc(ch):
        return supabase.rpc(
            "get_doubt_kb_suggestions",
            {"p_grade": grade, "p_subject": subject, "p_chapter": ch,
             "p_mode": mode, "p_limit": limit},
        ).execute().data or []

    try:
        rows = _call_rpc(chapter)

        # If no results, try with "Chapter N: " prefix stripped from the request chapter.
        # Lesson sends "Cell: The Building Block of Life" but DKB stores
        # "Chapter 2: Cell: The Building Block of Life".
        if not rows:
            stripped = _re.sub(r"^Chapter\s+\d+\s*:\s*", "", chapter, flags=_re.IGNORECASE).strip()
            if stripped and stripped != chapter:
                rows = _call_rpc(stripped)

        # If still no results, query the table directly with ILIKE on chapter
        # (the get_doubt_kb_suggestions RPC does not support NULL as 'match all').
        if not rows:
            core = _re.sub(
                r"^(?:Chapter\s+\d+\s*:\s*|Text Book\s*-\s*|Supplementary Reader\s*-\s*|"
                r"Workbook\s*-\s*|History\s*-\s*|Geography\s*-\s*|Economics\s*-\s*|"
                r"Political Science\s*-\s*)",
                "",
                chapter,
                flags=_re.IGNORECASE,
            ).strip()
            if core:
                direct = (
                    supabase
                    .table("doubt_kb")
                    .select("id, question, hit_count")
                    .eq("grade", grade)
                    .eq("subject", subject)
                    .eq("mode", mode)
                    .eq("status", "active")
                    .ilike("chapter", f"%{core}%")
                    .order("hit_count", desc=True)
                    .limit(limit)
                    .execute()
                )
                rows = direct.data or []

        return [{"id": row["id"], "question": row["question"]} for row in rows]

    except Exception as exc:
        logger.warning("DKB suggestions failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Admin stats
# ---------------------------------------------------------------------------

def get_doubt_kb_stats() -> dict:
    """
    Return aggregate DKB stats for the admin analytics console.

    Shows total entries, prewarmed vs auto-generated, hit rate, and estimated
    token savings.  Estimated savings assume each DB hit saves one LLM call
    at ~1500 tokens × $0.0001/1K = ~$0.00015 per hit.
    """
    def _stats_for_db(db):
        try:
            prewarmed_res = db.table("doubt_kb") \
                .select("id", count="exact") \
                .eq("status", "active").eq("source", "prewarmed").execute()
            prewarmed = prewarmed_res.count or 0
            llm_res = db.table("doubt_kb") \
                .select("id", count="exact") \
                .eq("status", "active").eq("source", "llm").execute()
            llm_gen = llm_res.count or 0
            hits_res = db.table("doubt_kb").select("hit_count").eq("status", "active").execute()
            total_hits = sum((r.get("hit_count") or 0) for r in (hits_res.data or []))
            grade_result = db.table("doubt_kb").select("grade, hit_count").eq("status", "active").execute()
            return prewarmed, llm_gen, total_hits, grade_result.data or []
        except Exception:
            return 0, 0, 0, []

    try:
        prewarmed, llm_generated, total_hits, grade_data = _stats_for_db(_primary_client)

        saved_per_hit = (1500 / 1000) * 0.0001 + (800 / 1000) * 0.0004
        estimated_savings = round(total_hits * saved_per_hit, 4)

        grade_breakdown = {}
        for r in grade_data:
            g = r.get("grade", "Unknown")
            grade_breakdown[g] = grade_breakdown.get(g, 0) + (r.get("hit_count") or 0)

        return {
            "total_entries": prewarmed + llm_generated,
            "prewarmed": prewarmed,
            "llm_generated": llm_generated,
            "total_hits": total_hits,
            "estimated_savings_usd": estimated_savings,
            "hits_by_grade": grade_breakdown,
        }

    except Exception as exc:
        logger.warning("DKB stats failed: %s", exc)
        return {
            "total_entries": 0, "prewarmed": 0, "llm_generated": 0,
            "total_hits": 0, "estimated_savings_usd": 0.0, "hits_by_grade": {},
        }


def _get_doubt_kb_stats_REMOVED() -> dict:
    """(Replaced by the multi-DB version above — kept for reference.)"""
    supabase = _primary_client
    try:
        # Use server-side counts to avoid the 1000-row default page limit.
        prewarmed_res = supabase.table("doubt_kb") \
            .select("id", count="exact") \
            .eq("status", "active").eq("source", "prewarmed").execute()
        prewarmed = prewarmed_res.count or 0

        llm_res = supabase.table("doubt_kb") \
            .select("id", count="exact") \
            .eq("status", "active").eq("source", "llm").execute()
        llm_generated = llm_res.count or 0

        hits_res = supabase.table("doubt_kb") \
            .select("hit_count") \
            .eq("status", "active").execute()
        total_hits = sum((r.get("hit_count") or 0) for r in (hits_res.data or []))

        # Estimated savings: each hit saves ~1500 input + 800 output tokens
        # gpt-4.1-nano: $0.0001/1K input, $0.0004/1K output
        saved_per_hit = (1500 / 1000) * 0.0001 + (800 / 1000) * 0.0004
        estimated_savings = round(total_hits * saved_per_hit, 4)

        # Grade-level breakdown — separate query
        grade_breakdown = {}
        grade_result = supabase.table("doubt_kb").select(
            "grade, hit_count"
        ).eq("status", "active").execute()

        for r in (grade_result.data or []):
            g = r.get("grade", "Unknown")
            grade_breakdown[g] = grade_breakdown.get(g, 0) + (r.get("hit_count") or 0)

        return {
            "total_entries": prewarmed + llm_generated,
            "prewarmed": prewarmed,
            "llm_generated": llm_generated,
            "total_hits": total_hits,
            "estimated_savings_usd": estimated_savings,
            "hits_by_grade": grade_breakdown,
        }

    except Exception as exc:
        logger.warning("DKB stats failed: %s", exc)
        return {
            "total_entries": 0,
            "prewarmed": 0,
            "llm_generated": 0,
            "total_hits": 0,
            "estimated_savings_usd": 0.0,
            "hits_by_grade": {},
        }


def get_dkb_chapter_status(grade: str) -> list[dict]:
    """
    For admin panel: list all syllabus chapters with DKB entry counts.
    Returns [{"subject": str, "chapter": str, "entries": int,
              "prewarmed": int, "llm": int, "gpt55": int, "admin_approved": int}]

    Unlike get_doubt_kb_grade_stats (per-subject only), this breaks counts
    down per chapter so an admin can see exactly which chapters still need
    a coverage pass -- mirrors lesson_kb_service.get_lkb_chapter_status.

    Matches on normalize_chapter_core(), NOT the raw chapter string. The
    student-facing dropdown shows a display-prefixed chapter name for
    multi-book subjects (e.g. "Text Book - Part 1 - 1. Locating Places on
    the Earth"), which is exactly what gets sent to /api/doubt/answer and
    what earlier DKB prewarm runs stored -- while get_syllabus_for_grade
    (used here to enumerate syllabus chapters) returns the bare form. An
    exact-string match would report most multi-book chapters as uncovered
    even when 30-60 Q&A pairs already exist for them under the prefixed
    name. Confirmed live: this exact-match version reported 51 of 54
    "zero-coverage" Grade 5-7 chapters as gaps when the content already
    existed under a mismatched chapter string.

    Fetches ALL active rows via explicit .range() pagination -- a plain
    .execute() silently caps at 1000 rows (PostgREST default page size),
    and every grade here already has 1,500-3,900+ active doubt_kb rows.
    Confirmed live: without pagination this function was aggregating off a
    truncated ~1000-row sample, reporting real chapters as zero-coverage
    simply because their rows fell outside the arbitrary first page.
    """
    try:
        from app.services.prewarm_service import get_syllabus_for_grade  # noqa: PLC0415
        from app.services.mock_test_service import normalize_chapter_core  # noqa: PLC0415
        syllabus = get_syllabus_for_grade(grade)
        cbse_data = syllabus.get("CBSE", {})

        supabase = get_content_db(grade)
        rows: list[dict] = []
        page_size = 1000
        start = 0
        while True:
            page = (
                supabase.table("doubt_kb")
                .select("subject, chapter, source")
                .eq("grade", grade)
                .eq("status", "active")
                .order("id")  # stable order required for correct pagination —
                # without it, Postgrest gives no guarantee that consecutive
                # .range() pages are disjoint when rows are being inserted
                # concurrently (confirmed live: running this while a batch
                # ingest was still writing produced a doubled count for one
                # chapter whose rows straddled a page boundary).
                .range(start, start + page_size - 1)
                .execute()
            ).data or []
            rows.extend(page)
            if len(page) < page_size:
                break
            start += page_size

        # Build per-(subject, normalized chapter core) breakdown by source —
        # aggregates every display-prefix variant of the same logical chapter.
        breakdown: dict[tuple, dict] = {}
        for row in rows:
            key = (row.get("subject"), normalize_chapter_core(row.get("chapter") or ""))
            entry = breakdown.setdefault(
                key, {"entries": 0, "prewarmed": 0, "llm": 0, "gpt55": 0, "admin_approved": 0}
            )
            entry["entries"] += 1
            src = row.get("source") or "llm"
            if src in entry:
                entry[src] += 1
            else:
                entry["llm"] += 1

        result = []
        for subject, chapters in cbse_data.items():
            for chapter in chapters:
                key = (subject, normalize_chapter_core(chapter))
                counts = breakdown.get(key, {
                    "entries": 0, "prewarmed": 0, "llm": 0, "gpt55": 0, "admin_approved": 0,
                })
                result.append({"subject": subject, "chapter": chapter, **counts})
        return result
    except Exception as exc:
        logger.warning("DKB chapter status failed for %s: %s", grade, exc)
        return []


def get_doubt_kb_grade_stats(grade: str) -> dict:
    """Return per-subject DKB entry counts for one grade."""
    supabase = get_content_db(grade)
    try:
        result = supabase.table("doubt_kb").select(
            "subject, hit_count, source"
        ).eq("grade", grade).eq("status", "active").execute()

        by_subject = {}
        for r in (result.data or []):
            subj = r.get("subject", "Unknown")
            if subj not in by_subject:
                by_subject[subj] = {"entries": 0, "hits": 0, "prewarmed": 0, "llm": 0}
            by_subject[subj]["entries"] += 1
            by_subject[subj]["hits"] += r.get("hit_count") or 0
            src_key = "prewarmed" if r.get("source") == "prewarmed" else "llm"
            by_subject[subj][src_key] += 1

        return {
            "grade": grade,
            "subjects": by_subject,
            "total_entries": sum(s["entries"] for s in by_subject.values()),
            "total_hits": sum(s["hits"] for s in by_subject.values()),
        }

    except Exception as exc:
        logger.warning("DKB grade stats failed for %s: %s", grade, exc)
        return {"grade": grade, "subjects": {}, "total_entries": 0, "total_hits": 0}


# ---------------------------------------------------------------------------
# Prewarm: generate Q&A pairs for a chapter
# ---------------------------------------------------------------------------

def prewarm_doubt_kb_for_chapter(
    grade: str,
    subject: str,
    chapter: str,
    mode: str = "CBSE",
    board: str = "CBSE",
    num_questions: int = 25,
    username: str = "prewarm_admin",
) -> dict:
    """
    Generate and store pre-answered Q&A pairs for one chapter.

    Uses gpt-4.1-nano + RAG context to anticipate the most common student
    doubts for the chapter, then generates answers and stores them with
    embeddings in the DKB.

    Already-existing questions for the chapter are checked first to avoid
    duplicate generation.  Safe to re-run.

    Returns {"generated": int, "skipped_existing": int, "errors": int}
    """
    from app.services.rag_service import search_textbook_content  # noqa: PLC0415
    from app.services.openai_service import ask_llm, PREWARM_TEXT_MODEL  # noqa: PLC0415
    import json  # noqa: PLC0415

    # Check how many Q&A pairs already exist for this chapter
    supabase = get_content_db(grade)
    try:
        existing = supabase.table("doubt_kb").select(
            "id", count="exact"
        ).eq("grade", grade).eq("subject", subject).eq("chapter", chapter).eq(
            "status", "active"
        ).execute()
        existing_count = existing.count or 0
        if existing_count >= num_questions:
            return {"generated": 0, "skipped_existing": existing_count, "errors": 0}
    except Exception:
        existing_count = 0

    # Fetch RAG context for the chapter
    try:
        rag_results = search_textbook_content(
            query=f"{subject} {chapter} concepts definitions formulas important topics",
            grade=grade,
            subject=subject,
            chapter=chapter,
            match_count=10,
        )
        rag_context = "\n\n".join(r.get("chunk_text", "") for r in rag_results)
    except Exception:
        rag_context = ""

    questions_to_generate = num_questions - existing_count

    # Step 1: Generate question list
    q_system = (
        "You are an education specialist who knows exactly what questions "
        "students ask about CBSE textbook chapters. "
        "Return ONLY a valid JSON array of question strings. No markdown."
    )
    q_prompt = f"""
Grade: {grade}
Subject: {subject}
Chapter: {chapter}

Textbook context:
{rag_context[:3000] if rag_context else "Standard CBSE textbook content for this chapter."}

Generate {questions_to_generate} distinct questions that Class {grade.replace("Grade ", "")} students
commonly ask about this chapter.

Requirements:
- Mix conceptual questions ("Why does...?", "What is the difference between...?")
- Include definition questions ("What is...?", "Define...?")
- Include application questions ("How does...?", "Give an example of...?")
- Include common misconception questions ("Is it true that...?")
- Questions should be answerable from the chapter content
- Each question must be different — no overlap
- Keep questions concise (under 20 words)

Return ONLY a JSON array: ["Question 1?", "Question 2?", ...]
"""

    try:
        raw_questions = ask_llm(
            q_system, q_prompt,
            username=username,
            feature="doubt_kb_prewarm",
            model=PREWARM_TEXT_MODEL,
        )
        raw_questions = raw_questions.strip()
        if raw_questions.startswith("```"):
            raw_questions = raw_questions.split("```")[1]
            if raw_questions.startswith("json"):
                raw_questions = raw_questions[4:]
        start = raw_questions.find("[")
        end = raw_questions.rfind("]")
        questions = json.loads(raw_questions[start:end + 1]) if start != -1 else []
    except Exception as exc:
        logger.warning("DKB prewarm question generation failed for %s/%s: %s", subject, chapter, exc)
        return {"generated": 0, "skipped_existing": existing_count, "errors": 1}

    # Step 2: Generate answer for each question and store
    generated = 0
    errors = 0

    a_system = (
        "You are an expert CBSE tutor. Answer the student's question clearly "
        "and concisely using the provided textbook context. "
        "Use student-appropriate language. Include key terms, formulas, or examples where relevant. "
        "Answer in 3-6 sentences unless a longer explanation is genuinely needed."
    )

    for question in questions[:questions_to_generate]:
        if not question or not isinstance(question, str):
            continue

        a_prompt = f"""
Grade: {grade}
Subject: {subject}
Chapter: {chapter}

Textbook context:
{rag_context[:2000] if rag_context else "Standard CBSE knowledge for this chapter."}

Student question: {question}

Answer the question clearly for a {grade} student.
"""

        try:
            answer = ask_llm(
                a_system, a_prompt,
                username=username,
                feature="doubt_kb_prewarm",
                model=PREWARM_TEXT_MODEL,
            )
            store_in_doubt_kb(
                question=question,
                answer=answer,
                grade=grade,
                subject=subject,
                chapter=chapter,
                mode=mode,
                board=board,
                source="prewarmed",
            )
            generated += 1
        except Exception as exc:
            logger.warning(
                "DKB prewarm answer failed for %s/%s/%s: %s",
                subject, chapter, question[:40], exc,
            )
            errors += 1

    return {
        "generated": generated,
        "skipped_existing": existing_count,
        "errors": errors,
    }


def prewarm_doubt_kb_for_grade(grade: str, mode: str = "CBSE") -> dict:
    """
    Pre-warm the DKB for all chapters of a grade that have RAG content.

    Iterates through the reviewed syllabus for the grade, skips chapters
    already fully covered, and generates Q&A for the rest.
    Safe to re-run — existing entries are skipped.
    """
    import time  # noqa: PLC0415
    from app.services.prewarm_service import get_syllabus_for_grade, has_rag_content_for_chapter  # noqa: PLC0415

    syllabus = get_syllabus_for_grade(grade)
    total_generated = 0
    total_skipped = 0
    total_errors = 0

    for current_mode, mode_data in syllabus.items():
        if current_mode != "CBSE":
            continue
        for subject, chapters in mode_data.items():
            for chapter in chapters:
                if not has_rag_content_for_chapter("CBSE", grade, subject, chapter):
                    continue
                result = prewarm_doubt_kb_for_chapter(
                    grade=grade,
                    subject=subject,
                    chapter=chapter,
                    mode=current_mode,
                )
                total_generated += result.get("generated", 0)
                total_skipped += result.get("skipped_existing", 0)
                total_errors += result.get("errors", 0)
                # Rate limit between chapters
                if result.get("generated", 0) > 0:
                    time.sleep(0.3)  # was 2.0 — gpt-4.1-nano allows 500+ RPM

    return {
        "grade": grade,
        "total_generated": total_generated,
        "total_skipped": total_skipped,
        "total_errors": total_errors,
    }
