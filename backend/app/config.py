import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    check_interval_seconds: int
    telegram_bot_token: str
    telegram_chat_id: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    alert_email_to: str
    alert_email_from: str
    db_path: str
    static_dir: str

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.alert_email_to)


settings = Settings(
    check_interval_seconds=_get_int("CHECK_INTERVAL_SECONDS", 3600),
    telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
    telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    smtp_host=os.getenv("SMTP_HOST", "").strip(),
    smtp_port=_get_int("SMTP_PORT", 465),
    smtp_user=os.getenv("SMTP_USER", "").strip(),
    smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
    alert_email_to=os.getenv("ALERT_EMAIL_TO", "").strip(),
    alert_email_from=os.getenv("ALERT_EMAIL_FROM", os.getenv("SMTP_USER", "")).strip(),
    db_path=os.getenv("DB_PATH", str(BACKEND_DIR / "data" / "pricewatch.db")),
    static_dir=os.getenv("STATIC_DIR", str(BACKEND_DIR / ".." / "frontend" / "dist")),
)
