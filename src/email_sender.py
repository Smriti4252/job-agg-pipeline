# ...existing code...
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

def send_digest_email():

    load_dotenv()

    def _clean_env(name):
        v = os.getenv(name)
        return v.strip() if isinstance(v, str) and v.strip() != "" else None

    # 🔍 CLEANED DEBUG PRINTS — show exact cleaned string
    SMTP_HOST = _clean_env("SMTP_HOST")
    SMTP_PORT = _clean_env("SMTP_PORT")
    SMTP_USER = _clean_env("SMTP_USER")
    PASSWORD = _clean_env("SMTP_PASSWORD")
    SMTP_FROM = _clean_env("SMTP_FROM")
    RECIPIENT = _clean_env("DIGEST_TO")

    print("DEBUG CLEANED SMTP_HOST  =", repr(SMTP_HOST))
    print("DEBUG CLEANED SMTP_PORT  =", repr(SMTP_PORT))
    print("DEBUG CLEANED SMTP_USER  =", repr(SMTP_USER))
    print("DEBUG CLEANED SMTP_PASS  =", "****" if PASSWORD else None)
    print("DEBUG CLEANED SMTP_FROM  =", repr(SMTP_FROM))
    print("DEBUG CLEANED DIGEST_TO  =", repr(RECIPIENT))
    print("-" * 60)

    # choose header From vs login sender
    SENDER = SMTP_USER or SMTP_FROM
    FROM_HEADER = SMTP_FROM or SENDER

    # Check required fields
    if not SMTP_HOST:
        print(" ERROR: SMTP_HOST is missing!")
        return

    if not SMTP_PORT:
        print(" ERROR: SMTP_PORT is missing!")
        return

    try:
        SMTP_PORT = int(SMTP_PORT)
    except ValueError:
        print(" ERROR: SMTP_PORT is not a valid number:", SMTP_PORT)
        return

    # Find latest digest
    digest_files = sorted(Path("data/digest").glob("*.html"))
    if not digest_files:
        print(" No digest file found.")
        return

    latest_digest = digest_files[-1]
    print(f"📧 Sending digest: {latest_digest}")

    # Read email HTML
    html_content = latest_digest.read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Daily Job Digest"
    msg["From"] = FROM_HEADER

    # allow multiple recipients separated by comma or semicolon
    recipients = []
    if RECIPIENT:
        for part in RECIPIENT.replace(";", ",").split(","):
            part = part.strip()
            if part:
                recipients.append(part)

    if not recipients:
        print(" ERROR: No recipient address provided in DIGEST_TO")
        return

    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    context = ssl.create_default_context()

    try:
        print(f"🔌 Connecting to SMTP: host={repr(SMTP_HOST)}, port={SMTP_PORT}")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            # only attempt login if we have credentials
            if SENDER and PASSWORD:
                server.login(SENDER, PASSWORD)
            server.sendmail(FROM_HEADER, recipients, msg.as_string())

        print(" Email sent successfully!")

    except smtplib.SMTPAuthenticationError as e:
        print(" Authentication failed:", e)
    except Exception as e:
        print(" Error sending email:", e)


if __name__ == "__main__":
    send_digest_email()
# ...existing code...