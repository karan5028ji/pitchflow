import os
import uuid
import smtplib
import requests
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Optional, Dict, Any
from config.settings import settings

class DispatchResult:
    def __init__(self, success: bool, message_id: str, error: Optional[str] = None):
        self.success = success
        self.message_id = message_id
        self.error = error

    def __repr__(self):
        return f"<DispatchResult success={self.success} message_id={self.message_id} error={self.error}>"


class BaseEmailProvider(ABC):
    @abstractmethod
    def send(self, msg: MIMEMultipart, recipient_email: str) -> DispatchResult:
        pass


class SmtpEmailProvider(BaseEmailProvider):
    """Sends email via standard SMTP with STARTTLS (e.g., Gmail App Password)."""

    def send(self, msg: MIMEMultipart, recipient_email: str) -> DispatchResult:
        message_id = msg.get("Message-ID", "")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.sender_email, [recipient_email], msg.as_string())
            return DispatchResult(success=True, message_id=message_id)
        except Exception as e:
            return DispatchResult(success=False, message_id=message_id, error=str(e))


class ResendEmailProvider(BaseEmailProvider):
    """Sends email via Resend API (https://resend.com)."""

    def send(self, msg: MIMEMultipart, recipient_email: str) -> DispatchResult:
        message_id = msg.get("Message-ID", "")
        if not settings.resend_api_key:
            return DispatchResult(success=False, message_id=message_id, error="Resend API key missing.")

        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json"
        }

        # Extract text and html payloads from MIMEMultipart
        html_content = ""
        text_content = ""
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                html_content = part.get_payload(decode=True).decode()
            elif ct == "text/plain":
                text_content = part.get_payload(decode=True).decode()

        payload = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [recipient_email],
            "subject": msg.get("Subject", ""),
            "html": html_content,
            "text": text_content,
            "headers": {
                "Message-ID": message_id
            }
        }

        if msg.get("In-Reply-To"):
            payload["headers"]["In-Reply-To"] = msg.get("In-Reply-To")
            payload["headers"]["References"] = msg.get("References")

        try:
            resp = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                res_data = resp.json()
                return DispatchResult(success=True, message_id=res_data.get("id", message_id))
            return DispatchResult(success=False, message_id=message_id, error=f"Resend error: {resp.text}")
        except Exception as e:
            return DispatchResult(success=False, message_id=message_id, error=str(e))


class GmailApiEmailProvider(BaseEmailProvider):
    """Sends email directly via Google Gmail API (OAuth 2.0)."""

    def send(self, msg: MIMEMultipart, recipient_email: str) -> DispatchResult:
        message_id = msg.get("Message-ID", "")
        try:
            import base64
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
            creds = None
            if os.path.exists(settings.gmail_token_file):
                creds = Credentials.from_authorized_user_file(settings.gmail_token_file, SCOPES)

            if not creds or not creds.valid:
                if not os.path.exists(settings.gmail_credentials_file):
                    return DispatchResult(
                        success=False,
                        message_id=message_id,
                        error=f"Gmail credentials not found at {settings.gmail_credentials_file}. Consider using SMTP."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(settings.gmail_credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(settings.gmail_token_file, "w") as token:
                    token.write(creds.to_json())

            service = build("gmail", "v1", credentials=creds)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            body = {"raw": raw}
            if msg.get("threadId"):
                body["threadId"] = msg.get("threadId")

            sent_msg = service.users().messages().send(userId="me", body=body).execute()
            return DispatchResult(success=True, message_id=sent_msg.get("id", message_id))
        except Exception as e:
            return DispatchResult(success=False, message_id=message_id, error=str(e))


class EmailDispatcher:
    """
    Central dispatcher that creates RFC 2822 multipart emails
    and dispatches via the active provider (SMTP / Gmail API / Resend).
    """

    def __init__(self):
        provider_type = settings.email_provider.lower()
        if provider_type == "resend":
            self.provider = ResendEmailProvider()
        elif provider_type == "gmail_api":
            self.provider = GmailApiEmailProvider()
        else:
            self.provider = SmtpEmailProvider()

    def build_message(
        self,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.sender_name} <{settings.sender_email}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="kxrn.music")

        # In-thread follow-up headers
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = references or in_reply_to

        # Attach text & html representations
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        return msg

    def send(
        self,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> DispatchResult:
        msg = self.build_message(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            in_reply_to=in_reply_to,
            references=references
        )
        return self.provider.send(msg, recipient_email)
