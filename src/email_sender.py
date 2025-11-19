# Loads .env and sends latest HTML digest via SMTP SSL.

import os
import smtplib
import ssl
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

DIGEST_DIR = Path("data/digest")


def _clean_env(name: str):
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) and v.strip() else None


def _latest_digest():
    files = sorted(DIGEST_DIR.glob("*.html"))
    return files[-1] if files else None


def send_digest_email():
    load_dotenv()

    smtp_host = _clean_env("SMTP_HOST")
    smtp_port = _clean_env("SMTP_PORT")
    smtp_user = _clean_env("SMTP_USER")
    smtp_password = _clean_env("SMTP_PASSWORD")
    smtp_from = _clean_env("SMTP_FROM") or smtp_user
    digest_to = _clean_env("DIGEST_TO")

    # sanity checks
    if not (smtp_host and smtp_port and smtp_user and smtp_password and digest_to):
        print("Missing SMTP config in environment. Check .env.")
        print("DEBUG:", smtp_host, smtp_port, smtp_user is not None, bool(digest_to))
        return

    try:
        smtp_port = int(smtp_port)
    except ValueError:
        print("SMTP_PORT must be an integer.")
        return

    recipients = [r.strip() for r in digest_to.replace(";", ",").split(",") if r.strip()]
    if not recipients:
        print("No recipients found in DIGEST_TO.")
        return

    latest = _latest_digest()
    if not latest:
        print("No digest HTML found in data/digest.")
        return

    print(f" Sending digest: {latest}")
    html = latest.read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Daily Job Digest"
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as s:
            s.login(smtp_user, smtp_password)
            s.sendmail(smtp_from, recipients, msg.as_string())
        print(" Email sent successfully!")
    except smtplib.SMTPAuthenticationError as e:
        print("Authentication failed:", e)
    except Exception as e:
        print("Error sending email:", e)


if __name__ == "__main__":
    send_digest_email()
