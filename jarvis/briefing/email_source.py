"""Fetch recent emails via IMAP."""

from __future__ import annotations

import email
import imaplib
import ssl
from dataclasses import dataclass
from email.header import decode_header

from ..config import EmailConfig


@dataclass
class EmailSummary:
    sender: str
    subject: str
    snippet: str
    date: str


def fetch_emails(cfg: EmailConfig) -> list[EmailSummary]:
    """Fetch recent emails and return structured summaries."""
    if not cfg.username or not cfg.password:
        return []

    try:
        # Explicit TLS certificate validation
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(cfg.imap_server, ssl_context=context)
        mail.login(cfg.username, cfg.password)
        mail.select("inbox")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        # Take the most recent N
        ids = ids[-cfg.max_emails:]

        results = []
        for eid in reversed(ids):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_header(msg["Subject"] or "(no subject)")
            sender = _decode_header(msg["From"] or "unknown")
            date = msg["Date"] or ""

            body = _get_body(msg)
            snippet = body[:300].strip() if body else ""

            results.append(EmailSummary(
                sender=sender, subject=subject, snippet=snippet, date=date
            ))

        mail.logout()
        return results
    except imaplib.IMAP4.error:
        return [EmailSummary(sender="error", subject="IMAP authentication failed", snippet="", date="")]
    except ssl.SSLCertVerificationError:
        return [EmailSummary(sender="error", subject="SSL certificate verification failed", snippet="", date="")]
    except Exception:
        return [EmailSummary(sender="error", subject="Could not fetch emails", snippet="", date="")]


def _decode_header(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _get_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="replace")
    return ""
