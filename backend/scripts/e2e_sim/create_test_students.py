#!/usr/bin/env python3
"""
Create one test student per grade (Grade 5-12) with full CBSE access, then
sign in as each to obtain a real access token for driving the E2E student
journey simulation (lesson launch, doubts, mock tests) through the actual
HTTP API surface, the same way the frontend would.

Writes account + token info to scripts/e2e_sim/students.json.

Idempotent: if a student with the expected email already exists, it signs in
instead of re-creating it (so this can be re-run safely).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from supabase import create_client  # noqa: E402
from app.services.auth_service import admin_client, SUPABASE_URL  # noqa: E402
import os  # noqa: E402

GRADES = [f"Grade {g}" for g in range(5, 13)]
PASSWORD = "E2ESimTest#2026"
OUT_PATH = Path(__file__).resolve().parent / "students.json"

SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_ANON_KEY:
    raise SystemExit("SUPABASE_ANON_KEY missing from environment")

anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def email_for(grade: str) -> str:
    n = grade.split()[-1]
    return f"e2esim.grade{n}@example.com"


def username_for(grade: str) -> str:
    n = grade.split()[-1]
    return f"E2ESim-Grade{n}"


def find_existing_auth_user(email: str):
    page = 1
    while True:
        resp = admin_client.auth.admin.list_users(page=page, per_page=200)
        users = resp if isinstance(resp, list) else getattr(resp, "users", resp)
        if not users:
            return None
        for u in users:
            if (getattr(u, "email", None) or "").lower() == email.lower():
                return u
        if len(users) < 200:
            return None
        page += 1


def ensure_student(grade: str) -> dict:
    email = email_for(grade)
    username = username_for(grade)

    existing = find_existing_auth_user(email)
    if existing:
        user_id = existing.id
        print(f"  {grade}: auth user already exists ({user_id})")
    else:
        created = admin_client.auth.admin.create_user({
            "email": email,
            "password": PASSWORD,
            "email_confirm": True,
        })
        user_id = created.user.id
        print(f"  {grade}: created auth user ({user_id})")

    existing_profile = (
        admin_client.table("profiles").select("id,username,grade").eq("id", user_id).execute()
    )
    if not existing_profile.data:
        profile = {
            "id": user_id,
            "email": email,
            "username": username,
            "role": "student",
            "parent_id": None,
            "family_id": None,
            "grade": grade,
            "board": "CBSE",
            "account_status": "active",
            "subscription_plan": "test_full_access",
            "access_cbse": True,
            "cbse_subjects": [],  # empty = all subjects, per subject_access_service.py
            "daily_token_limit": 5_000_000,
            "monthly_token_limit": 100_000_000,
            "ai_model_preference": "default",
        }
        admin_client.table("profiles").insert(profile).execute()
        print(f"  {grade}: created profile")
    else:
        # Make sure an existing profile still has full access (idempotent re-run).
        admin_client.table("profiles").update({
            "grade": grade,
            "board": "CBSE",
            "account_status": "active",
            "access_cbse": True,
            "cbse_subjects": [],
            "daily_token_limit": 5_000_000,
            "monthly_token_limit": 100_000_000,
        }).eq("id", user_id).execute()
        print(f"  {grade}: profile already existed, refreshed access flags")

    # Sign in as the student (anon-key client) to get a real bearer token,
    # exactly as the frontend login flow would.
    auth_resp = anon_client.auth.sign_in_with_password({"email": email, "password": PASSWORD})
    access_token = auth_resp.session.access_token

    return {
        "grade": grade,
        "username": username,
        "email": email,
        "user_id": user_id,
        "access_token": access_token,
    }


def main() -> None:
    students = []
    for grade in GRADES:
        students.append(ensure_student(grade))

    OUT_PATH.write_text(json.dumps(students, indent=2), encoding="utf-8")
    print(f"\nWrote {len(students)} student accounts + tokens to {OUT_PATH}")


if __name__ == "__main__":
    main()
