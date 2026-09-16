import os
import json
from typing import Dict, Any
from config.settings import settings

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app_config.json")

class ConfigStore:
    """
    Manages persistent application settings in data/app_config.json.
    Eliminates the need for manual .env file editing and allows instant in-app configuration.
    """

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            "sender_name": settings.sender_name or "Kxrn Gupta",
            "sender_email": settings.sender_email or "chitesh.gupta@gmail.com",
            "email_provider": settings.email_provider or "smtp",
            "smtp_host": settings.smtp_host or "smtp.gmail.com",
            "smtp_port": settings.smtp_port or 587,
            "smtp_user": settings.smtp_user or settings.sender_email or "chitesh.gupta@gmail.com",
            "smtp_password": settings.smtp_password or "",
            "imap_host": settings.imap_host or "imap.gmail.com",
            "imap_port": settings.imap_port or 993,
            "imap_user": settings.imap_user or settings.sender_email or "chitesh.gupta@gmail.com",
            "imap_password": settings.imap_password or "",
            "imap_check_folder": settings.imap_check_folder or "INBOX",
            "notion_api_key": settings.notion_api_key or "",
            "notion_database_id": settings.notion_database_id or "",
            "use_notion": bool(settings.notion_api_key and settings.notion_database_id),
            "tracking_server_url": settings.tracking_server_url or "https://kxrn-pr-tracker.vercel.app",
            "min_delay_seconds": settings.min_delay_seconds or 180,
            "max_delay_seconds": settings.max_delay_seconds or 420,
            "daily_send_limit": settings.daily_send_limit or 30,
            "follow_up_after_days": settings.follow_up_after_days or 4,
            "pause_on_weekends": getattr(settings, "pause_on_weekends", True),
            "telegram_bot_token": settings.telegram_bot_token or "",
            "telegram_chat_id": settings.telegram_chat_id or "",
            "default_track_name": "Midnight Reverie",
            "default_stream_link": "https://open.spotify.com/artist/kxrn-gupta",
            "default_bio_link": "https://kxrn.is-a.dev/press",
        }

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """Loads config from disk, merging with defaults."""
        defaults = cls.get_default_config()
        if not os.path.exists(CONFIG_FILE):
            return defaults

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
                return defaults
        except Exception:
            return defaults

    @classmethod
    def save(cls, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Saves config to disk and updates runtime settings object in memory."""
        current = cls.get_default_config()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    current.update(json.load(f))
            except Exception:
                pass

        current.update(new_config)

        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)

        # Synchronize global settings object in memory
        cls.apply_to_settings(current)
        return current

    @classmethod
    def apply_to_settings(cls, config: Dict[str, Any]) -> None:
        """Applies configuration directly to the live settings instance."""
        for key, val in config.items():
            if hasattr(settings, key):
                setattr(settings, key, val)
        # Also sync imap credentials if not explicitly set separately
        if config.get("smtp_user") and not config.get("imap_user"):
            settings.imap_user = config["smtp_user"]
        if config.get("smtp_password") and not config.get("imap_password"):
            settings.imap_password = config["smtp_password"]
