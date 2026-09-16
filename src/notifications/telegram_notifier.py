import requests
from typing import Optional
from config.settings import settings

class TelegramNotifier:
    """Sends real-time alerts to the artist/user when high-value events happen."""

    @classmethod
    def send_alert(cls, message: str) -> bool:
        token = settings.telegram_bot_token
        chat_id = settings.telegram_chat_id

        if not token or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            resp = requests.post(url, json=payload, timeout=8)
            return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    def notify_reply(cls, lead_name: str, publication: str, email: str, subject: str) -> bool:
        text = (
            f"🔥 *Cold Email Reply Received!*\n\n"
            f"👤 *From:* {lead_name} ({publication})\n"
            f"✉️ *Email:* `{email}`\n"
            f"📌 *Subject:* {subject}\n\n"
            f"⚡ Check your inbox and follow up manually!"
        )
        return cls.send_alert(text)

    @classmethod
    def notify_open(cls, lead_name: str, publication: str, open_count: int) -> bool:
        text = (
            f"👀 *Email Opened by Curator!*\n\n"
            f"👤 *Curator:* {lead_name} ({publication})\n"
            f"📊 *Total Opens:* {open_count}\n"
        )
        return cls.send_alert(text)
