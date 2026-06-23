"""
Supabase client for Grade 11 & 12 content.

This second Supabase project holds all RAG chunks, DKB entries,
lesson cache, and question bank rows for Grade 11 & 12 CBSE — keeping
them separate from the primary project that stores Grade 1-10 content
and all user/auth data.

Environment variables required (set in Render + .env):
    SUPABASE_GRADE_1112_URL          e.g. https://sjfjyzaaypfzyfhhggqw.supabase.co
    SUPABASE_GRADE_1112_SERVICE_KEY  service_role key (bypasses RLS for backend writes)
"""

import logging
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_logger = logging.getLogger("likhapoha.supabase_1112")

_url = os.getenv(
    "SUPABASE_GRADE_1112_URL",
    "https://sjfjyzaaypfzyfhhggqw.supabase.co",
)
_key = os.getenv(
    "SUPABASE_GRADE_1112_SERVICE_KEY",
    # Fallback hardcoded only for local dev — always set the env var in production.
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqZmp5emFheXBmenlmaGhnZ3F3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjE2NDM2MywiZXhwIjoyMDk3NzQwMzYzfQ.VNbQ2cHF0sPSoR7zy5uVi993SHXtLomK8eJkeu6LwTs",
)

_logger.info("Grade 11/12 Supabase client initialising → %s", _url)

# Service-role client — used by all backend services to bypass RLS
grade_1112_client = create_client(_url, _key)
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
        "Grade 11/12 connectivity test FAILED (check SUPABASE_GRADE_1112_SERVICE_KEY in Render): %s",
        _exc,
    )

# Convenience alias used by the grade router
supabase_1112 = grade_1112_client
