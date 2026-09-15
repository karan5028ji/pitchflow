import os
import json
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from config.settings import settings
from src.crm.schemas import Lead, LeadStatus

class NotionClient:
    """
    Interacts with Notion API (v1) to query and update cold outreach leads.
    Includes a local JSON fallback if Notion credentials are not yet configured.
    """

    NOTION_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"
    LOCAL_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "local_leads.json")

    def __init__(self):
        self.api_key = settings.notion_api_key
        self.database_id = settings.notion_database_id
        self.is_configured = bool(getattr(settings, "use_notion", False) and self.api_key and self.database_id and not self.api_key.startswith("secret_your"))

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # =========================================================================
    # Notion API Methods
    # =========================================================================

    def verify_connection(self) -> Dict[str, Any]:
        """Tests connection to Notion database."""
        if not self.is_configured:
            return {"status": "unconfigured", "message": "Using local offline database (data/local_leads.json)."}
        url = f"{self.BASE_URL}/databases/{self.database_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                title_list = data.get("title", [])
                db_name = title_list[0].get("plain_text", "Untitled") if title_list else "Connected"
                return {"status": "connected", "database_name": db_name}
            return {"status": "error", "code": resp.status_code, "message": resp.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_leads_by_status(self, status: LeadStatus) -> List[Lead]:
        """Fetches all leads currently in a given status."""
        if not self.is_configured:
            return [l for l in self._load_local_leads() if l.status == status]

        url = f"{self.BASE_URL}/databases/{self.database_id}/query"
        payload = {
            "filter": {
                "property": "Status",
                "status": {
                    "equals": status
                }
            }
        }
        leads: List[Lead] = []
        has_more = True
        start_cursor = None

        while has_more:
            if start_cursor:
                payload["start_cursor"] = start_cursor
            try:
                resp = requests.post(url, headers=self._headers(), json=payload, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for page in data.get("results", []):
                    lead = self._parse_notion_page(page)
                    if lead:
                        leads.append(lead)
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            except Exception:
                break

        return leads

    def get_all_leads(self) -> List[Lead]:
        """Fetches all leads regardless of status."""
        if not self.is_configured:
            return self._load_local_leads()

        url = f"{self.BASE_URL}/databases/{self.database_id}/query"
        leads: List[Lead] = []
        has_more = True
        start_cursor = None

        while has_more:
            payload = {}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            try:
                resp = requests.post(url, headers=self._headers(), json=payload, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for page in data.get("results", []):
                    lead = self._parse_notion_page(page)
                    if lead:
                        leads.append(lead)
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            except Exception:
                break

        return leads

    def get_lead_by_id(self, lead_id: str) -> Optional[Lead]:
        """Fetches a specific lead by page/record ID."""
        if not self.is_configured:
            for l in self._load_local_leads():
                if l.id == lead_id:
                    return l
            return None

        url = f"{self.BASE_URL}/pages/{lead_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                return self._parse_notion_page(resp.json())
        except Exception:
            pass
        return None

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Finds a lead matching an email address."""
        email_clean = email.strip().lower()
        if not self.is_configured:
            for l in self._load_local_leads():
                if l.email.strip().lower() == email_clean:
                    return l
            return None

        url = f"{self.BASE_URL}/databases/{self.database_id}/query"
        payload = {
            "filter": {
                "property": "Email",
                "email": {
                    "equals": email_clean
                }
            }
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return self._parse_notion_page(results[0])
        except Exception:
            pass
        return None

    def record_email_sent(self, lead_id: str, message_id: str, thread_id: Optional[str] = None) -> bool:
        """Updates lead after sending initial outreach."""
        now_iso = datetime.now().isoformat()
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    l.status = "Sent"
                    l.send_count = l.send_count + 1
                    l.sent_at = datetime.now()
                    l.message_id = message_id
                    l.thread_id = thread_id
                    break
            self._save_local_leads(leads)
            return True

        lead = self.get_lead_by_id(lead_id)
        current_send_count = lead.send_count if lead else 0

        properties = {
            "Status": {"status": {"name": "Sent"}},
            "Sent At": {"date": {"start": now_iso}},
            "Send Count": {"number": current_send_count + 1},
            "Message ID": {"rich_text": [{"text": {"content": message_id}}]},
        }
        if thread_id:
            properties["Thread ID"] = {"rich_text": [{"text": {"content": thread_id}}]}

        return self._update_page(lead_id, properties)

    def record_follow_up_sent(self, lead_id: str, message_id: str) -> bool:
        """Updates lead after sending in-thread follow-up."""
        now_iso = datetime.now().isoformat()
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    l.status = "Follow-up Sent"
                    l.send_count = l.send_count + 1
                    l.message_id = message_id
                    break
            self._save_local_leads(leads)
            return True

        lead = self.get_lead_by_id(lead_id)
        current_send_count = lead.send_count if lead else 1

        properties = {
            "Status": {"status": {"name": "Follow-up Sent"}},
            "Send Count": {"number": current_send_count + 1},
            "Message ID": {"rich_text": [{"text": {"content": message_id}}]},
        }
        return self._update_page(lead_id, properties)

    def record_email_opened(self, lead_id: str) -> bool:
        """Updates open count, last opened timestamp, and moves to 'Opened' if currently 'Sent'."""
        now_iso = datetime.now().isoformat()
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    l.open_count = (l.open_count or 0) + 1
                    l.last_opened_at = datetime.now()
                    if l.status in ("Sent", "Follow-up Sent"):
                        l.status = "Opened"
                    break
            self._save_local_leads(leads)
            return True

        lead = self.get_lead_by_id(lead_id)
        current_opens = lead.open_count if lead else 0
        new_status = "Opened" if (lead and lead.status in ("Sent", "Follow-up Sent")) else (lead.status if lead else "Opened")

        properties = {
            "Status": {"status": {"name": new_status}},
            "Open Count": {"number": current_opens + 1},
            "Last Opened At": {"date": {"start": now_iso}},
        }
        return self._update_page(lead_id, properties)

    def record_email_replied(self, lead_id: str) -> bool:
        """Moves lead to 'Replied' and halts any further outreach."""
        now_iso = datetime.now().isoformat()
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    l.status = "Replied"
                    l.replied_at = datetime.now()
                    break
            self._save_local_leads(leads)
            return True

        properties = {
            "Status": {"status": {"name": "Replied"}},
            "Replied At": {"date": {"start": now_iso}},
        }
        return self._update_page(lead_id, properties)

    def record_email_blacklisted(self, lead_id: str) -> bool:
        """Moves lead to 'Blacklisted' and prevents any future emails."""
        now_iso = datetime.now().isoformat()
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    l.status = "Blacklisted"
                    break
            self._save_local_leads(leads)
            return True

        properties = {
            "Status": {"status": {"name": "Blacklisted"}},
        }
        return self._update_page(lead_id, properties)


    def add_lead(self, name: str, email: str, publication: str = "", persona: str = "Journalist", recent_work: str = "") -> str:
        """Creates a new lead card in Notion or local DB."""
        if not self.is_configured:
            leads = self._load_local_leads()
            import uuid
            new_id = f"local_{uuid.uuid4().hex[:8]}"
            lead = Lead(
                id=new_id,
                name=name,
                email=email,
                publication=publication or "your platform",
                persona=persona,
                recent_work=recent_work,
                status="To Contact"
            )
            leads.append(lead)
            self._save_local_leads(leads)
            return new_id

        url = f"{self.BASE_URL}/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": name}}]},
                "Email": {"email": email},
                "Publication / Platform": {"rich_text": [{"text": {"content": publication}}]},
                "Persona": {"select": {"name": persona}},
                "Recent Work / Article": {"rich_text": [{"text": {"content": recent_work}}]},
                "Status": {"status": {"name": "To Contact"}},
                "Send Count": {"number": 0},
                "Open Count": {"number": 0},
            }
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json().get("id", "")
        except Exception:
            pass
        return ""

    def _update_page(self, page_id: str, properties: Dict[str, Any]) -> bool:
        url = f"{self.BASE_URL}/pages/{page_id}"
        payload = {"properties": properties}
        try:
            resp = requests.patch(url, headers=self._headers(), json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def _parse_notion_page(self, page: Dict[str, Any]) -> Optional[Lead]:
        try:
            props = page.get("properties", {})
            page_id = page.get("id")

            # Extract Name
            name = "Music Curator"
            title_objs = props.get("Name", {}).get("title", [])
            if title_objs:
                name = title_objs[0].get("plain_text", name)

            # Extract Email
            email = props.get("Email", {}).get("email", "")
            if not email:
                return None

            # Extract Publication
            publication = "your platform"
            pub_objs = props.get("Publication / Platform", {}).get("rich_text", [])
            if pub_objs:
                publication = pub_objs[0].get("plain_text", publication)

            # Extract Persona
            persona = "Journalist"
            persona_obj = props.get("Persona", {}).get("select")
            if persona_obj:
                persona = persona_obj.get("name", persona)

            # Extract Recent Work
            recent_work = None
            work_objs = props.get("Recent Work / Article", {}).get("rich_text", [])
            if work_objs:
                recent_work = work_objs[0].get("plain_text")

            # Extract Status
            status = "To Contact"
            status_obj = props.get("Status", {}).get("status")
            if status_obj:
                status = status_obj.get("name", status)

            # Counts & Dates
            send_count = props.get("Send Count", {}).get("number") or 0
            open_count = props.get("Open Count", {}).get("number") or 0

            sent_at_val = props.get("Sent At", {}).get("date")
            sent_at = datetime.fromisoformat(sent_at_val["start"]) if sent_at_val and sent_at_val.get("start") else None

            last_opened_val = props.get("Last Opened At", {}).get("date")
            last_opened_at = datetime.fromisoformat(last_opened_val["start"]) if last_opened_val and last_opened_val.get("start") else None

            replied_at_val = props.get("Replied At", {}).get("date")
            replied_at = datetime.fromisoformat(replied_at_val["start"]) if replied_at_val and replied_at_val.get("start") else None

            # Message IDs
            msg_objs = props.get("Message ID", {}).get("rich_text", [])
            message_id = msg_objs[0].get("plain_text") if msg_objs else None

            thread_objs = props.get("Thread ID", {}).get("rich_text", [])
            thread_id = thread_objs[0].get("plain_text") if thread_objs else None

            return Lead(
                id=page_id,
                name=name,
                email=email,
                publication=publication,
                persona=persona,
                recent_work=recent_work,
                status=status,
                send_count=send_count,
                open_count=open_count,
                sent_at=sent_at,
                last_opened_at=last_opened_at,
                replied_at=replied_at,
                message_id=message_id,
                thread_id=thread_id,
            )
        except Exception:
            return None

    # =========================================================================
    # Local JSON Database Fallback
    # =========================================================================

    def _load_local_leads(self) -> List[Lead]:
        if not os.path.exists(self.LOCAL_DB_FILE):
            return []
        try:
            with open(self.LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Lead(**item) for item in data]
        except Exception:
            return []

    def _save_local_leads(self, leads: List[Lead]) -> None:
        os.makedirs(os.path.dirname(self.LOCAL_DB_FILE), exist_ok=True)
        with open(self.LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump([l.model_dump(mode="json") for l in leads], f, indent=2)

    def delete_lead(self, lead_id: str) -> bool:
        """Deletes a lead from local DB or archives in Notion."""
        if not self.is_configured:
            leads = self._load_local_leads()
            leads = [l for l in leads if l.id != lead_id]
            self._save_local_leads(leads)
            return True
        # Notion archive page
        url = f"{self.BASE_URL}/pages/{lead_id}"
        try:
            resp = requests.patch(url, headers=self._headers(), json={"archived": True}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def update_lead_fields(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Updates editable fields of a lead."""
        if not self.is_configured:
            leads = self._load_local_leads()
            for l in leads:
                if l.id == lead_id:
                    for k, v in updates.items():
                        if hasattr(l, k):
                            setattr(l, k, v)
                    break
            self._save_local_leads(leads)
            return True
        # For Notion, map status or properties
        props = {}
        if "status" in updates:
            props["Status"] = {"status": {"name": updates["status"]}}
        if "publication" in updates:
            props["Publication / Platform"] = {"rich_text": [{"text": {"content": updates["publication"]}}]}
        if "persona" in updates:
            props["Persona"] = {"select": {"name": updates["persona"]}}
        if "recent_work" in updates:
            props["Recent Work / Article"] = {"rich_text": [{"text": {"content": updates["recent_work"]}}]}
        return self._update_page(lead_id, props)

