import os
import json
import random
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Notion CRM
    notion_api_key: str = Field(default="", alias="NOTION_API_KEY")
    notion_database_id: str = Field(default="", alias="NOTION_DATABASE_ID")
    use_notion: bool = Field(default=False)

    # Sender Profile
    sender_name: str = Field(default="Kxrn Gupta", alias="SENDER_NAME")
    sender_email: str = Field(default="chitesh.gupta@gmail.com", alias="SENDER_EMAIL")

    # Email Engine
    email_provider: Literal["smtp", "gmail_api", "resend"] = Field(
        default="smtp", alias="EMAIL_PROVIDER"
    )
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="chitesh.gupta@gmail.com", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")

    gmail_credentials_file: str = Field(
        default="config/credentials.json", alias="GMAIL_CREDENTIALS_FILE"
    )
    gmail_token_file: str = Field(
        default="config/token.json", alias="GMAIL_TOKEN_FILE"
    )

    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")

    # IMAP Settings
    imap_host: str = Field(default="imap.gmail.com", alias="IMAP_HOST")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    imap_user: str = Field(default="chitesh.gupta@gmail.com", alias="IMAP_USER")
    imap_password: str = Field(default="", alias="IMAP_PASSWORD")
    imap_check_folder: str = Field(default="INBOX", alias="IMAP_CHECK_FOLDER")

    # Tracking Server
    tracking_server_url: str = Field(
        default="https://kxrn-pr-tracker.vercel.app", alias="TRACKING_SERVER_URL"
    )

    # Throttling & Limits
    min_delay_seconds: int = Field(default=180, alias="MIN_DELAY_SECONDS")
    max_delay_seconds: int = Field(default=420, alias="MAX_DELAY_SECONDS")
    daily_send_limit: int = Field(default=30, alias="DAILY_SEND_LIMIT")
    follow_up_after_days: int = Field(default=4, alias="FOLLOW_UP_AFTER_DAYS")
    pause_on_weekends: bool = Field(default=True, alias="PAUSE_ON_WEEKENDS")

    # Music & Pitch Defaults
    default_track_name: str = Field(default="Midnight Reverie")
    default_stream_link: str = Field(default="https://open.spotify.com/artist/kxrn-gupta")
    default_bio_link: str = Field(default="https://kxrn.is-a.dev/press")

    # Telegram alerts (optional)
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")

    def get_random_delay(self) -> int:
        """Returns a randomized delay in seconds within configured bounds."""
        min_d = max(1, self.min_delay_seconds)
        max_d = max(min_d, self.max_delay_seconds)
        return random.randint(min_d, max_d)


settings = Settings()

# Overlay persisted UI config if available
_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app_config.json")
if os.path.exists(_config_path):
    try:
        with open(_config_path, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            for _k, _v in _data.items():
                if hasattr(settings, _k):
                    setattr(settings, _k, _v)
    except Exception:
        pass
