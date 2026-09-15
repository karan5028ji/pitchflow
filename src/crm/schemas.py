from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

LeadStatus = Literal[
    "To Contact",
    "Sent",
    "Opened",
    "Replied",
    "Follow-up Needed",
    "Follow-up Sent",
    "Featured",
    "Bounced",
    "Blacklisted"
]

class Lead(BaseModel):
    id: str = Field(description="Notion Page ID or unique record ID")
    name: str
    email: str
    publication: str = Field(default="your platform")
    persona: str = Field(default="Journalist")
    recent_work: Optional[str] = Field(default=None)
    status: LeadStatus = Field(default="To Contact")
    send_count: int = Field(default=0)
    sent_at: Optional[datetime] = None
    open_count: int = Field(default=0)
    last_opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    custom_notes: Optional[str] = None

    @property
    def first_name(self) -> str:
        """Extracts first name from full name cleanly."""
        parts = self.name.strip().split()
        return parts[0] if parts else "there"
