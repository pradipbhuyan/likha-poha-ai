"""
Supabase client for Grade 11 & 12 content.

This second Supabase project holds all RAG chunks, DKB entries,
lesson cache, and question bank rows for Grade 11 & 12 CBSE — keeping
them separate from the primary project that stores Grade 1-10 content
and all user/auth data.

Environment variables required (set in Railway / Render / .env):
    SUPABASE_GRADE_1112_URL          e.g. https://sjfjyzaaypfzyfhhggqw.supabase.co
    SUPABASE_GRADE_1112_SERVICE_KEY  service_role key (bypasses RLS for backend writes)
"""

import logging
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_logger = logging.getLogger("likhapoha.supabase_1112")

_url = os.getenv("SUPABASE_GRADE_1112_URL")
_key = os.getenv("SUPABASE_GRADE_1112_SERVICE_KEY")

if not _url or not _key:
    # Warn but do NOT exit — allows the test suite and non-Grade-11/12 routes
    # to run without these vars.  Any actual call to grade_1112_client will
    # raise a clear RuntimeError at that point rather than crashing startup.
    _logger.warning(
        "SUPABASE_GRADE_1112_URL or SUPABASE_GRADE_1112_SERVICE_KEY is not set. "
        "Grade 11/12 features will be unavailable. "
        "Add these variables to your Railway / Render environment."
    )
    grade_1112_client = None  # type: ignore[assignment]
    supabase_1112 = None  # type: ignore[assignment]
else:
    _logger.info("Grade 11/12 Supabase client initialising → %s", _url)
    # Service-role client — used by all backend services to bypass RLS
    grade_1112_client = create_client(_url, _key)
    supabase_1112 = grade_1112_client
    _logger.info("Grade 11/12 Supabase client created successfully.")

    # Quick connectivity test — log but never raise so startup is not blocked
    try:
        _test = grade_1112_client.table("rag_documents").select("id").limit(1).execute()
        _logger.info(
            "Grade 11/12 connectivity test: %d row(s) returned from rag_documents.",
            len(_test.data or []),
        )
    except Exception as _exc:  # noqa: BLE001
        _logger.error(
            "Grade 11/12 connectivity test FAILED (check SUPABASE_GRADE_1112_SERVICE_KEY in Railway/Render): %s",
            _exc,
        )
