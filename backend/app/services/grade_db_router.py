"""
Grade DB Router
===============
Returns the correct Supabase client based on the student grade.

  Grade 1–10  →  primary Supabase   (user data + CBSE 1-10 RAG)
  Grade 11    →  second Supabase    (Grade 11 & 12 RAG / DKB / cache)
  Grade 12    →  second Supabase    (Grade 11 & 12 RAG / DKB / cache)

Why this split exists: it is a temporary cost-deferral measure, not a
deliberate sharding architecture. Both projects are on Supabase's free tier;
splitting Grade 11/12 content onto a second project keeps each project under
the free-tier row/storage limits until Likha Poha AI has paying subscribers.
The intended long-term fix is to upgrade to a paid Supabase plan and merge
both projects back into one — this split should not be treated as permanent
architecture to build further sharding/routing logic around. Every content
query MUST go through get_content_db() below rather than a bare Supabase
client, or it will silently read/write the wrong project for Grade 11/12.

Usage in any service:
    from app.services.grade_db_router import get_content_db

    db = get_content_db(grade)
    db.table("rag_documents").select("*").execute()
"""

# Grade 11/12 content has been migrated to the primary Supabase project.
# The secondary project (grade_1112_client) is kept for backward compatibility
# during the transition but all NEW Grade 11/12 board_sample_papers writes
# and reads now go to primary. Update this set to re-enable secondary routing
# if needed during rollback.
_GRADE_1112 = {"grade 11"}   # Grade 12 removed — now served by primary DB


def get_content_db(grade: str | None = None):
    """
    Return the Supabase client that holds RAG / DKB / lesson cache
    / question bank content for the given grade.

    Falls back to the primary DB for any unrecognised grade value, and for
    Grade 11/12 when SUPABASE_GRADE_1112_URL / SUPABASE_GRADE_1112_SERVICE_KEY
    are not set (e.g. during key rotation) — grade_1112_client is None in that
    case (see supabase_grade_1112_client.py), so services degrade gracefully
    rather than crashing. Pre-warmed Grade 11/12 cache won't be found (cache
    miss), but LLM generation still works normally until keys are restored.
    """
    if grade and grade.strip().lower() in _GRADE_1112:
        from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
        if grade_1112_client is not None:
            return grade_1112_client
        # Credentials missing/rotating — fall through to the primary DB below.

    # Primary Supabase — Grade 1-10 + all auth/user data
    from app.services.auth_service import admin_client
    return admin_client


def is_grade_1112(grade: str | None) -> bool:
    """True when the grade belongs to the second Supabase project."""
    return bool(grade and grade.strip().lower() in _GRADE_1112)
