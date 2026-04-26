from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> str:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "noreply@vrptw.local")

    if not smtp_host:
        print(
            f"[MAIL-CONSOLE] To: {to_email}\\nSubject: {subject}\\n{body}\\n")
        if html_body:
            print(f"[MAIL-CONSOLE-HTML] {html_body}\\n")
        return "console"

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    return "smtp"
