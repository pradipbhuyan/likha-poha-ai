"""Destructive-by-design deployed smoke test using disposable accounts only.

Required environment:
  TENANT_SMOKE_ALLOW_WRITES=1
  TENANT_SMOKE_API_URL=https://staging-api.example
  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

Production is refused unless TENANT_SMOKE_ALLOW_PRODUCTION=1 is also set.
All created auth users and rows are removed in a finally block.
"""
from __future__ import annotations

import os
import secrets
import sys
import uuid

import httpx


def _required(name: str) -> str:
    value = os.getenv(name, "").strip().rstrip("/")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    if os.getenv("TENANT_SMOKE_ALLOW_WRITES") != "1":
        raise RuntimeError("Refusing writes: set TENANT_SMOKE_ALLOW_WRITES=1")

    api_url = _required("TENANT_SMOKE_API_URL")
    if "likhapoha.in" in api_url and os.getenv("TENANT_SMOKE_ALLOW_PRODUCTION") != "1":
        raise RuntimeError("Refusing production: set TENANT_SMOKE_ALLOW_PRODUCTION=1 explicitly")

    supabase_url = _required("SUPABASE_URL")
    anon_key = _required("SUPABASE_ANON_KEY")
    service_key = _required("SUPABASE_SERVICE_ROLE_KEY")
    run = uuid.uuid4().hex[:12]
    password = f"Smoke-{secrets.token_urlsafe(18)}!"
    users: list[str] = []
    profile_ids: list[str] = []

    admin_headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    def create_user(label: str, role: str, parent_id: str | None = None) -> tuple[str, str, str]:
        email = f"tenant-smoke-{run}-{label}@example.test"
        response = httpx.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=admin_headers,
            json={"email": email, "password": password, "email_confirm": True},
            timeout=30,
        )
        response.raise_for_status()
        user_id = response.json()["id"]
        users.append(user_id)
        username = f"tenant.smoke.{run}.{label}"
        profile = {
            "id": user_id, "email": email, "username": username, "role": role,
            "account_status": "active",
        }
        if parent_id:
            profile["parent_id"] = parent_id
        saved = httpx.post(
            f"{supabase_url}/rest/v1/profiles",
            headers=admin_headers, json=profile, timeout=30,
        )
        saved.raise_for_status()
        profile_ids.append(user_id)
        return user_id, email, username

    def token(email: str) -> str:
        response = httpx.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password}, timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def api_get(path: str, access_token: str) -> httpx.Response:
        return httpx.get(
            f"{api_url}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )

    try:
        parent_id, parent_email, _ = create_user("parent", "parent")
        child_id, _, child_username = create_user("child", "student", parent_id=parent_id)
        teacher_id, teacher_email, _ = create_user("teacher", "teacher")
        _, unassigned_email, _ = create_user("unassigned", "teacher")

        progress = {
            "profile_id": child_id, "username": child_username, "grade": "Grade 8",
            "mode": "CBSE", "subject": "Science", "chapter": f"Smoke {run}",
            "current_step_index": 1, "highest_unlocked_step": 1, "completed": True,
            "last_lesson": "Disposable tenant smoke record", "step_lessons": {},
        }
        test = {
            "profile_id": child_id, "username": child_username, "grade": "Grade 8",
            "mode": "CBSE", "subject": "Science", "chapter": f"Smoke {run}",
            "percentage": 80, "raw_score": 8, "final_score": 8, "max_score": 10,
            "difficulty": "medium", "wrong_count": 2, "penalty": 0,
        }
        assignment = {
            "teacher_id": teacher_id, "student_id": child_id,
            "subject": "Science", "grade": "Grade 8",
        }
        for table, row in (
            ("student_progress", progress),
            ("test_history", test),
            ("teacher_student_assignments", assignment),
        ):
            response = httpx.post(
                f"{supabase_url}/rest/v1/{table}", headers=admin_headers, json=row, timeout=30,
            )
            response.raise_for_status()

        parent_view = api_get(f"/api/parent/children/{child_id}/analytics", token(parent_email))
        parent_view.raise_for_status()
        parent_json = parent_view.json()
        assert parent_json["mock_tests"]["total_tests"]["value"] == 1, parent_json
        assert parent_json["progress"]["completed_chapters"]["value"] == 1, parent_json

        teacher_view = api_get(f"/api/teacher/students/{child_id}", token(teacher_email))
        teacher_view.raise_for_status()
        assert teacher_view.json()["learning"]["mock_tests_completed"] == 1, teacher_view.text

        denied = api_get(f"/api/teacher/students/{child_id}", token(unassigned_email))
        assert denied.status_code == 403, denied.text
        print("PASS: parent/assigned-teacher visibility and unassigned-teacher isolation")
        return 0
    finally:
        # Delete owned data explicitly before auth cleanup so this remains safe
        # even if a staging database has not yet applied ON DELETE CASCADE.
        for table in ("teacher_student_assignments", "student_progress", "test_history"):
            for column in ("student_id", "profile_id"):
                if profile_ids:
                    httpx.delete(
                        f"{supabase_url}/rest/v1/{table}?{column}=in.({','.join(profile_ids)})",
                        headers=admin_headers, timeout=30,
                    )
        for user_id in reversed(users):
            httpx.delete(
                f"{supabase_url}/auth/v1/admin/users/{user_id}",
                headers=admin_headers, timeout=30,
            )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
