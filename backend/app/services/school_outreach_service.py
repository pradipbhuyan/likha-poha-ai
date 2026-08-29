"""
school_outreach_service.py — CBSE principal outreach campaign.

State lives in Supabase (school_outreach_principals — see
migrations/20260828_school_outreach.sql), not a script-local file, so the
admin console (Admin Control -> School Outreach) can browse, filter, select,
and trigger sends directly.

Sending is deliberately NOT app.services.email_service._send_via_resend():
that function reads its `reply_to` from a global EMAIL_REPLY_TO env var, which
would silently redirect replies to every transactional email the app sends
(welcome, password reset, digests) if set for this campaign. This module
takes reply_to as an explicit argument instead, and never touches the shared
transactional send path. It does reuse email_service._feature_table() — a
pure, stateless icon-row renderer with no coupling to the shell/footer — so
the feature lists render identically to the real welcome email.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from app.services.auth_service import admin_client
from app.services.email_service import _feature_table
from app.services.logger_service import get_logger

_log = get_logger(__name__)

RESEND_URL = "https://api.resend.com/emails"

_BRAND_COLOR = "#6366f1"
_LOGO_URL = "https://likhapoha.in/favicon.png"

FROM_ADDRESS = os.getenv("SCHOOL_OUTREACH_FROM", "principals@likhapoha.in")
SENDER_NAME = os.getenv("SCHOOL_OUTREACH_SENDER_NAME", "Likha Poha AI Schools")
REPLY_TO = os.getenv("SCHOOL_OUTREACH_REPLY_TO", "likhapohaaischool@gmail.com")
CTA_URL = os.getenv("FRONTEND_URL", "https://likhapoha.in")
SEND_DELAY_SECONDS = 2.0  # spread sends out rather than firing requests back to back

TABLE = "school_outreach_principals"


class SendResult:
    def __init__(self, success: bool, detail: str = ""):
        self.success = success
        self.detail = detail


# ─────────────────────────────────────────────────────────────────────────────
# Branded email shell + content (identical to the approved template)
# ─────────────────────────────────────────────────────────────────────────────

def _campaign_email_shell(body_html: str, cta_url: str, cta_label: str) -> str:
    """Same visual brand shell as the product's welcome email, with a campaign-specific footer."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Likha Poha AI</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1e293b">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
    <tr>
      <td align="center" style="padding:32px 16px">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0"
               style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;
                      box-shadow:0 4px 24px rgba(99,102,241,0.10);overflow:hidden">

          <!-- Header with logo -->
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
                       padding:24px 32px 22px">
              <img src="{_LOGO_URL}" alt="Likha Poha AI" width="52" height="52"
                   style="display:block;margin:0 auto 10px;border-radius:12px;
                          border:2px solid rgba(255,255,255,0.28)" />
              <p style="margin:0;font-size:22px;font-weight:900;color:#ffffff;
                        letter-spacing:-0.02em">Likha Poha AI</p>
              <p style="margin:5px 0 0;font-size:13px;color:#c4b5fd;font-weight:500">
                India's AI-Powered CBSE Tutor &middot; Grades 5&ndash;12
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 36px">
              {body_html}
              <div style="margin-top:32px;text-align:center">
                <a href="{cta_url}"
                   style="display:inline-block;padding:14px 32px;
                          background:linear-gradient(135deg,#4f46e5,#7c3aed);
                          color:#ffffff;text-decoration:none;font-weight:800;
                          font-size:15px;border-radius:10px;
                          box-shadow:0 6px 20px rgba(99,102,241,0.28)">
                  {cta_label}
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8fafc;padding:20px 36px;border-top:1px solid #e5e7eb">
              <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;line-height:1.6">
                Likha Poha AI &middot; CBSE Learning Platform for Grades 5&ndash;12<br>
                Email us at
                <a href="mailto:likhapohaaischool@gmail.com" style="color:{_BRAND_COLOR};text-decoration:none">likhapohaaischool@gmail.com</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _stat_badges(stats: list[tuple[str, str]]) -> str:
    cell_width = 100 // len(stats)
    cells = "".join(
        f'''<td width="{cell_width}%" align="center" style="padding:4px">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                 style="background:#f5f3ff;border:1px solid #ede9fe;border-radius:10px">
            <tr><td align="center" style="padding:10px 4px">
              <div style="font-size:18px;font-weight:900;color:#6d28d9;line-height:1.2">{value}</div>
              <div style="font-size:10.5px;color:#7c3aed;font-weight:600;text-transform:uppercase;letter-spacing:.03em">{label}</div>
            </td></tr>
          </table>
        </td>'''
        for value, label in stats
    )
    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:4px 0 22px">
  <tr>{cells}</tr>
</table>"""


def _section_title(icon: str, text: str, color: str) -> str:
    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:26px 0 4px">
  <tr>
    <td style="border-bottom:3px solid {color};padding-bottom:6px">
      <span style="font-size:16px;font-weight:800;color:#0f172a">{icon} {text}</span>
    </td>
  </tr>
</table>"""


def _trust_strip(items: list[tuple[str, str, str]]) -> str:
    cell_width = 100 // len(items)
    cells = "".join(
        f'''<td width="{cell_width}%" valign="top" style="padding:4px">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                 style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;height:100%">
            <tr><td style="padding:12px 12px">
              <div style="font-size:18px;margin-bottom:4px">{icon}</div>
              <div style="font-size:12.5px;font-weight:700;color:#0f172a;margin-bottom:3px">{title}</div>
              <div style="font-size:11.5px;color:#64748b;line-height:1.5">{desc}</div>
            </td></tr>
          </table>
        </td>'''
        for icon, title, desc in items
    )
    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:10px 0 4px">
  <tr>{cells}</tr>
</table>"""


_STUDENT_FEATURES = [
    ("📚", "AI Lessons", "Every chapter explained step by step, in simple words — like a patient teacher who repeats things until you get it."),
    ("💬", "Ask-a-Doubt", "Ask any question about what you're studying and get an answer right away — no waiting."),
    ("📝", "Practice Tests", "Thousands of practice questions that mark themselves instantly."),
    ("🔢", "Formula Sheet", "Every formula in one place with simple tips to remember them."),
    ("🎓", "Extra-Tough Practice", "Harder bonus questions for students who want an extra challenge."),
    ("📄", "Real Exam Papers", "Actual past exam papers from the last 10 years, with correct answers."),
    ("🎯", "Big Exam Training Camp", "Extra practice for students aiming at big entrance exams — JEE, NEET, CUET, SAT, IELTS &amp; TOEFL."),
    ("🏆", "Points, Streaks &amp; Rankings", "Earn points and see your rank in class as you study — like a video game score, but for learning."),
    ("📈", "My Progress", "Simple charts that show if you're getting better over time."),
    ("📱", "Works On Any Phone", "Opens straight in the browser — nothing to download or install."),
]

_PARENT_FEATURES = [
    ("👪", "Parent Dashboard", "One screen that shows how your child is doing — what they studied, test scores, and anything that needs attention."),
    ("⚠️", "Early Warning on Weak Topics", "Quietly flags which topic a child is struggling with — before a small problem becomes a big one."),
    ("👥", "Manage the Whole Family", "Add more than one child — each gets their own profile and progress, kept separate."),
    ("🗂", "Detailed Child Profile", "What they've studied, how their tests went, and a report you can print."),
    ("📊", "Progress Charts", "Simple graphs showing whether scores are going up or down, subject by subject."),
    ("🔔", "Friendly Reminders", "Gentle updates split into what needs attention now and what's simply good news."),
    ("🖨", "Printable Report Card", "A shareable summary of a child's learning — handy for family or school."),
    ("🎓", "Every Grade Covered", "Works all the way from Grade 5 to Grade 12."),
]

_TEACHER_FEATURES = [
    ("🏫", "Teacher Dashboard", "One home screen for the whole class — like a car dashboard, but for how students are doing."),
    ("🚨", "Who Needs Help First", "Sorts students into who needs help urgently, who needs a little help, and who's doing fine."),
    ("👥", "Students &amp; Classrooms", "The full class list in one place, organised into classrooms, with one click into any student's profile."),
    ("✉️", "Invitations", "Invite a student to join a class by entering their name and email."),
    ("📝", "Create Lesson Plans", "The AI writes a full lesson plan — what to teach, in what order, and how to check understanding."),
    ("🖨", "Create Test Paper", "The AI puts together a test paper with an answer key, ready to print."),
    ("🎧", "Listen to Lecture", "The AI reads the lesson plan out loud, so a teacher can rehearse before walking into class."),
    ("📊", "Student Analytics", "Simple charts showing how each student is scoring over time."),
    ("🗂", "Student Profile", "A detailed page per student — progress, test scores, and private notes only the teacher sees."),
]

_TRUST_ITEMS = [
    ("🔒", "Stays On Topic", "The AI only talks schoolwork — it blocks hateful, political, or unrelated content automatically."),
    ("🔑", "Safe Google Sign-In", "We only ever see a user's name, email, and photo — nothing else, never sold."),
    ("💳", "Safe Payments", "All payments go through Razorpay, a trusted, widely-used Indian payment service."),
]

_STAT_BADGES = [
    ("900+", "Chapters"),
    ("8", "Grades (5-12)"),
    ("12+", "Subjects"),
    ("140,000+", "Questions"),
]


def build_principal_email_html(principal_name: str, school_name: str, cta_url: str) -> str:
    first_name = (principal_name or "Principal").strip().split()[0] if principal_name else "Principal"
    school_clean = (school_name or "your school").strip()

    intro = f"""
<p style="margin:0 0 14px;font-size:15px;line-height:1.7">
  Dear {first_name},
</p>
<p style="margin:0 0 6px;font-size:15px;line-height:1.7">
  I'm reaching out from <strong>Likha Poha AI</strong>, an AI-powered CBSE
  learning platform built from actual NCERT textbooks. Through methodical
  revision, practice tests, and homework support, it helps your students
  excel in their studies &mdash; augmenting what your teachers teach in the
  classroom, not replacing it. A full overview of what it offers everyone at
  {school_clean} &mdash; and what it offers you, as Principal.
</p>"""

    stats = _stat_badges(_STAT_BADGES)
    students = _section_title("🎓", "For Students", "#7c3aed") + _feature_table(_STUDENT_FEATURES)
    parents = _section_title("👪", "For Parents", "#059669") + _feature_table(_PARENT_FEATURES)
    teachers = _section_title("🏫", "For Your Teachers", "#2563eb") + _feature_table(_TEACHER_FEATURES)
    trust = _section_title("🛡", "Safety &amp; Trust", "#64748b") + _trust_strip(_TRUST_ITEMS)

    principal = f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
       style="margin:26px 0 4px;background:linear-gradient(135deg,#fffbeb,#fef3c7);
              border:1px solid #fde68a;border-radius:12px">
  <tr>
    <td style="padding:18px 20px">
      <div style="font-size:16px;font-weight:800;color:#92400e;margin-bottom:8px">
        🏛 And for you, as Principal
      </div>
      <p style="margin:0;font-size:13.5px;line-height:1.7;color:#78350f">
        A dedicated <strong>Principal Command Center</strong> for {school_clean}
        &mdash; one dashboard to see every teacher and student already on the
        platform, track free-vs-paid adoption at a glance, and unlock
        school-level rewards (free teacher seats, printed materials,
        recognition) as adoption grows. It never changes what a student,
        parent, or teacher can already do &mdash; it's purely an oversight
        layer for you.
      </p>
    </td>
  </tr>
</table>"""

    closing = f"""
<p style="margin:22px 0 0;font-size:15px;line-height:1.7">
  I'd love to give your team a demo of the platform and set it up for
  {school_clean} personally &mdash; just reply to this email and I'll take
  it from there.
</p>"""

    body = intro + stats + students + parents + teachers + trust + principal + closing
    return _campaign_email_shell(body_html=body, cta_url=cta_url, cta_label="Visit Likha Poha AI")


def _text_feature_lines(features: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"- {title}: {desc}" for _icon, title, desc in features).replace("&amp;", "&")


def build_principal_email_text(principal_name: str, school_name: str, cta_url: str) -> str:
    first = (principal_name or "Principal").strip().split()[0] if principal_name else "Principal"
    school = (school_name or "your school").strip()
    return f"""Dear {first},

I'm reaching out from Likha Poha AI, an AI-powered CBSE learning platform built
from actual NCERT textbooks (900+ chapters, Grades 5-12, 12+ subjects,
140,000+ practice questions). Through methodical revision, practice tests, and
homework support, it helps your students excel in their studies -- augmenting
what your teachers teach in the classroom, not replacing it. A full overview
of what it offers everyone at {school} -- and what it offers you, as
Principal.

FOR STUDENTS
{_text_feature_lines(_STUDENT_FEATURES)}

FOR PARENTS
{_text_feature_lines(_PARENT_FEATURES)}

FOR YOUR TEACHERS
{_text_feature_lines(_TEACHER_FEATURES)}

SAFETY & TRUST
{_text_feature_lines(_TRUST_ITEMS)}

AND FOR YOU, AS PRINCIPAL
A dedicated Principal Command Center for {school} -- one dashboard to see every
teacher and student already on the platform, track free-vs-paid adoption at a
glance, and unlock school-level rewards (free teacher seats, printed materials,
recognition) as adoption grows. It never changes what a student, parent, or
teacher can already do -- it's purely an oversight layer for you.

I'd love to give your team a demo of the platform and set it up for {school}
personally -- just reply to this email and I'll take it from there.

{cta_url}

Email us at likhapohaaischool@gmail.com
"""


def build_reminder_email_html(principal_name: str, school_name: str, cta_url: str) -> str:
    first_name = (principal_name or "Principal").strip().split()[0] if principal_name else "Principal"
    school_clean = (school_name or "your school").strip()

    body = f"""
<p style="margin:0 0 16px;font-size:15px;line-height:1.7">
  Dear {first_name},
</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.7">
  Just following up on my note last week about <strong>Likha Poha AI</strong>
  for {school_clean} — an AI-powered CBSE learning platform for students,
  parents, and teachers, with a dedicated Principal Command Center for
  school-wide oversight.
</p>
<p style="margin:0;font-size:15px;line-height:1.7">
  I'd still love to give your team a quick demo and set it up for
  {school_clean} personally. Just reply to this email whenever suits you
  &mdash; and if now isn't the right time, no worries at all.
</p>"""
    return _campaign_email_shell(body_html=body, cta_url=cta_url, cta_label="Visit Likha Poha AI")


def build_reminder_email_text(principal_name: str, school_name: str, cta_url: str) -> str:
    first = (principal_name or "Principal").strip().split()[0] if principal_name else "Principal"
    school = (school_name or "your school").strip()
    return f"""Dear {first},

Just following up on my note last week about Likha Poha AI for {school} -- an
AI-powered CBSE learning platform for students, parents, and teachers, with a
dedicated Principal Command Center for school-wide oversight.

I'd still love to give your team a quick demo and set it up for {school}
personally. Just reply to this email whenever suits you -- and if now isn't
the right time, no worries at all.

{cta_url}

Email us at likhapohaaischool@gmail.com
"""


# ─────────────────────────────────────────────────────────────────────────────
# Resend transport
# ─────────────────────────────────────────────────────────────────────────────

def send_campaign_email(*, to: str, subject: str, html: str, text: str) -> SendResult:
    """Send one campaign email via Resend. Never raises — returns a SendResult."""
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        return SendResult(False, "RESEND_API_KEY not set")

    try:
        import truststore  # noqa: PLC0415

        truststore.inject_into_ssl()
    except Exception:
        pass

    payload = {
        "from": f"{SENDER_NAME} <{FROM_ADDRESS}>",
        "to": [to],
        "cc": [REPLY_TO],  # so every outbound copy also lands where replies go
        "subject": subject,
        "html": html,
        "text": text,
        "reply_to": REPLY_TO,
    }

    req = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "LikhaPohaAI-SchoolOutreach/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            if resp.status in (200, 201) or body.get("id"):
                return SendResult(True, body.get("id", ""))
            return SendResult(False, f"unexpected response: {body}")
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            detail = str(e)
        return SendResult(False, f"HTTP {e.code}: {detail}")
    except Exception as e:
        return SendResult(False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Supabase-backed queries
# ─────────────────────────────────────────────────────────────────────────────

def get_summary() -> dict:
    rows = (
        admin_client.table(TABLE)
        .select("status")
        .execute()
        .data or []
    )
    counts = {"pending": 0, "sent": 0, "failed": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    reminders_sent = (
        admin_client.table(TABLE)
        .select("id", count="exact")
        .not_.is_("reminder_sent_at", "null")
        .execute()
    ).count or 0
    responded = (
        admin_client.table(TABLE)
        .select("id", count="exact")
        .eq("responded", True)
        .execute()
    ).count or 0

    from datetime import datetime, timezone  # noqa: PLC0415
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    sent_today = (
        admin_client.table(TABLE)
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", today_start)
        .execute()
    ).count or 0

    return {
        "total": sum(counts.values()),
        "pending": counts.get("pending", 0),
        "sent": counts.get("sent", 0),
        "failed": counts.get("failed", 0),
        "sent_today": sent_today,
        "reminders_sent": reminders_sent,
        "responded": responded,
    }


def list_principals(
    *,
    status: str = "",
    needs_reminder: bool = False,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Paginated, filterable roster for the admin console's selection UI.
    needs_reminder=True overrides status filtering — it always means
    "sent 7+ days ago, no reminder yet, not marked responded".
    """
    query = admin_client.table(TABLE).select("*", count="exact")

    if needs_reminder:
        from datetime import datetime, timedelta, timezone  # noqa: PLC0415
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        query = (
            query.eq("status", "sent")
            .lte("sent_at", cutoff)
            .is_("reminder_sent_at", "null")
            .eq("responded", False)
        )
    elif status:
        query = query.eq("status", status)

    if q:
        q_clean = q.strip()
        query = query.or_(
            f"principal_name.ilike.%{q_clean}%,school_name.ilike.%{q_clean}%,email.ilike.%{q_clean}%"
        )

    query = query.order("created_at").range(offset, offset + limit - 1)
    resp = query.execute()
    return {"rows": resp.data or [], "total": resp.count or 0}


def get_by_emails(emails: list[str]) -> list[dict]:
    if not emails:
        return []
    return (
        admin_client.table(TABLE)
        .select("*")
        .in_("email", [e.strip().lower() for e in emails])
        .execute()
    ).data or []


def _mark_sent(email: str, resend_id: str) -> None:
    from datetime import datetime, timezone  # noqa: PLC0415
    admin_client.table(TABLE).update({
        "status": "sent",
        "resend_id": resend_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "error": "",
    }).eq("email", email).execute()


def _mark_failed(email: str, error: str) -> None:
    admin_client.table(TABLE).update({
        "status": "failed",
        "error": error[:500],
    }).eq("email", email).execute()


def _mark_reminder_sent(email: str) -> None:
    from datetime import datetime, timezone  # noqa: PLC0415
    admin_client.table(TABLE).update({
        "reminder_sent_at": datetime.now(timezone.utc).isoformat(),
    }).eq("email", email).execute()


def mark_responded(emails: list[str]) -> int:
    from datetime import datetime, timezone  # noqa: PLC0415
    if not emails:
        return 0
    resp = (
        admin_client.table(TABLE)
        .update({"responded": True, "responded_at": datetime.now(timezone.utc).isoformat()})
        .in_("email", [e.strip().lower() for e in emails])
        .execute()
    )
    return len(resp.data or [])


# ─────────────────────────────────────────────────────────────────────────────
# Background batch sender — runs in a daemon thread so the admin's request
# returns immediately instead of blocking for minutes on a large selection.
# ─────────────────────────────────────────────────────────────────────────────

def _run_batch(rows: list[dict], email_type: str) -> None:
    for row in rows:
        email = row["email"]
        name = row.get("principal_name", "")
        school = row.get("school_name", "")

        if email_type == "reminder":
            html = build_reminder_email_html(name, school, CTA_URL)
            text = build_reminder_email_text(name, school, CTA_URL)
            subject = f"Following up — {school}" if school else "Following up on Likha Poha AI"
        else:
            html = build_principal_email_html(name, school, CTA_URL)
            text = build_principal_email_text(name, school, CTA_URL)
            subject = f"A Principal Command Center for {school}" if school else "A Principal Command Center for your school"

        result = send_campaign_email(to=email, subject=subject, html=html, text=text)

        try:
            if result.success:
                if email_type == "reminder":
                    _mark_reminder_sent(email)
                else:
                    _mark_sent(email, result.detail)
            else:
                if email_type != "reminder":
                    _mark_failed(email, result.detail)
                _log.warning("school_outreach.send_failed", email=email, type=email_type, error=result.detail)
        except Exception:
            _log.error("school_outreach.state_update_failed", email=email, exc_info=True)

        time.sleep(SEND_DELAY_SECONDS)


def queue_send(emails: list[str], email_type: str = "initial") -> int:
    """
    Kick off sending to the given emails in a background thread; returns
    immediately with the count queued. email_type: "initial" | "reminder".

    "initial" only sends to rows still pending (skips anything already sent,
    so re-selecting an already-emailed principal is a harmless no-op).
    "reminder" sends regardless of status filtering here — the admin route
    is expected to have used needs_reminder=True to build the selection.
    """
    rows = get_by_emails(emails)
    if email_type == "initial":
        rows = [r for r in rows if r.get("status") != "sent"]

    if not rows:
        return 0

    threading.Thread(target=_run_batch, args=(rows, email_type), daemon=True).start()
    return len(rows)
