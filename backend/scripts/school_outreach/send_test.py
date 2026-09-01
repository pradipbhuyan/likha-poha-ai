"""
send_test.py — send ONE real campaign email, for verifying from/reply-to/template
before any real sends go out from the admin console.

Uses the exact same builder + sender as the admin-triggered send
(app.services.school_outreach_service) — not a separate copy — so this test
send is guaranteed to match what a real campaign send actually looks like.

Usage:
    cd backend
    .venv/bin/python scripts/school_outreach/send_test.py \\
        --to pradip.bhuyan@gmail.com \\
        --name "Test Principal" \\
        --school "Demo Public School (Test Send)"
    .venv/bin/python scripts/school_outreach/send_test.py --to X --reminder   # preview the reminder instead
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.school_outreach_service import (  # noqa: E402
    CTA_URL,
    FROM_ADDRESS,
    REPLY_TO,
    SENDER_NAME,
    build_principal_email_html,
    build_principal_email_text,
    build_reminder_email_html,
    build_reminder_email_text,
    send_campaign_email,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, help="Recipient address for this test send")
    parser.add_argument("--name", default="Test Principal")
    parser.add_argument("--school", default="Demo Public School (Test Send)")
    parser.add_argument("--reminder", action="store_true", help="Preview the 7-day reminder instead of the initial email")
    args = parser.parse_args()

    if args.reminder:
        html = build_reminder_email_html(args.name, args.school, CTA_URL)
        text = build_reminder_email_text(args.name, args.school, CTA_URL)
        subject = f"[TEST] Following up — {args.school}"
    else:
        html = build_principal_email_html(args.name, args.school, CTA_URL)
        text = build_principal_email_text(args.name, args.school, CTA_URL)
        subject = f"[TEST] AI-Powered Learning & Revision Platform for Students of {args.school}"

    result = send_campaign_email(to=args.to, subject=subject, html=html, text=text)

    if result.success:
        print(f"Sent. Resend id: {result.detail}")
        print(f"From:     {SENDER_NAME} <{FROM_ADDRESS}>")
        print(f"Reply-To: {REPLY_TO}")
        print(f"To:       {args.to}")
    else:
        print(f"FAILED: {result.detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
