import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

def send_digest_email():

    load_dotenv()

    # 🔍 BETTER DEBUG PRINTS — show exact raw string including spaces!
    print("DEBUG RAW SMTP_HOST  =", repr(os.getenv("SMTP_HOST")))
    print("DEBUG RAW SMTP_PORT  =", repr(os.getenv("SMTP_PORT")))
    print("DEBUG RAW SMTP_USER  =", repr(os.getenv("SMTP_USER")))
    print("DEBUG RAW SMTP_PASS  =", "****" if os.getenv("SMTP_PASSWORD") else None)
    print("DEBUG RAW SMTP_FROM  =", repr(os.getenv("SMTP_FROM")))
    print("DEBUG RAW DIGEST_TO  =", repr(os.getenv("DIGEST_TO")))
    print("-" * 60)

    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SENDER = os.getenv("SMTP_USER")
    PASSWORD = os.getenv("SMTP_PASSWORD")
    RECIPIENT = os.getenv("DIGEST_TO")

    # Check required fields
    if not SMTP_HOST:
        print(" ERROR: SMTP_HOST is missing!")
        return

    if SMTP_PORT:
        try:
            SMTP_PORT = int(SMTP_PORT)
        except:
            print(" ERROR: SMTP_PORT is not a valid number:", SMTP_PORT)
            return
    else:
        print(" ERROR: SMTP_PORT is missing!")
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
    msg["From"] = SENDER
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(html_content, "html"))

    context = ssl.create_default_context()

    try:
        print(f"🔌 Connecting to SMTP: host={repr(SMTP_HOST)}, port={SMTP_PORT}")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, RECIPIENT, msg.as_string())

        print(" Email sent successfully!")

    except smtplib.SMTPAuthenticationError as e:
        print(" Authentication failed:", e)
    except Exception as e:
        print(" Error sending email:", e)


if __name__ == "__main__":
    send_digest_email()
