"""
seed_principal_demo_data.py
─────────────────────────────────────────────────────────────────────────────
Populate the "testprincipal" account's school with realistic fictitious
teachers and students, so the Principal Dashboard has something to show and
demo instead of a completely empty roster.

Every account created here is clearly synthetic:
  - email domain: @example.test (matches the existing convention in
    app/services/student_learning_simulation_service.py)
  - user_metadata.is_demo_seed = True
  - "paid" students use subscription_plan="test_full_access" — the existing
    DB convention for a test-granted paid plan, never confused with a real
    Razorpay-paid account in any billing/revenue report

Idempotent: safe to rerun — skips any email that already has a profile.
Only ever touches profiles/rows it created (matched by the @example.test
email domain scoped to this specific school), never any real account.

Usage:
    cd backend
    .venv/bin/python scripts/seed_principal_demo_data.py
    .venv/bin/python scripts/seed_principal_demo_data.py --reset   # remove seeded rows
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.auth_service import admin_client  # noqa: E402

PRINCIPAL_EMAIL = "test@test.com"
EMAIL_DOMAIN = "example.test"
DEMO_PASSWORD = "test1234"

TEACHERS = [
    ("Anita Desai", "Mathematics"),
    ("Rajesh Kumar", "Science"),
    ("Priya Nair", "English"),
    ("Suresh Reddy", "Social Science"),
    ("Meena Iyer", "Hindi"),
    ("Arvind Menon", "Computer Science"),
]

STUDENTS_BY_GRADE = {
    5: ["Aarav Sharma", "Diya Patel", "Kabir Singh", "Ananya Gupta", "Vihaan Joshi"],
    6: ["Ishita Rao", "Arjun Mehta", "Saanvi Kapoor", "Rohan Verma", "Myra Choudhary"],
    7: ["Aditya Pillai", "Kavya Iyer", "Reyansh Nair", "Anika Bose", "Vivaan Malhotra"],
    8: ["Riya Sinha", "Aryan Chatterjee", "Prisha Reddy", "Dhruv Agarwal", "Navya Krishnan"],
    9: ["Sai Kulkarni", "Aarohi Bhatt", "Vedant Rana", "Ira Chauhan", "Krishna Menon"],
    10: ["Zara Khan", "Yash Trivedi", "Anaya Deshmukh", "Ritvik Saxena", "Tara Bhandari"],
    11: ["Aryan Kohli", "Meher Vora", "Shaurya Bakshi", "Ishaan Dutta", "Aadhya Ranganathan"],
    12: ["Kiaan Shetty", "Riya Bhattacharya", "Advik Sinha", "Nitya Ramesh", "Arnav Bhalla"],
}


def _get_test_school() -> dict:
    resp = (
        admin_client.table("profiles")
        .select("id, school_id")
        .eq("email", PRINCIPAL_EMAIL)
        .eq("role", "principal")
        .limit(1)
        .execute()
    )
    principal = (resp.data or [None])[0]
    if not principal or not principal.get("school_id"):
        raise SystemExit(f"No principal profile with school_id found for {PRINCIPAL_EMAIL}")

    school_resp = (
        admin_client.table("schools").select("*").eq("id", principal["school_id"]).limit(1).execute()
    )
    school = (school_resp.data or [None])[0]
    if not school:
        raise SystemExit("Principal's school_id does not match any school row.")
    return school


def _ensure_auth_user(email: str, username: str) -> str:
    existing = admin_client.table("profiles").select("id").eq("email", email).limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]

    res = admin_client.auth.admin.create_user({
        "email": email,
        "password": DEMO_PASSWORD,
        "email_confirm": True,
        "user_metadata": {"is_demo_seed": True, "display_name": username},
    })
    if not res.user:
        raise RuntimeError(f"Failed to create auth user for {email}")
    return res.user.id


def _seed_teachers(school_id: str) -> list[dict]:
    created = []
    for name, subject in TEACHERS:
        email = f"demo.teacher.{name.split()[0].lower()}@{EMAIL_DOMAIN}"
        uid = _ensure_auth_user(email, name)
        admin_client.table("profiles").upsert({
            "id": uid,
            "email": email,
            "username": name,
            "role": "teacher",
            "school_id": school_id,
            "account_status": "active",
        }, on_conflict="id").execute()
        created.append({"id": uid, "name": name, "subject": subject})
        print(f"  teacher: {name} ({subject}) — {email}")
    return created


def _seed_students(school_id: str) -> list[dict]:
    created = []
    i = 0
    for grade, names in STUDENTS_BY_GRADE.items():
        for name in names:
            email = f"demo.student.{name.split()[0].lower()}{grade}@{EMAIL_DOMAIN}"
            uid = _ensure_auth_user(email, name)

            is_paid = (i % 8) < 3  # ~37.5% paid, a realistic early-adoption split
            last_active = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 10))

            profile = {
                "id": uid,
                "email": email,
                "username": name,
                "role": "student",
                "school_id": school_id,
                "grade": f"Grade {grade}",
                "board": "CBSE",
                "account_status": "active",
                "access_cbse": is_paid,
                "subscription_plan": "test_full_access" if is_paid else "free",
                "subscription_expires_at": None,
            }
            admin_client.table("profiles").upsert(profile, on_conflict="id").execute()

            existing_sp = (
                admin_client.table("student_profiles")
                .select("profile_id")
                .eq("profile_id", uid)
                .limit(1)
                .execute()
            )
            sp_fields = {"username": name, "last_active_date": last_active.date().isoformat()}
            if existing_sp.data:
                admin_client.table("student_profiles").update(sp_fields).eq("profile_id", uid).execute()
            else:
                admin_client.table("student_profiles").insert({**sp_fields, "profile_id": uid}).execute()

            created.append({"id": uid, "name": name, "grade": grade, "is_paid": is_paid})
            print(f"  student: {name} (Grade {grade}, {'paid' if is_paid else 'free'}) — {email}")
            i += 1
    return created


def _seed_assignments(teachers: list[dict], students: list[dict]) -> None:
    for idx, student in enumerate(students):
        teacher = teachers[idx % len(teachers)]
        admin_client.table("teacher_student_assignments").insert({
            "teacher_id": teacher["id"],
            "student_id": student["id"],
            "grade": f"Grade {student['grade']}",
            "subject": teacher["subject"],
            "section": "Section A",
        }).execute()
    print(f"  linked {len(students)} students across {len(teachers)} teachers")


def _seed_reward_history(school: dict, principal_id: str) -> None:
    existing = (
        admin_client.table("school_reward_redemptions")
        .select("id")
        .eq("school_id", school["id"])
        .limit(1)
        .execute()
    )
    if existing.data:
        return
    admin_client.table("school_reward_redemptions").insert({
        "school_id": school["id"],
        "principal_id": principal_id,
        "reward_key": "bronze_support",
        "reward_label": "Standard support line",
        "tier_at_redemption": "bronze",
        "status": "fulfilled",
    }).execute()
    print("  seeded one fulfilled reward redemption (bronze_support)")


def reset(school: dict) -> None:
    resp = (
        admin_client.table("profiles")
        .select("id, email")
        .eq("school_id", school["id"])
        .like("email", f"demo.%@{EMAIL_DOMAIN}")
        .execute()
    )
    demo_profiles = resp.data or []
    print(f"Removing {len(demo_profiles)} demo profiles from {school['name']}...")
    for p in demo_profiles:
        admin_client.table("teacher_student_assignments").delete().or_(
            f"teacher_id.eq.{p['id']},student_id.eq.{p['id']}"
        ).execute()
        admin_client.table("student_profiles").delete().eq("profile_id", p["id"]).execute()
        admin_client.table("profiles").delete().eq("id", p["id"]).execute()
        try:
            admin_client.auth.admin.delete_user(p["id"])
        except Exception as e:
            print(f"  WARNING: could not delete auth user {p['email']}: {e}")
    admin_client.table("school_reward_redemptions").delete().eq("school_id", school["id"]).execute()
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Remove previously seeded demo data instead")
    args = parser.parse_args()

    school = _get_test_school()
    print(f"Target school: {school['name']} ({school['id']})")

    if args.reset:
        reset(school)
        return

    print("Seeding teachers...")
    teachers = _seed_teachers(school["id"])
    print("Seeding students...")
    students = _seed_students(school["id"])
    print("Linking students to teachers...")
    _seed_assignments(teachers, students)
    print("Seeding reward redemption history...")
    _seed_reward_history(school, school["principal_id"])

    paid_count = sum(1 for s in students if s["is_paid"])
    print()
    print(f"Done: {len(teachers)} teachers, {len(students)} students "
          f"({paid_count} paid / {len(students) - paid_count} free) seeded for {school['name']}.")


if __name__ == "__main__":
    main()
