"""
Grade DB Router
===============
Returns the Supabase client that holds RAG / DKB / lesson cache / question
bank content for a given grade.

All grades now route to the primary Supabase project. Grade 11/12 content
used to live on a second, free-tier Supabase project (see
supabase_grade_1112_client.py) as a temporary cost-deferral measure; that
content has since been migrated onto primary (see
backend/migrations/20260723_migrate_grade1112_content_to_primary.sql) and
this router now always returns the primary client. is_grade_1112() is kept
for other grade-based business logic (e.g. the stream field) that has
nothing to do with DB routing.

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
    """Return the Supabase client that holds RAG / DKB / lesson cache / question bank content."""
    from app.services.auth_service import admin_client
    return admin_client


def is_grade_1112(grade: str | None) -> bool:
    """True when the grade belongs to the second Supabase project."""
    return bool(grade and grade.strip().lower() in _GRADE_1112)
