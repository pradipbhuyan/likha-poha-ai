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

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_url = os.getenv(
    "SUPABASE_GRADE_1112_URL",
    "https://sjfjyzaaypfzyfhhggqw.supabase.co",
)
_key = os.getenv(
    "SUPABASE_GRADE_1112_SERVICE_KEY",
    # Fallback hardcoded only for local dev — always set the env var in production.
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqZmp5emFheXBmenlmaGhnZ3F3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjE2NDM2MywiZXhwIjoyMDk3NzQwMzYzfQ.VNbQ2cHF0sPSoR7zy5uVi993SHXtLomK8eJkeu6LwTs",
)

# Service-role client — used by all backend services to bypass RLS
grade_1112_client = create_client(_url, _key)

# Convenience alias used by the grade router
supabase_1112 = grade_1112_client
