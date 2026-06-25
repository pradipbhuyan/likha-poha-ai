"""
Grade DB Router
===============
Returns the correct Supabase client based on the student grade.

  Grade 1–10  →  primary Supabase   (user data + CBSE 1-10 RAG)
  Grade 11    →  second Supabase    (Grade 11 & 12 RAG / DKB / cache)
  Grade 12    →  second Supabase    (Grade 11 & 12 RAG / DKB / cache)

Usage in any service:
    from app.services.grade_db_router import get_content_db

    db = get_content_db(grade)
    db.table("rag_documents").select("*").execute()
"""

_GRADE_1112 = {"grade 11", "grade 12"}


def get_content_db(grade: str | None = None):
    """
    Return the Supabase client that holds RAG / DKB / lesson cache
    / question bank content for the given grade.

    Falls back to the primary DB for any unrecognised grade value.

    When SUPABASE_GRADE_1112_URL / SUPABASE_GRADE_1112_SERVICE_KEY are not
    set (e.g. during key rotation), the Grade 11/12 client calls sys.exit(1).
    We catch that SystemExit here and fall back to the primary DB so all
    services (lesson generation, RAG search, cache) degrade gracefully rather
    than crashing. Pre-warmed Grade 11/12 cache won't be found (cache miss),
    but LLM generation will work normally until keys are rotated.
    """
    if grade and grade.strip().lower() in _GRADE_1112:
        try:
            from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
            return grade_1112_client
        except SystemExit:
            # Grade 11/12 Supabase credentials missing or being rotated.
            # Fall through to primary DB — lesson generation still works via LLM.
            pass
        except Exception:
            pass

    # Primary Supabase — Grade 1-10 + all auth/user data
    from app.services.auth_service import admin_client
    return admin_client


def is_grade_1112(grade: str | None) -> bool:
    """True when the grade belongs to the second Supabase project."""
    return bool(grade and grade.strip().lower() in _GRADE_1112)
