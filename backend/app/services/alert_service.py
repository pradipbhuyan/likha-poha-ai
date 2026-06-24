"""
Alert Service
=============
Sends internal admin alert emails when the platform hits AI provider rate
limits or quota errors that affect paying users.

Uses a per-process cooldown (default 15 minutes) so a rate-limit storm
doesn't generate hundreds of emails — one notification per window is enough.

Configuration (environment variables):
  ALERT_SMTP_HOST     — SMTP hostname, default: smtp.gmail.com
  ALERT_SMTP_PORT     — SMTP port, default: 587
  ALERT_SMTP_USER     — Gmail address that sends the alert
  ALERT_SMTP_PASSWORD — Gmail App Password (not the account password)
  ALERT_TO_EMAIL      — Recipient address, default: likhapohai@gmail.com

If ALERT_SMTP_USER or ALERT_SMTP_PASSWORD are not set, alerting is silently
skipped so the platform never breaks due to a missing email config.
"""

import os
import smtplib
import threading
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.logger_service import get_logger

_log = get_logger("alert_service")

# ── Cooldown state ────────────────────────────────────────────────────────────
_lock = threading.Lock()
_last_rate_limit_alert: dict[str, float] = {}   # feature → last sent timestamp
COOLDOWN_SECONDS = 15 * 60   # 15 minutes between alerts per feature


def _should_send(feature: str) -> bool:
    """Return True if enough time has passed since the last alert for this feature."""
    now = time.monotonic()
    with _lock:
        last = _last_rate_limit_alert.get(feature, 0)
        if now - last >= COOLDOWN_SECONDS:
            _last_rate_limit_alert[feature] = now
            return True
    return False


# ── Email config ──────────────────────────────────────────────────────────────
def _get_smtp_config() -> dict | None:
    """Return SMTP config from environment, or None if not configured."""
    user = os.getenv("ALERT_SMTP_USER", "").strip()
    password = os.getenv("ALERT_SMTP_PASSWORD", "").strip()
    if not user or not password:
        return None
    return {
        "host": os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("ALERT_SMTP_PORT", "587")),
        "user": user,
        "password": password,
        "to": os.getenv("ALERT_TO_EMAIL", "likhapohai@gmail.com"),
    }


def _send_email(subject: str, body_html: str, body_text: str) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    cfg = _get_smtp_config()
    if not cfg:
        _log.warning("alert_service.smtp_not_configured: ALERT_SMTP_USER/PASSWORD not set")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["user"]
        msg["To"] = cfg["to"]
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], [cfg["to"]], msg.as_string())

        _log.info("alert_service.email_sent", to=cfg["to"], subject=subject)
        return True

    except Exception as exc:
        _log.error("alert_service.email_failed", error=str(exc))
        return False


def _send_in_background(subject: str, body_html: str, body_text: str) -> None:
    """Fire-and-forget: send alert email in a daemon thread so routes don't block."""
    t = threading.Thread(
        target=_send_email,
        args=(subject, body_html, body_text),
        daemon=True,
    )
    t.start()


# ── Public API ────────────────────────────────────────────────────────────────

def alert_rate_limit(
    feature: str,
    username: str,
    error_detail: str,
    grade: str = "",
    subject: str = "",
    chapter: str = "",
) -> None:
    """
    Send a rate-limit alert email if the cooldown has elapsed.

    Call this from route exception handlers when a 429 / quota error
    affects a real user request.  The email is sent in a background thread
    so the route response is never delayed.
    """
    if not _should_send(feature):
        return   # Still within cooldown window — skip

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    feature_label = feature.replace("_", " ").title()
    context_parts = [p for p in [grade, subject, chapter] if p]
    context_str = " / ".join(context_parts) if context_parts else "—"

    body_html = f"""
<html><body style="font-family:sans-serif;color:#1e293b;padding:20px">
<h2 style="color:#dc2626">⚠️ AI Rate Limit Alert — {feature_label}</h2>
<table style="border-collapse:collapse;width:100%;max-width:600px">
  <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Time</td>
      <td style="padding:8px">{ts}</td></tr>
  <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Feature</td>
      <td style="padding:8px">{feature_label}</td></tr>
  <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">User</td>
      <td style="padding:8px">{username}</td></tr>
  <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Context</td>
      <td style="padding:8px">{context_str}</td></tr>
  <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Error</td>
      <td style="padding:8px;color:#dc2626;font-size:0.85rem">{error_detail[:400]}</td></tr>
</table>
<p style="margin-top:20px;font-size:0.88rem;color:#64748b">
  This alert fires at most once every 15 minutes per feature to avoid spam.<br>
  Check your AI provider dashboard to top up or rotate API keys.
</p>
</body></html>
"""

    body_text = (
        f"AI Rate Limit Alert — {feature_label}\n"
        f"Time:    {ts}\n"
        f"Feature: {feature_label}\n"
        f"User:    {username}\n"
        f"Context: {context_str}\n"
        f"Error:   {error_detail[:400]}\n\n"
        "Check your AI provider dashboard to top up or rotate API keys.\n"
        "(This alert fires at most once every 15 minutes per feature.)"
    )

    _send_in_background(
        subject=f"[LikhaPoha] ⚠️ AI Rate Limit — {feature_label} ({ts})",
        body_html=body_html,
        body_text=body_text,
    )
