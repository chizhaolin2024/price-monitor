import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from .config import Settings


async def notify(settings: Settings, subject: str, message: str) -> list[str]:
    channels: list[str] = []
    if settings.telegram_configured:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": settings.telegram_chat_id, "text": message, "parse_mode": "HTML"},
                )
                resp.raise_for_status()
            channels.append("telegram")
        except Exception as exc:
            print(f"[notifier] telegram failed: {type(exc).__name__}: {exc}")

    if settings.email_configured:
        try:
            await asyncio.to_thread(_send_email, settings, subject, message)
            channels.append("email")
        except Exception as exc:
            print(f"[notifier] email failed: {type(exc).__name__}: {exc}")

    if not channels:
        channels.append("console")
        print(f"[alert:{subject}] {message}")
    return channels


def _send_email(settings: Settings, subject: str, message: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[PriceWatch] {subject}"
    msg["From"] = settings.alert_email_from or settings.smtp_user
    msg["To"] = settings.alert_email_to
    msg.set_content(message)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
