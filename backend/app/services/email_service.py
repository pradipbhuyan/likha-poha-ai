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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.logger_service import get_logger

_log = get_logger("email_service")

_BRAND_COLOR = "#6366f1"
_FRONTEND_URL = os.getenv("FRONTEND_URL", "https://likhapoha.in")
# Logo always uses the production domain — never localhost — so it renders in email clients
_LOGO_URL = "https://likhapoha.in/favicon.png"


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
    if _send_via_resend(to, subject, html, text):
        return True

    # Fallback: SMTP (for local dev / non-Railway environments)
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
     "Hard problems from NCERT Exemplar with instant AI explanations â "
     "essential for scoring 90%+ in board exams."),
    ("📊", "Progress & Analytics",
     "Track lessons completed, mock test scores, weak topics, and AI usage — "
     "all in your <strong>Analytics</strong> dashboard."),
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
    <strong>📌 Free Tier limits:</strong> limited AI lessons, 5 mock tests/day,
    and limited Doubt answers. Upgrade to <strong>Premium (&#8377;299/month)</strong>
    for unlimited access, NCERT Exemplar, and advanced formula sheets.
  </p>
</div>"""


# ── Public API ────────────────────────────────────────────────────────────────

def send_welcome_email(
    to: str,
    name: str,
    role: str,
    is_paid: bool = False,
    plan_name: str = "",
) -> None:
    """
    Send a welcome email to a newly registered user (student, parent, or teacher).

    Called after:
      - Free Tier signup  (signup_free)
      - Paid signup       (complete_signup)
      - Offer code signup (signup_with_offer_code)
      - Google OAuth      (oauth_complete_profile — first time role is set)

    Non-blocking: always fires in a background thread.
    """
    if not to:
        return

    first_name = (name or "there").split()[0]
    role_clean = (role or "student").lower()
    is_parent  = role_clean == "parent"

    plan_badge = ""
    if is_paid and plan_name:
        plan_badge = (
            f'<span style="display:inline-block;background:#dcfce7;color:#166534;'
            f'border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;'
            f'margin-bottom:18px">'
            f'&#10003; {plan_name} activated</span><br>'
        )

    features_html = _feature_table(_FEATURES_PARENT if is_parent else _FEATURES_STUDENT)
    free_notice   = "" if is_paid else _FREE_TIER_NOTICE

    if is_parent:
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
<p style="margin:0 0 20px;font-size:24px;font-weight:900;letter-spacing:-0.02em">
  Welcome, {first_name}! 🎉
</p>
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

    text = (
        f"Welcome to Likha Poha AI, {first_name}!\n\n"
        f"Your account is ready. Visit {_FRONTEND_URL} to start learning.\n\n"
        f"Key features: AI Lessons | Mock Tests | Ask Doubts | Formula Sheets | Progress Analytics\n"
        + (f"\nYour plan: {plan_name}\n" if is_paid and plan_name else
           f"\nFree Tier: 5 mock tests/day, limited lessons. Upgrade anytime at {_FRONTEND_URL}.\n")
    )

    _send_async(
        to=to,
        subject=f"Welcome to Likha Poha AI, {first_name}! 🎉",
        html=html,
        text=text,
    )
    _log.info("email_service.welcome_queued", to=to, role=role_clean, is_paid=is_paid)


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
