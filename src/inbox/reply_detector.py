import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from typing import List, Dict, Any
from config.settings import settings
from src.crm.notion_client import NotionClient
from src.notifications.telegram_notifier import TelegramNotifier

class ReplyDetector:
    """
    Scans the Gmail inbox via IMAP to detect incoming replies from pitched curators.
    Features:
    1. Positive reply detection: moves lead to 'Replied' and halts follow-ups.
    2. Opt-out / Blacklist detection: if curator says 'unsubscribe', 'remove', 'stop', 'pass',
       automatically marks them as 'Blacklisted' to protect Gmail sender reputation.
    3. Instant notification alerts.
    """

    OPT_OUT_KEYWORDS = [
        "unsubscribe", "remove me", "take me off", "stop emailing",
        "don't email", "dont email", "not interested", "opt out",
        "spam", "pass", "please stop", "remove from list"
    ]

    def __init__(self, notion_client: NotionClient = None):
        self.notion = notion_client or NotionClient()

    def _decode_str(self, header_value: str) -> str:
        """Decodes RFC 2047 encoded email headers."""
        if not header_value:
            return ""
        decoded_fragments = decode_header(header_value)
        result = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                try:
                    result.append(text.decode(encoding or "utf-8", errors="replace"))
                except Exception:
                    result.append(text.decode("latin1", errors="replace"))
            else:
                result.append(str(text))
        return "".join(result)

    def _get_email_body(self, msg: email.message.Message) -> str:
        """Extracts plain or html text from email payload."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype in ("text/plain", "text/html"):
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="replace") + " "
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
            except Exception:
                pass
        return body.lower()

    def is_opt_out(self, text: str) -> bool:
        """Checks if email text contains any opt-out/blacklist phrasing."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.OPT_OUT_KEYWORDS)

    def scan_for_replies(self) -> List[Dict[str, Any]]:
        """
        Connects to IMAP server, checks recent emails, and matches senders against active leads.
        """
        if not settings.imap_user or not settings.imap_password:
            return []

        all_leads = self.notion.get_all_leads()
        active_leads = {
            lead.email.strip().lower(): lead
            for lead in all_leads
            if lead.status in ("Sent", "Opened", "Follow-up Sent")
        }

        if not active_leads:
            return []

        found_replies: List[Dict[str, Any]] = []

        try:
            mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
            mail.login(settings.imap_user, settings.imap_password)
            mail.select(settings.imap_check_folder)

            # Search unseen emails in inbox
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                mail.close()
                mail.logout()
                return []

            msg_ids = messages[0].split()
            for msg_id in msg_ids:
                res, data = mail.fetch(msg_id, "(RFC822)")
                if res != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract From address
                from_header = self._decode_str(msg.get("From", ""))
                _, sender_email = parseaddr(from_header)
                sender_clean = sender_email.strip().lower()

                subject = self._decode_str(msg.get("Subject", ""))
                in_reply_to = msg.get("In-Reply-To", "")
                body = self._get_email_body(msg)

                if sender_clean in active_leads:
                    matched_lead = active_leads[sender_clean]
                    combined_text = f"{subject} {body}"

                    if self.is_opt_out(combined_text):
                        # Blacklist curator
                        self.notion.record_email_blacklisted(matched_lead.id)
                        TelegramNotifier.send_alert(
                            f"🚫 *Curator Opted Out / Blacklisted:*\n"
                            f"👤 *Name:* {matched_lead.name} ({matched_lead.publication})\n"
                            f"✉️ *Email:* `{sender_clean}`\n"
                            f"📌 Marked as *Blacklisted* to protect sender reputation."
                        )
                        found_replies.append({
                            "lead": matched_lead,
                            "from_email": sender_clean,
                            "subject": subject,
                            "in_reply_to": in_reply_to,
                            "action": "blacklisted"
                        })
                    else:
                        # Regular positive reply
                        self.notion.record_email_replied(matched_lead.id)
                        TelegramNotifier.notify_reply(
                            lead_name=matched_lead.name,
                            publication=matched_lead.publication,
                            email=sender_clean,
                            subject=subject
                        )
                        found_replies.append({
                            "lead": matched_lead,
                            "from_email": sender_clean,
                            "subject": subject,
                            "in_reply_to": in_reply_to,
                            "action": "replied"
                        })

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"[ReplyDetector] Warning: Could not check IMAP inbox: {e}")

        return found_replies
