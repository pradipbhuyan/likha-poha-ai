"""
email_service.py — Transactional email service for Likha Poha AI
─────────────────────────────────────────────────────────────────
Sends:
  1. Welcome email   — on every new signup (platform or Google OAuth)
  2. Upgrade email   — when a student/parent activates a paid plan

Design:
  - All sends are fire-and-forget (daemon thread) — never blocks a route.
  - Reuses the same SMTP credentials as the alert service (ALERT_SMTP_*).
  - Gracefully skips sending if SMTP is not configured.
  - Never raises — logs errors and returns silently.

SMTP configuration (environment variables):
  ALERT_SMTP_HOST     — default: smtp.gmail.com
  ALERT_SMTP_PORT     — default: 587
  ALERT_SMTP_USER     — Gmail address that sends the email
  ALERT_SMTP_PASSWORD — Gmail App Password
  EMAIL_SENDER_NAME   — Display name in From header (default: Likha Poha AI)
"""

import os
import smtplib
import threading
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.logger_service import get_logger

_log = get_logger("email_service")

_BRAND_COLOR = "#6366f1"
_FRONTEND_URL = os.getenv("FRONTEND_URL", "https://likhapoha.in")
# Logo always uses the production domain — never localhost — so it renders in email clients
_LOGO_URL = "https://likhapoha.in/favicon.png"
# Internal inbox that gets pinged whenever a new teacher signs up, so someone
# reviews the school details and approves the account (see require_teacher()).
_ADMIN_NOTIFICATION_EMAIL = "likhapohaai@gmail.com"


# ── SMTP helpers ──────────────────────────────────────────────────────────────

def _get_smtp_config() -> dict | None:
    """Return SMTP config dict or None if not configured."""
    user     = os.getenv("ALERT_SMTP_USER", "").strip()
    password = os.getenv("ALERT_SMTP_PASSWORD", "").strip()
    if not user or not password:
        return None
    sender_name = os.getenv("EMAIL_SENDER_NAME", "Likha Poha AI").strip()
    return {
        "host":     os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com"),
        "port":     int(os.getenv("ALERT_SMTP_PORT", "587")),
        "user":     user,
        "password": password,
        "from":     f"{sender_name} <{user}>",
    }


def _make_ssl_context():
    """
    Build an SSL context using the system trust store (truststore package)
    so macOS/Windows/Linux corporate certificates are trusted automatically.
    Falls back to the default Python SSL context if truststore is unavailable.
    """
    try:
        import truststore  # noqa: PLC0415
        truststore.inject_into_ssl()
    except Exception:
        pass
    import ssl  # noqa: PLC0415
    return ssl.create_default_context()


def _clear_proxy_env() -> dict:
    """
    Temporarily clear proxy environment variables so smtplib connects directly.

    macOS PAC/system proxies (e.g. Cisco AnyConnect, Zscaler) can intercept
    and refuse SMTP connections on ports 587/465.  Python's smtplib reads
    ALL_PROXY, HTTP_PROXY, HTTPS_PROXY from the environment — clearing them
    for the SMTP call lets the connection bypass the proxy.
    """
    _proxy_keys = [
        "ALL_PROXY", "all_proxy",
        "HTTP_PROXY", "http_proxy",
        "HTTPS_PROXY", "https_proxy",
        "NO_PROXY", "no_proxy",
    ]
    saved = {}
    for k in _proxy_keys:
        val = os.environ.pop(k, None)
        if val is not None:
            saved[k] = val
    return saved


def _restore_proxy_env(saved: dict) -> None:
    """Restore proxy environment variables after SMTP send."""
    os.environ.update(saved)


def _send_via_resend(to: str, subject: str, html: str, text: str) -> bool:
    """
    Send email via Resend HTTPS API (port 443 — never blocked by firewalls).

    Resend free tier: 3,000 emails/month, no credit card required.
    Setup: resend.com → Add domain → Create API key → set RESEND_API_KEY + EMAIL_FROM_ADDRESS

    Required env vars:
      RESEND_API_KEY        — from resend.com (re_...)
      EMAIL_FROM_ADDRESS    — verified sender e.g. hello@likhapoha.in
    """
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_addr = os.getenv("EMAIL_FROM_ADDRESS", "").strip()
    sender_name = os.getenv("EMAIL_SENDER_NAME", "Likha Poha AI").strip()

    if not api_key or not from_addr:
        return False  # Resend not configured — fall through to SMTP

    _log.info("email_service.resend_attempt", to=to, from_addr=from_addr)

    try:
        import urllib.request  # noqa: PLC0415
        import urllib.error as _urllib_error  # noqa: PLC0415
        import json as _json  # noqa: PLC0415

        # Inject system trust store so macOS certificates work with urllib
        try:
            import truststore  # noqa: PLC0415
            truststore.inject_into_ssl()
        except Exception:
            pass

        reply_to = os.getenv("EMAIL_REPLY_TO", "").strip() or None

        resend_payload: dict = {
            "from": f"{sender_name} <{from_addr}>",
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        if reply_to:
            resend_payload["reply_to"] = reply_to

        payload = _json.dumps(resend_payload).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "LikhaPohaAI/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = _json.loads(resp.read())
                if resp.status in (200, 201) or body.get("id"):
                    _log.info("email_service.sent_via_resend", to=to, subject=subject)
                    return True
                _log.warning(
                    "email_service.resend_unexpected_response",
                    to=to, status=resp.status, body=str(body)[:300],
                )
        except _urllib_error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            _log.warning(
                "email_service.resend_http_error",
                to=to, status=http_err.code, body=err_body,
            )
    except Exception as exc:
        _log.warning("email_service.resend_failed", to=to, error=str(exc)[:300])

    return False


def _send(to: str, subject: str, html: str, text: str) -> bool:
    """
    Send an email — tries Resend HTTPS API first, falls back to SMTP.

    Resend (port 443): works on Railway, cloud servers, all networks.
    SMTP (port 587/465): works on home networks, may be blocked on corporate/cloud.
    Returns True on success, False on failure (never raises).
    """
    # Primary: Resend HTTPS API (if configured — works on Railway/cloud)
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    resend_from = os.getenv("EMAIL_FROM_ADDRESS", "").strip()
    resend_configured = bool(resend_key and resend_from)

    if resend_configured:
        result = _send_via_resend(to, subject, html, text)
        if result:
            return True
        # Resend is configured but failed — do NOT fall through to SMTP
        # (SMTP is blocked on Railway/cloud servers anyway)
        _log.warning("email_service.resend_failed_no_smtp_fallback",
                     to=to, from_addr=resend_from,
                     hint="Check RESEND_API_KEY and EMAIL_FROM_ADDRESS in Railway env vars")
        return False

    # Fallback: SMTP (only when Resend is NOT configured — local dev only)
    cfg = _get_smtp_config()
    if not cfg:
        _log.debug("email_service.not_configured", to=to)
        return False

    # Strip spaces from App Password (Gmail displays it as "xxxx xxxx xxxx xxxx")
    password = cfg["password"].replace(" ", "")

    # Clear proxy env vars — corporate proxies may block SMTP ports
    saved_proxy = _clear_proxy_env()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["from"]
        msg["To"]      = to

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        ctx = _make_ssl_context()

        # Primary SMTP: STARTTLS on port 587
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.login(cfg["user"], password)
                server.sendmail(cfg["user"], [to], msg.as_string())
            _log.info("email_service.sent_via_smtp", to=to, subject=subject, port=cfg["port"])
            return True
        except (smtplib.SMTPException, OSError):
            pass  # fall through to port 465

        # SMTP fallback: SSL on port 465
        with smtplib.SMTP_SSL(cfg["host"], 465, context=ctx, timeout=15) as server:
            server.login(cfg["user"], password)
            server.sendmail(cfg["user"], [to], msg.as_string())
        _log.info("email_service.sent_via_smtp", to=to, subject=subject, port=465)
        return True

    except Exception as exc:
        _log.error("email_service.failed", to=to, subject=subject, error=str(exc)[:200])
        return False
    finally:
        _restore_proxy_env(saved_proxy)


def _send_async(to: str, subject: str, html: str, text: str) -> None:
    """Fire-and-forget in a daemon thread so routes never block."""
    threading.Thread(
        target=_send,
        args=(to, subject, html, text),
        daemon=True,
    ).start()


# ── Shared email shell ────────────────────────────────────────────────────────

def _email_shell(body_html: str, cta_url: str, cta_label: str) -> str:
    """Wrap body content in a branded HTML email shell."""
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
                Questions? Email us at
                <a href="mailto:likhapohaai@gmail.com" style="color:{_BRAND_COLOR};text-decoration:none">likhapohaai@gmail.com</a>
                or visit <a href="{_FRONTEND_URL}" style="color:{_BRAND_COLOR};text-decoration:none">likhapoha.in</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Feature blocks ────────────────────────────────────────────────────────────

# ── Grade-specific feature sets ───────────────────────────────────────────────

_FEATURES_GRADE_5_8 = [
    ("📖", "AI Lessons — 5 Steps Per Chapter",
     "Every NCERT chapter broken into 5 easy steps: Concept → Examples → Practice → Summary → Quiz. "
     "Go to <strong>Lessons</strong> and pick your grade, subject, and chapter."),
    ("🧪", "Chapter-Wise Mock Tests",
     "MCQ tests for any chapter with AI explanations for every answer. "
     "Try <strong>Mock Tests</strong> after finishing a lesson."),
    ("❓", "Ask Doubts Instantly",
     "Stuck on a question? Type it and get a clear AI answer in seconds — "
     "Maths, Science, English, Social Science, Hindi. Use the <strong>Ask Doubt</strong> tab anytime."),
    ("📊", "Progress Tracking",
     "See which chapters you've covered, your mock test scores, and your daily learning streak. "
     "Check your <strong>Analytics</strong> dashboard after each session."),
]

_FEATURES_GRADE_9_10 = [
    ("📖", "AI Lessons — 5 Steps Per Chapter",
     "Concept → Examples → Practice → Summary → Exam-style problems. Every NCERT chapter, "
     "board-exam ready. Go to <strong>Lessons</strong> to start your first chapter today."),
    ("🧪", "Chapter-Wise Mock Tests",
     "Board-pattern MCQ tests for every chapter with AI explanations for each answer — "
     "ideal for CBSE Class 10 boards. Use <strong>Mock Tests</strong> after every lesson."),
    ("❓", "Ask Doubts Instantly",
     "Type any doubt and get a clear AI answer in seconds — Maths, Science, English, SST, Hindi. "
     "Available in the <strong>Ask Doubt</strong> tab, all day."),
    ("&#128270;", "NCERT Exemplar Research",
     "Hard NCERT Exemplar problems with instant AI step-by-step solutions — "
     "essential for scoring 90%+ in Class 10 boards."),
    ("📄", "Board Papers",
     "A decade of real CBSE Class 10 board papers to practise under exam conditions, "
     "with every mark explained. Find them under <strong>Board Papers</strong>."),
    ("📐", "Formula Sheets",
     "Chapter-wise Maths & Science formulas with worked examples, memory tips, "
     "and practice MCQs. Find them under <strong>Resources</strong>."),
    ("📊", "Progress & Analytics",
     "Lessons completed, mock scores, weak topics, and AI usage — all tracked in your "
     "<strong>Analytics</strong> dashboard."),
]

_FEATURES_GRADE_11_12_SCIENCE = [
    ("📖", "AI Lessons — NCERT Class 11 & 12",
     "Full AI-guided lessons for Physics, Chemistry, Maths, and Biology — "
     "concept → worked examples → exam problems → summary. Start from <strong>Lessons</strong>."),
    ("🧪", "Chapter-Wise Mock Tests",
     "Board-pattern MCQ tests with AI explanations — covers CBSE Class 11 & 12 syllabus "
     "for all your stream subjects. Use <strong>Mock Tests</strong> after each chapter."),
    ("📐", "Formula Sheets — Science & Maths",
     "Complete formula library for Physics, Chemistry, and Maths with derivations, "
     "memory tips, and practice problems. Available under <strong>Resources</strong>."),
    ("&#128270;", "NCERT Exemplar Research",
     "Hard NCERT Exemplar problems — Physics, Chemistry, Maths, Biology — "
     "with instant AI explanations. Essential for board exam scoring."),
    ("📄", "Board Papers",
     "A decade of real CBSE Class 11 & 12 board papers to practise under exam conditions, "
     "with every mark explained. Find them under <strong>Board Papers</strong>."),
    ("❓", "Ask Doubts Instantly",
     "Type any Physics, Chemistry, Maths, or Biology doubt and get an AI answer with "
     "step-by-step working. Available in the <strong>Ask Doubt</strong> tab."),
    ("📊", "Progress & Analytics",
     "Track your chapter coverage, mock test scores by subject, weak topics, and daily study time "
     "— all in your <strong>Analytics</strong> dashboard."),
]

_FEATURES_GRADE_11_12_EXAM_PREP = [
    ("🎯", "Exam Prep Center — JEE & NEET",
     "AI-powered JEE Main and NEET UG practice questions, topic priority cards, "
     "and simulated full tests — available as a <strong>Premium feature</strong>."),
    ("📖", "AI Lessons — NCERT Class 11 & 12",
     "Full AI-guided lessons for your stream subjects with worked examples and exam problems. "
     "Start from <strong>Lessons</strong>."),
    ("📐", "Formula Sheets — Physics, Chemistry, Maths/Bio",
     "Complete formula library with derivations, memory tips, and practice MCQs. "
     "Available under <strong>Resources</strong>."),
    ("🧪", "Chapter-Wise Mock Tests",
     "Board and entrance exam pattern tests with AI explanations for every answer. "
     "Use <strong>Mock Tests</strong> to test chapter readiness."),
    ("❓", "Ask Doubts Instantly",
     "Type any Physics, Chemistry, Maths, or Biology doubt — AI answers with full working. "
     "Available in the <strong>Ask Doubt</strong> tab."),
    ("📊", "Progress & Analytics",
     "Chapter coverage, mock test scores by subject, weak topic tracker, and daily study time "
     "— all in your <strong>Analytics</strong> dashboard."),
]

_FEATURES_GRADE_11_12_COMMERCE = [
    ("📖", "AI Lessons — Commerce Class 11 & 12",
     "Full AI-guided lessons for Accountancy, Business Studies, Economics, and Maths — "
     "board-exam ready. Start from <strong>Lessons</strong>."),
    ("🧪", "Chapter-Wise Mock Tests",
     "Board-pattern tests for Accountancy, Business Studies, Economics, and Maths "
     "with AI explanations for every answer. Use <strong>Mock Tests</strong> after each chapter."),
    ("❓", "Ask Doubts Instantly",
     "Type any Accountancy, Economics, or Business Studies doubt and get an AI answer "
     "in seconds. Available in the <strong>Ask Doubt</strong> tab."),
    ("📄", "Board Papers",
     "A decade of real CBSE Class 11 & 12 board papers to practise under exam conditions, "
     "with every mark explained. Find them under <strong>Board Papers</strong>."),
    ("📊", "Progress & Analytics",
     "Track your chapter coverage, mock test scores by subject, and daily study time "
     "— all in your <strong>Analytics</strong> dashboard."),
    ("📐", "Formula Sheets",
     "Commerce formulas, ratio definitions, and key concepts with examples. "
     "Available under <strong>Resources</strong>."),
]

_FEATURES_GRADE_11_12_HUMANITIES = [
    ("📖", "AI Lessons — Humanities Class 11 & 12",
     "Full AI-guided lessons for History, Geography, Political Science, Economics, and Sociology — "
     "board-exam ready. Start from <strong>Lessons</strong>."),
    ("🧪", "Chapter-Wise Mock Tests",
     "Board-pattern tests for all your Humanities subjects with AI explanations. "
     "Use <strong>Mock Tests</strong> after each chapter."),
    ("❓", "Ask Doubts Instantly",
     "Type any History, Geography, or Polsci doubt and get a clear AI answer in seconds. "
     "Available in the <strong>Ask Doubt</strong> tab."),
    ("📄", "Board Papers",
     "A decade of real CBSE Class 11 & 12 board papers to practise under exam conditions, "
     "with every mark explained. Find them under <strong>Board Papers</strong>."),
    ("📊", "Progress & Analytics",
     "Track your chapter coverage, mock test scores by subject, and study consistency "
     "— all in your <strong>Analytics</strong> dashboard."),
]

# Fallback (generic) — used when grade is unknown
_FEATURES_STUDENT = [
    ("📖", "AI Lessons — 5 Steps Per Chapter",
     "Concept → Examples → Practice → Summary → Quiz. Every NCERT chapter in 5 guided steps "
     "with audio narration. Go to <strong>Lessons</strong> to start."),
    ("🧪", "Chapter-Wise Mock Tests",
     "MCQ tests for any chapter with AI explanations for every answer — ideal for board exam prep. "
     "Try <strong>Mock Tests</strong> after each lesson."),
    ("❓", "Ask Doubts Instantly",
     "Type any question and get a clear AI answer in seconds — Maths, Science, English, "
     "Social Science, and more. Use the <strong>Ask Doubt</strong> tab anytime."),
    ("📐", "Formula Sheets",
     "Chapter-wise formulas for Maths & Science with worked examples, memory tips, "
     "and practice MCQs. Find them under <strong>Resources</strong>."),
    ("&#128270;", "NCERT Exemplar Research",
     "Hard problems from NCERT Exemplar with instant AI explanations — "
     "essential for scoring 90%+ in board exams."),
    ("📄", "Board Papers",
     "A decade of real CBSE board papers (Grades 9&ndash;12) to practise under exam conditions, "
     "with every mark explained. Find them under <strong>Board Papers</strong>."),
    ("🎯", "Exam Prep Center",
     "Dedicated JEE Main &amp; NEET UG prep for Grades 11&ndash;12 — topic-priority practice "
     "and simulated full tests, available as a <strong>Premium feature</strong>."),
    ("📊", "Progress & Analytics",
     "Track lessons completed, mock test scores, weak topics, and AI usage — "
     "all in your <strong>Analytics</strong> dashboard."),
]


def _get_student_features(grade: str, stream: str, is_paid: bool) -> list:
    """Return the grade- and stream-appropriate feature list."""
    g = (grade or "").strip().lower()
    s = (stream or "").strip().upper()

    if g in ("grade 5", "grade 6", "grade 7", "grade 8"):
        return _FEATURES_GRADE_5_8
    if g in ("grade 9", "grade 10"):
        return _FEATURES_GRADE_9_10
    if g in ("grade 11", "grade 12"):
        if s in ("PCM", "PCB", "PCMB"):
            # Science stream — show exam prep if paid, else mention it as premium
            features = list(_FEATURES_GRADE_11_12_SCIENCE)
            if is_paid:
                # Insert Exam Prep Center at top
                features.insert(0, _FEATURES_GRADE_11_12_EXAM_PREP[0])
            else:
                # Mention it as a premium feature at the end
                features.append(_FEATURES_GRADE_11_12_EXAM_PREP[0])
            return features
        if s == "COMMERCE":
            return _FEATURES_GRADE_11_12_COMMERCE
        if s == "HUMANITIES":
            return _FEATURES_GRADE_11_12_HUMANITIES
        # Grade 11/12 with unknown/general stream
        return _FEATURES_GRADE_11_12_SCIENCE
    return _FEATURES_STUDENT  # fallback

_FEATURES_TEACHER = [
    ("📋", "Create Lesson Plans",
     "Generate curriculum-aligned lesson plans for any NCERT chapter in seconds. "
     "Go to <strong>Create Lesson Plans</strong>."),
    ("🧪", "Create Test Papers",
     "Generate CBSE-pattern test papers for any grade, subject, and chapter, "
     "ready to print or share. Use <strong>Create Test Paper</strong>."),
    ("🎧", "Listen to Lecture Audio",
     "AI-narrated lecture audio you can play in class or share with students for revision. "
     "Available under <strong>Listen to Lecture</strong>."),
    ("📖", "Browse AI Lessons",
     "Preview the same step-by-step AI lessons your students see, chapter by chapter. "
     "Available under <strong>Lessons</strong>."),
    ("📊", "Student Analytics",
     "Track your students' chapter coverage, mock test scores, and weak topics — "
     "all in your <strong>Student Analytics</strong> dashboard."),
]

_FEATURES_PARENT = [
    ("👁", "Child Progress Dashboard",
     "See every lesson your child has studied, mock test scores by chapter, "
     "and daily AI usage — all in one view on your <strong>Parent Dashboard</strong>."),
    ("📈", "Academic Insights",
     "Weekly trends, weak subject detection, and AI-generated insights "
     "so you always know where your child needs help."),
    ("🔔", "Activity Alerts",
     "Get notified when your child hasn't logged in, completes a chapter, "
     "or scores below expectations on a mock test."),
    ("➕", "Add Child & Share Access",
     "Log in &rarr; click <strong>Add Child</strong> to create your child's student account. "
     "Share the login link so they can start learning immediately."),
    ("💳", "Manage Subscription",
     "Upgrade to <strong>Family Premium</strong> for unlimited access for up to 2 children — "
     "NCERT Exemplar, full mock tests, and no daily caps."),
]


def _feature_table(features: list) -> str:
    rows = ""
    for i, (icon, title, desc) in enumerate(features):
        bg = " style=\"background:#f8fafc\"" if i == 0 else ""
        border = "" if i == 0 else " style=\"border-top:1px solid #e5e7eb\""
        rows += f"""
  <tr{border}{bg}>
    <td width="40" style="padding:12px 14px;font-size:20px">{icon}</td>
    <td style="padding:12px 8px 12px 0">
      <strong style="font-size:14px">{title}</strong><br>
      <span style="font-size:13px;color:#64748b">{desc}</span>
    </td>
  </tr>"""
    return f"""<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
       style="margin:20px 0;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb">
  {rows}
</table>"""


_FREE_TIER_NOTICE = """
<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;
            padding:14px 16px;margin-top:16px">
  <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6">
    <strong>&#128204; Free Tier limits:</strong> limited AI lessons, 5 mock tests/day,
    and limited Doubt answers. Upgrade to <strong>Premium (&#8377;299/month)</strong>
    for unlimited access, NCERT Exemplar, and advanced formula sheets.
  </p>
</div>"""


# ── Admin notification — new teacher signup ────────────────────────────────

def send_teacher_signup_admin_notification(name: str, email: str, school: str) -> None:
    """
    Notify the team inbox whenever a new teacher account is created, so
    someone reviews the school details and approves it via
    POST /api/admin/support/users/{id}/verify-teacher (see require_teacher()
    in auth_service.py — the account is otherwise stuck on
    account_status="pending_verification" until this happens).

    Reuses the same branded shell / fire-and-forget send as every other
    email in this module. Never raises — callers wrap this in try/except
    anyway, but a failure here must never be able to block a signup.
    """
    if not _ADMIN_NOTIFICATION_EMAIL:
        return

    first_name = (name or "there").split()[0]
    school_clean = (school or "").strip() or "(not provided)"
    email_clean = (email or "").strip() or "(not provided)"

    body = f"""
<p style="margin:0 0 16px;font-size:20px;font-weight:900;letter-spacing:-0.02em">
  New teacher signup &#128276;
</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.7">
  <strong>{name or "A teacher"}</strong> just signed up and is waiting on school verification
  before their Teacher Dashboard unlocks.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
       style="margin:8px 0 16px;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb">
  <tr style="background:#f8fafc">
    <td style="padding:10px 14px;font-size:13px;color:#64748b;width:110px">Name</td>
    <td style="padding:10px 14px;font-size:13px;font-weight:700">{name or "—"}</td>
  </tr>
  <tr style="border-top:1px solid #e5e7eb">
    <td style="padding:10px 14px;font-size:13px;color:#64748b">Email</td>
    <td style="padding:10px 14px;font-size:13px;font-weight:700">{email_clean}</td>
  </tr>
  <tr style="border-top:1px solid #e5e7eb;background:#f8fafc">
    <td style="padding:10px 14px;font-size:13px;color:#64748b">School</td>
    <td style="padding:10px 14px;font-size:13px;font-weight:700">{school_clean}</td>
  </tr>
</table>
<p style="margin:0;font-size:13px;color:#64748b;line-height:1.7">
  Approve from Admin Control &rarr; Support Tools &rarr; Pending Teacher Approvals.
</p>
"""

    html = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="Open Admin Panel →",
    )

    text = (
        f"New teacher signup: {name or 'Unknown'}\n"
        f"Email: {email_clean}\n"
        f"School: {school_clean}\n\n"
        f"Approve from Admin Control -> Support Tools -> Pending Teacher Approvals.\n"
        f"{_FRONTEND_URL}\n"
    )

    _send_async(
        to=_ADMIN_NOTIFICATION_EMAIL,
        subject=f"New teacher signup: {first_name} ({school_clean})",
        html=html,
        text=text,
    )
    _log.info("email_service.teacher_admin_notification_queued", teacher_email=email_clean, school=school_clean)


# ── Public API ────────────────────────────────────────────────────────────────

def send_welcome_email(
    to: str,
    name: str,
    role: str,
    is_paid: bool = False,
    plan_name: str = "",
    grade: str = "",
    stream: str = "",
    school: str = "",
) -> None:
    """
    Send a grade-personalised welcome email to a newly registered user.

    Parameters
    ----------
    grade  : Student grade string e.g. "Grade 9", "Grade 11". Empty for parents/teachers.
    stream : Academic stream for Grade 11/12 e.g. "PCM", "PCB", "Commerce", "Humanities".
    school : Teacher's school name. Empty for parents/students. When role="teacher",
             also triggers send_teacher_signup_admin_notification() so the team
             knows to review and approve the account.

    Called after:
      - Free Tier signup  (signup_free)
      - Paid signup       (complete_signup)
      - Offer code signup (signup_with_offer_code)
      - Google OAuth      (oauth_complete_profile — first time role is set)
      - Teacher signup    (teacher_signup)

    Non-blocking: always fires in a background thread.
    """
    if not to:
        return

    first_name = (name or "there").split()[0]
    role_clean = (role or "student").lower()
    is_parent  = role_clean == "parent"
    is_teacher = role_clean == "teacher"
    g = (grade or "").strip()
    s = (stream or "").strip().upper()
    g_lower = g.lower()
    is_1112 = g_lower in ("grade 11", "grade 12")
    is_science_stream = s in ("PCM", "PCB", "PCMB")

    if is_teacher:
        try:
            send_teacher_signup_admin_notification(name=name, email=to, school=school)
        except Exception:
            _log.warning("email_service.teacher_admin_notification_failed", to=to, exc_info=True)

    plan_badge = ""
    if is_paid and plan_name:
        plan_badge = (
            f'<span style="display:inline-block;background:#dcfce7;color:#166534;'
            f'border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;'
            f'margin-bottom:18px">'
            f'&#10003; {plan_name} activated</span><br>'
        )

    # ── Grade badge for students ───────────────────────────────────────────
    grade_badge = ""
    if g and not is_parent:
        stream_label = f" &middot; {s}" if s else ""
        grade_badge = (
            f'<span style="display:inline-block;background:#ede9fe;color:#5b21b6;'
            f'border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;'
            f'margin-bottom:14px">'
            f'{g}{stream_label}</span><br>'
        )

    # ── Grade-specific features ────────────────────────────────────────────
    if is_teacher:
        features = _FEATURES_TEACHER
    elif is_parent:
        features = _FEATURES_PARENT
    else:
        features = _get_student_features(g, s, is_paid)

    features_html = _feature_table(features)

    # ── Grade-specific free tier notice ───────────────────────────────────
    if is_teacher:
        free_notice = """
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
            padding:14px 16px;margin-top:16px">
  <p style="margin:0;font-size:13px;color:#1e3a8a;line-height:1.6">
    <strong>&#128203; Account under review:</strong> our team verifies your school details
    before the Teacher Dashboard unlocks — usually within one business day. You can log in
    anytime to check your status.
  </p>
</div>"""
    elif is_paid:
        free_notice = ""
    elif is_1112 and is_science_stream:
        free_notice = """
<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;
            padding:14px 16px;margin-top:16px">
  <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6">
    <strong>&#128204; Free Tier limits:</strong> limited AI lessons, 5 mock tests/day,
    and limited Doubt answers. <strong>Exam Prep Center (JEE/NEET)</strong> is a Premium feature.
    Upgrade to <strong>Premium (&#8377;299/month)</strong> for unlimited access,
    NCERT Exemplar, and advanced formula sheets.
  </p>
</div>"""
    elif is_1112:
        free_notice = """
<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;
            padding:14px 16px;margin-top:16px">
  <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6">
    <strong>&#128204; Free Tier limits:</strong> limited AI lessons, 5 mock tests/day,
    and limited Doubt answers. Upgrade to <strong>Premium (&#8377;299/month)</strong>
    for unlimited access, NCERT Exemplar, and advanced formula sheets.
  </p>
</div>"""
    else:
        free_notice = _FREE_TIER_NOTICE

    # ── Grade-specific intro + next step ──────────────────────────────────
    if is_teacher:
        intro = (
            "<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            "Welcome to <strong>Likha Poha AI</strong> — India's AI-powered CBSE tutor. "
            "As a teacher, you can generate lesson plans and test papers in seconds, "
            "listen to AI-narrated lecture audio, and track every student's progress "
            "from one dashboard.</p>"
            "<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            "Here's what you'll have access to once your account is verified:</p>"
        )
        next_step = (
            "<div style=\"background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;"
            "padding:16px 18px;margin-top:16px\">"
            "<p style=\"margin:0 0 8px;font-size:14px;font-weight:700;color:#1e40af\">"
            "&#128075; What happens next</p>"
            "<p style=\"margin:0;font-size:13px;color:#1e3a8a;line-height:1.7\">"
            "Our team verifies your school details — usually within one business day. "
            "You can log in right away to check your verification status; once approved, "
            "your <strong>Teacher Dashboard</strong> unlocks automatically.</p>"
            "</div>"
        )
    elif is_parent:
        intro = (
            "<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            "Welcome to <strong>Likha Poha AI</strong> — India's AI-powered CBSE tutor. "
            "As a parent, you get a dedicated dashboard to monitor your child's lessons, "
            "mock test scores, and AI usage in real time.</p>"
            "<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            "Here's what you can see and do on your Parent Dashboard:</p>"
        )
        next_step = (
            "<div style=\"background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;"
            "padding:16px 18px;margin-top:16px\">"
            "<p style=\"margin:0 0 8px;font-size:14px;font-weight:700;color:#1e40af\">"
            "&#128075; First Step: Create Your Child's Account</p>"
            "<p style=\"margin:0;font-size:13px;color:#1e3a8a;line-height:1.7\">"
            "Log in &rarr; go to your <strong>Parent Dashboard</strong> &rarr; "
            "click <strong>Add Child</strong> &rarr; fill in your child's name and grade. "
            "A student account will be created instantly. Share the login details with your child "
            "so they can start their first AI lesson today.</p>"
            "</div>"
        )
    elif g_lower in ("grade 5", "grade 6", "grade 7", "grade 8"):
        intro = (
            f"<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            f"Welcome to <strong>Likha Poha AI</strong> — your AI-powered CBSE tutor for "
            f"{g}. Get step-by-step AI lessons, take chapter tests, and clear every doubt "
            f"in seconds.</p>"
            f"<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            f"Here's what you can do:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            "<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            "pick your Subject and Chapter &rarr; click <em>Generate Lesson</em>. "
            "Your first AI lesson is ready in seconds.</p>"
        )
    elif g_lower in ("grade 9", "grade 10"):
        intro = (
            f"<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            f"Welcome to <strong>Likha Poha AI</strong> — your AI-powered CBSE tutor for "
            f"{g} board exam preparation. Generate chapter-wise AI lessons, take board-pattern "
            f"mock tests, and get instant AI answers to every doubt.</p>"
            f"<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            f"Here's what you can do to prepare for boards:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            "<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            "pick your Subject and Chapter &rarr; click <em>Generate Lesson</em>. "
            "After each lesson, take the mock test and check <em>Analytics</em> for weak topics.</p>"
        )
    elif is_1112 and is_science_stream:
        exam_label = "JEE Main & NEET UG" if s == "PCMB" else ("JEE Main" if s == "PCM" else "NEET UG")
        intro = (
            f"<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            f"Welcome to <strong>Likha Poha AI</strong> — your AI-powered CBSE tutor for "
            f"{g} {s}. Get chapter-wise AI lessons, mock tests, instant doubt solving, "
            f"and — as a Premium feature — dedicated <strong>Exam Prep for {exam_label}</strong> "
            f"with topic-priority practice questions and simulated full tests.</p>"
            f"<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            f"Here's what's available on your account:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            f"<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            f"pick {g} {s} subjects &rarr; click <em>Generate Lesson</em>. "
            "After each chapter, take the mock test. Use <em>Exam Prep Center</em> "
            "(Premium) for JEE/NEET topic-wise practice and simulated tests.</p>"
        )
    elif is_1112 and s == "COMMERCE":
        intro = (
            f"<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            f"Welcome to <strong>Likha Poha AI</strong> — your AI-powered CBSE tutor for "
            f"{g} Commerce. Get AI-guided lessons for Accountancy, Business Studies, "
            f"Economics, and Maths, board-pattern mock tests, and instant doubt solving.</p>"
            f"<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            f"Here's what's available on your account:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            "<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            "pick Accountancy, Business Studies, Economics, or Maths &rarr; click <em>Generate Lesson</em>. "
            "After each lesson, take the mock test to lock in understanding.</p>"
        )
    elif is_1112:
        intro = (
            f"<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            f"Welcome to <strong>Likha Poha AI</strong> — your AI-powered CBSE tutor for "
            f"{g}. Get AI-guided lessons for your stream subjects, board-pattern mock tests, "
            f"and instant AI doubt solving.</p>"
            f"<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            f"Here's what's available on your account:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            "<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            "pick your Subject and Chapter &rarr; click <em>Generate Lesson</em>. "
            "Take the mock test after each lesson and check <em>Analytics</em> for weak topics.</p>"
        )
    else:
        intro = (
            "<p style=\"margin:0 0 12px;font-size:15px;line-height:1.7\">"
            "Welcome to <strong>Likha Poha AI</strong> — your personal CBSE tutor for "
            "Grades 5&ndash;12. Generate full AI lessons, take chapter-wise mock tests, "
            "ask doubts instantly, and track your progress every day.</p>"
            "<p style=\"margin:0 0 6px;font-size:14px;color:#64748b\">"
            "Here's what you can do on the platform:</p>"
        )
        next_step = (
            "<p style=\"margin:20px 0 0;font-size:14px;color:#475569;line-height:1.7\">"
            "<strong>Get started:</strong> Log in &rarr; go to <em>Lessons</em> &rarr; "
            "pick your Grade, Subject, and Chapter &rarr; click <em>Generate Lesson</em>. "
            "Your first AI lesson is ready in seconds.</p>"
        )

    body = f"""
<p style="margin:0 0 16px;font-size:24px;font-weight:900;letter-spacing:-0.02em">
  Welcome, {first_name}! 🎉
</p>
{grade_badge}
{plan_badge}
{intro}
{features_html}
{next_step}
{free_notice}
"""

    html = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="Start Learning on Likha Poha AI →",
    )

    grade_line = f" ({g}{(' ' + s) if s else ''})" if g else ""
    text = (
        f"Welcome to Likha Poha AI, {first_name}!{grade_line}\n\n"
        f"Your account is ready. Visit {_FRONTEND_URL} to start learning.\n\n"
        f"Key features: AI Lessons | Mock Tests | Ask Doubts | Formula Sheets | "
        f"Board Papers | Exam Prep Center | Progress Analytics\n"
        + (f"\nYour plan: {plan_name}\n" if is_paid and plan_name else
           f"\nFree Tier: 5 mock tests/day, limited lessons. Upgrade anytime at {_FRONTEND_URL}.\n")
    )

    _send_async(
        to=to,
        subject=f"Welcome to Likha Poha AI, {first_name}! 🎉",
        html=html,
        text=text,
    )
    _log.info("email_service.welcome_queued", to=to, role=role_clean, is_paid=is_paid, grade=g)


def send_upgrade_email(
    to: str,
    name: str,
    role: str,
    plan_name: str,
    expires_at: str | None = None,
    days_remaining: int | None = None,
) -> None:
    """
    Send a plan upgrade confirmation email to a student or parent.

    Called after:
      - verify_payment()         (payments.py) — parent-triggered upgrade
      - student_verify_payment() (payments.py) — student self-service upgrade

    Non-blocking: always fires in a background thread.
    """
    if not to:
        return

    first_name = (name or "there").split()[0]
    role_clean = (role or "student").lower()
    is_parent  = role_clean == "parent"

    # Validity line
    if expires_at:
        try:
            from datetime import datetime, timezone  # noqa: PLC0415
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            exp_str = exp.strftime("%d %b %Y")
            validity_line = f"<p style=\"margin:0 0 4px;font-size:14px;color:#475569\">Valid until: <strong>{exp_str}</strong></p>"
            if days_remaining is not None:
                validity_line += (
                    f"<p style=\"margin:0 0 20px;font-size:13px;color:#64748b\">"
                    f"{days_remaining} days remaining</p>"
                )
        except Exception:
            validity_line = ""
    else:
        validity_line = "<p style=\"margin:0 0 20px;font-size:13px;color:#64748b\">Lifetime / perpetual access</p>"

    # What's unlocked
    if is_parent:
        unlocked_items = [
            "Full AI lessons for your child — all 5 steps, no daily cap",
            "Unlimited mock tests — practice any chapter any number of times",
            "NCERT Exemplar access — hard problems for top scores",
            "Advanced formula sheets — solved examples, memory tips, MCQ practice",
            "Up to 2 children on Family Premium plans",
        ]
    else:
        unlocked_items = [
            "Full AI lessons — all 5 steps for every chapter, no daily cap",
            "Unlimited mock tests — any chapter, any number of times",
            "NCERT Exemplar Research — hard problems essential for 90%+ scores",
            "Full formula sheets — solved examples, memory tips, and MCQ practice",
            "Unlimited Ask Doubts — instant AI answers for any CBSE question",
        ]

    unlocked_html = "".join(
        f'<li style="margin:6px 0;font-size:14px;color:#374151;line-height:1.5">{item}</li>'
        for item in unlocked_items
    )

    body = f"""
<p style="margin:0 0 20px;font-size:24px;font-weight:900;letter-spacing:-0.02em">
  You're all set, {first_name}! 🚀
</p>

<div style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5);
            border:1px solid #86efac;border-radius:10px;
            padding:18px 20px;margin-bottom:20px">
  <p style="margin:0 0 6px;font-size:12px;font-weight:700;
            text-transform:uppercase;letter-spacing:.06em;color:#166534">
    Plan Activated
  </p>
  <p style="margin:0 0 8px;font-size:20px;font-weight:900;color:#14532d">
    &#10003; {plan_name}
  </p>
  {validity_line}
  <p style="margin:0;font-size:13px;color:#166534">
    Full platform access is now live on your account.
  </p>
</div>

<p style="margin:0 0 10px;font-size:15px;font-weight:700">What's now unlocked:</p>
<ul style="margin:0 0 20px;padding-left:20px">
  {unlocked_html}
</ul>

<p style="margin:0;font-size:14px;color:#475569;line-height:1.7">
  <strong>How to get the most out of your plan:</strong><br>
  Go to <em>Lessons</em> &rarr; pick any chapter &rarr; generate a full 5-step AI lesson.
  After each lesson, take the mock test and review weak areas in <em>Analytics</em>.
  Use <em>Ask Doubts</em> for any question that comes up during study.
</p>
"""

    html = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="Go to My Dashboard →",
    )

    text = (
        f"Congratulations, {first_name}!\n\n"
        f"Your {plan_name} is now active.\n"
        + (f"Valid until: {expires_at[:10]}\n" if expires_at else "")
        + "\nWhat's unlocked:\n"
        + "".join(f"  - {item}\n" for item in unlocked_items)
        + f"\nLog in at {_FRONTEND_URL} to start learning.\n"
    )

    _send_async(
        to=to,
        subject=f"Your {plan_name} is now active! ✓",
        html=html,
        text=text,
    )
    _log.info("email_service.upgrade_queued", to=to, plan_name=plan_name)


# ── Weekly parent digest ──────────────────────────────────────────────────────

def _build_weekly_digest_email(
    parent_name: str,
    children: list[dict],
    unsubscribe_url: str,
) -> tuple[str, str, str]:
    """
    Build (subject, html, text) for the weekly parent digest.

    children: [{name, grade, mock_tests_count, avg_score (float|None),
                weak_areas (list[str]), activity_count, plan_name,
                plan_status_label, has_full_access}, ...]
    """
    first_name = (parent_name or "there").split()[0]

    def _child_block(c: dict) -> str:
        score_line = (
            f"{c['avg_score']}% average" if c.get("avg_score") is not None
            else "no mock tests this week"
        )
        weak = c.get("weak_areas") or []
        weak_line = (
            f"<p style=\"margin:6px 0 0;font-size:13px;color:#b91c1c\">"
            f"Needs practice: {', '.join(weak[:3])}</p>"
            if weak else ""
        )
        plan_color = "#166534" if c.get("has_full_access") else "#dc2626"
        return f"""
<div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;margin-bottom:12px">
  <p style="margin:0 0 4px;font-size:16px;font-weight:800">{c.get('name','Child')}
    <span style="font-weight:500;color:#64748b;font-size:13px">&middot; {c.get('grade','')}</span>
  </p>
  <p style="margin:0;font-size:13px;color:{plan_color};font-weight:700">{c.get('plan_status_label','')}</p>
  <p style="margin:8px 0 0;font-size:14px;color:#374151">
    {c.get('mock_tests_count',0)} mock test(s) this week &middot; {score_line}
    &middot; {c.get('activity_count',0)} AI activity session(s)
  </p>
  {weak_line}
</div>"""

    children_html = "".join(_child_block(c) for c in children)

    body = f"""
<p style="margin:0 0 20px;font-size:24px;font-weight:900;letter-spacing:-0.02em">
  This week's progress, {first_name} 👋
</p>
<p style="margin:0 0 20px;font-size:14px;color:#475569">
  Here's how your {"children are" if len(children) > 1 else "child is"} doing this week:
</p>
{children_html}
<p style="margin:20px 0 0;font-size:12px;color:#94a3b8">
  <a href="{unsubscribe_url}" style="color:#94a3b8">Unsubscribe from weekly emails</a>
</p>
"""

    html = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="View Full Dashboard →",
    )

    def _child_text(c: dict) -> str:
        score = f"{c['avg_score']}% average" if c.get("avg_score") is not None else "no mock tests this week"
        lines = [
            f"- {c.get('name','Child')} ({c.get('grade','')}): {c.get('plan_status_label','')}",
            f"  {c.get('mock_tests_count',0)} mock test(s), {score}, "
            f"{c.get('activity_count',0)} AI activity session(s)",
        ]
        if c.get("weak_areas"):
            lines.append(f"  Needs practice: {', '.join(c['weak_areas'][:3])}")
        return "\n".join(lines)

    text = (
        f"This week's progress, {first_name}\n\n"
        + "\n\n".join(_child_text(c) for c in children)
        + f"\n\nView your full dashboard at {_FRONTEND_URL}\n"
        + f"Unsubscribe: {unsubscribe_url}\n"
    )

    subject = "Your weekly progress digest 📊" if len(children) > 1 else f"{children[0].get('name','Your child')}'s weekly progress 📊"
    return subject, html, text


def send_weekly_digest_email(
    to: str,
    parent_name: str,
    children: list[dict],
    unsubscribe_url: str,
    blocking: bool = False,
) -> bool | None:
    """
    Send the weekly parent progress digest.

    blocking=True is required for callers whose process exits right after
    calling this (e.g. the weekly digest cron job) — _send_async's daemon
    thread would otherwise be killed before it finishes sending. Returns the
    send result (True/False) when blocking, else None (fire-and-forget).
    """
    if not to or not children:
        return False if blocking else None

    subject, html, text = _build_weekly_digest_email(parent_name, children, unsubscribe_url)

    if blocking:
        result = _send(to, subject, html, text)
        _log.info("email_service.digest_sent" if result else "email_service.digest_failed",
                   to=to, children=len(children))
        return result

    _send_async(to=to, subject=subject, html=html, text=text)
    _log.info("email_service.digest_queued", to=to, children=len(children))
    return None


def send_teacher_parent_message(
    *,
    to: str,
    parent_name: str,
    teacher_name: str,
    student_name: str,
    subject: str,
    message: str,
) -> bool:
    """Send a teacher's message to an existing parent's email account."""
    if not (to or "").strip():
        return False

    safe_parent = escape((parent_name or "Parent").strip())
    safe_teacher = escape((teacher_name or "Teacher").strip())
    safe_student = escape((student_name or "your child").strip())
    safe_subject = escape((subject or "Update from your child's teacher").strip())
    safe_message = escape((message or "").strip()).replace("\n", "<br>")

    body = f"""
<p style="margin:0 0 16px;font-size:20px;font-weight:900">Message from {safe_teacher}</p>
<p style="margin:0 0 16px;font-size:14px;color:#475569">
  Hello {safe_parent}, here is an update about <strong>{safe_student}</strong>.
</p>
<div style="padding:16px;border:1px solid #e5e7eb;border-radius:10px;background:#f8fafc;
            font-size:14px;line-height:1.7;color:#1e293b">
  {safe_message}
</div>
"""
    html_body = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="Open Parent Dashboard →",
    )
    text = (
        f"Hello {parent_name or 'Parent'},\n\n"
        f"{teacher_name or 'Your teacher'} sent an update about {student_name or 'your child'}:\n\n"
        f"{message.strip()}\n\nOpen the Parent Dashboard: {_FRONTEND_URL}\n"
    )
    return _send(
        to=to.strip(),
        subject=f"{subject.strip() or 'Student update'} — Likha Poha AI",
        html=html_body,
        text=text,
    )


def configured_email_provider() -> str:
    """Return a non-secret provider label for delivery logs and diagnostics."""
    if os.getenv("RESEND_API_KEY", "").strip():
        return "resend"
    if _get_smtp_config():
        return "smtp"
    return "unconfigured"


def send_student_invitation_email(
    *,
    to: str,
    student_name: str,
    teacher_name: str,
    grade: str,
    invite_link: str,
    expiry_days: int = 7,
    stream: str = "",
) -> bool:
    """
    Send a teacher's student invitation email via Resend/SMTP.

    Fires when a teacher invites a student from the Teacher Dashboard's
    Invitations tab. The link takes the student to a public accept-invitation
    page where they set a password and their account is created.

    Non-blocking: call via _send_async for fire-and-forget, or use the
    returned bool from _send() directly when the caller wants to know
    whether the email actually went out.
    """
    if not (to or "").strip():
        return False

    safe_student = escape((student_name or "there").strip())
    safe_teacher = escape((teacher_name or "Your teacher").strip())
    safe_grade   = escape((grade or "").strip())
    safe_stream  = escape((stream or "").strip())

    grade_line = f" for <strong>{safe_grade}</strong>" if safe_grade else ""
    if safe_stream:
        grade_line += f" (<strong>{safe_stream}</strong> stream)"

    body = f"""
<p style="margin:0 0 16px;font-size:20px;font-weight:900">You're invited to Likha Poha AI</p>
<p style="margin:0 0 16px;font-size:14px;color:#475569">
  Hi {safe_student}, <strong>{safe_teacher}</strong> has invited you to join their classroom
  on Likha Poha AI{grade_line}.
</p>
<div style="padding:16px;border:1px solid #e5e7eb;border-radius:10px;background:#f8fafc;
            font-size:14px;line-height:1.7;color:#1e293b">
  Click the button below to set your password and start learning. This invitation
  expires in {expiry_days} days.
</div>
"""
    html_body = _email_shell(
        body_html=body,
        cta_url=invite_link,
        cta_label="Accept Invitation →",
    )
    text_grade = (f" for {grade}" if grade else "") + (f" ({stream} stream)" if stream else "")
    text = (
        f"Hi {student_name or 'there'},\n\n"
        f"{teacher_name or 'Your teacher'} has invited you to join their classroom on "
        f"Likha Poha AI{text_grade}.\n\n"
        f"Accept your invitation: {invite_link}\n\n"
        f"This invitation expires in {expiry_days} days.\n"
    )
    return _send(
        to=to.strip(),
        subject=f"{teacher_name or 'Your teacher'} invited you to Likha Poha AI",
        html=html_body,
        text=text,
    )


_CHAT_STORAGE_ALERT_TO = "likhapohaai@gmail.com"


def send_chat_storage_alert_email(
    total_bytes: int,
    threshold_bytes: int,
    blocking: bool = False,
) -> bool | None:
    """
    Alert the platform team when chat attachment storage crosses a threshold.

    Fires from the chat retention cleanup job when the sum of attachment_size
    across chat_messages is still over the threshold after expired
    messages/files have been purged — i.e. storage is growing from live usage,
    not just an unpruned backlog.

    blocking=True is required for the cron job (process exits right after the
    job returns); the admin-triggered path can leave it fire-and-forget.
    """
    total_gb = total_bytes / (1024 ** 3)
    threshold_gb = threshold_bytes / (1024 ** 3)

    body = f"""
<p style="margin:0 0 16px;font-size:20px;font-weight:900">Chat storage alert</p>
<p style="margin:0 0 16px;font-size:14px;color:#475569">
  Platform chat attachments now total <strong>{total_gb:.2f} GB</strong>, over the
  <strong>{threshold_gb:.0f} GB</strong> alert threshold.
</p>
<div style="padding:16px;border:1px solid #e5e7eb;border-radius:10px;background:#f8fafc;
            font-size:14px;line-height:1.7;color:#1e293b">
  The retention cleanup job already purged everything past its expiry — this total
  is what's left from active/recent chats. Consider tightening the chat retention
  window or file-size limit in Admin &rarr; Chat Settings.
</div>
"""
    html_body = _email_shell(
        body_html=body,
        cta_url=_FRONTEND_URL,
        cta_label="Open Admin Dashboard →",
    )
    text = (
        f"Chat storage alert\n\n"
        f"Platform chat attachments now total {total_gb:.2f} GB, over the "
        f"{threshold_gb:.0f} GB alert threshold.\n\n"
        f"The retention cleanup job already purged everything past its expiry — "
        f"this total is what's left from active/recent chats. Consider tightening "
        f"the chat retention window or file-size limit in Admin -> Chat Settings.\n\n"
        f"{_FRONTEND_URL}\n"
    )

    if blocking:
        result = _send(_CHAT_STORAGE_ALERT_TO, "⚠️ Chat storage over 1 GB — Likha Poha AI", html_body, text)
        _log.info("email_service.chat_storage_alert_sent" if result else "email_service.chat_storage_alert_failed",
                   total_bytes=total_bytes)
        return result

    _send_async(_CHAT_STORAGE_ALERT_TO, "⚠️ Chat storage over 1 GB — Likha Poha AI", html_body, text)
    return None
