import logging
import os
import smtplib
from email.message import EmailMessage
from threading import Event, Lock, Thread

from config import db_cursor, get_db_connection

logger = logging.getLogger(__name__)
_worker_lock = Lock()
_worker_wakeup = Event()
_worker_thread = None


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
    try:
        with db_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO email_outbox (recipient, subject, body) VALUES (%s, %s, %s)",
                (to_email, subject, body),
            )
            message_id = cursor.lastrowid
        _worker_wakeup.set()
        return message_id
    except Exception as exc:
        logger.error("Could not enqueue email notification: %s", exc)
        return None


def _claim_message():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        connection.start_transaction()
        cursor.execute(
            """
            SELECT id, recipient, subject, body, attempts
            FROM email_outbox
            WHERE status IN ('pending', 'failed')
              AND next_attempt_at <= NOW() AND attempts < 5
            ORDER BY id
            LIMIT 1
            FOR UPDATE
            """
        )
        message = cursor.fetchone()
        if not message:
            connection.commit()
            return None
        cursor.execute(
            "UPDATE email_outbox SET status = 'processing', attempts = attempts + 1 WHERE id = %s",
            (message["id"],),
        )
        connection.commit()
        return message
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _finish_message(message, delivered):
    with db_cursor(commit=True) as cursor:
        if delivered:
            cursor.execute(
                """
                UPDATE email_outbox
                SET status = 'sent', sent_at = NOW(), last_error = NULL
                WHERE id = %s
                """,
                (message["id"],),
            )
        else:
            delay_seconds = min(60 * (2 ** message["attempts"]), 3600)
            cursor.execute(
                """
                UPDATE email_outbox
                SET status = IF(attempts >= 5, 'failed', 'pending'),
                    next_attempt_at = DATE_ADD(NOW(), INTERVAL %s SECOND),
                    last_error = 'SMTP delivery failed'
                WHERE id = %s
                """,
                (delay_seconds, message["id"]),
            )


def _notification_worker():
    while True:
        try:
            message = _claim_message()
            if message:
                delivered = send_email(
                    message["recipient"], message["subject"], message["body"]
                )
                _finish_message(message, delivered)
                continue
        except Exception as exc:
            logger.warning("Email outbox worker failed: %s", exc)
        _worker_wakeup.wait(30)
        _worker_wakeup.clear()


def start_notification_worker():
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        try:
            with db_cursor(commit=True) as cursor:
                cursor.execute(
                    """
                    UPDATE email_outbox
                    SET status = 'pending'
                    WHERE status = 'processing'
                      AND updated_at < DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                    """
                )
        except Exception as exc:
            logger.warning("Email outbox recovery deferred: %s", exc)
        _worker_thread = Thread(
            target=_notification_worker,
            name="issueflow-email-outbox",
            daemon=True,
        )
        _worker_thread.start()
