import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

def send_digest_email():

    load_dotenv()

    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    SENDER = os.getenv("SMTP_USER")
    PASSWORD = os.getenv("SMTP_PASSWORD")
    RECIPIENT = os.getenv("DIGEST_TO")

    digest_files = sorted(Path("data/digest").glob("*.html"))
    if not digest_files:
        print("❌ No digest file found.")
        return

    latest_digest = digest_files[-1]
    print(f"📧 Sending digest: {latest_digest}")

    # Read HTML
    html_content = latest_digest.read_text(encoding="utf-8")

    # Email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Daily Job Digest"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(html_content, "html"))

    # Secure SSL connection
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SENDER, PASSWORD)
            server.sendmail(SENDER, RECIPIENT, msg.as_string())

        print("✅ Email sent successfully!")

    except smtplib.SMTPAuthenticationError as e:
        print("❌ Authentication failed:", e)
    except Exception as e:
        print("❌ Error sending email:", e)


if __name__ == "__main__":
    send_digest_email()
