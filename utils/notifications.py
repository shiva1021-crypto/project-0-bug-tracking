import logging
import os
import smtplib
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage


logger = logging.getLogger(__name__)
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="issueflow-email")


def send_email(to_email, subject, body):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")

    if not host or not sender or not to_email:
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return True
    except Exception as exc:
        logger.warning("Email notification failed: %s", exc)
        return False


def queue_email(to_email, subject, body):
    if not to_email:
        return None
    return _email_executor.submit(send_email, to_email, subject, body)
