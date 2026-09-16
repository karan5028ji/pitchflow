import os
import re
import sys
import csv
import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, Response, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure root dir is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config.settings import settings
from src.config_store import ConfigStore
from src.crm.notion_client import NotionClient
from src.crm.schemas import Lead
from src.engine.personalizer import Personalizer
from src.engine.email_dispatcher import EmailDispatcher
from src.engine.rate_limiter import RateLimiter
from src.inbox.reply_detector import ReplyDetector
from src.notifications.telegram_notifier import TelegramNotifier
from src.orchestrator import OutreachOrchestrator

app = FastAPI(title="PR Outreach Automator & CRM (Kxrn Edition)", version="2.2.0")

# SECURITY FIX: Restrict CORS to localhost only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# 1x1 transparent PNG payload (43 bytes)
TRANSPARENT_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)

WEB_DIR = os.path.join(BASE_DIR, "web")

# Simple email regex for validation
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Valid lead_id pattern
_LEAD_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,80}$")


def _valid_email(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email.strip()))


# =============================================================================
# Background Tasks
# =============================================================================

def process_lead_open(lead_id: str, user_agent: str, client_ip: str):
    """Background worker to update CRM without slowing down pixel delivery."""
    try:
        notion = NotionClient()
        lead = notion.get_lead_by_id(lead_id)
        if lead:
            notion.record_email_opened(lead_id)
            TelegramNotifier.notify_open(
                lead_name=lead.name,
                publication=lead.publication,
                open_count=(lead.open_count or 0) + 1
            )
            print(f"[Tracker] Recorded open for: {lead.name} ({lead.email}) from {client_ip}")
    except Exception as e:
        print(f"[Tracker] Error updating open for {lead_id}: {e}")

# =============================================================================
# Frontend UI Route
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>PR Outreach Automator</h1><p>Web UI file not found in web/index.html</p>"

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "PR Outreach Tracking Server (Kxrn Edition)",
        "is_weekend": RateLimiter.is_weekend(),
    }


# =============================================================================
# Tracking Pixel Route
# =============================================================================

@app.get("/t/{lead_id}.png")
def track_pixel(lead_id: str, request: Request, background_tasks: BackgroundTasks):
    headers = {
        "Content-Type": "image/png",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if not _LEAD_ID_RE.match(lead_id):
        return Response(content=TRANSPARENT_PNG_BYTES, media_type="image/png", headers=headers)

    user_agent = request.headers.get("user-agent", "Unknown")
    client_ip = request.client.host if request.client else "Unknown"
    background_tasks.add_task(process_lead_open, lead_id, user_agent, client_ip)
    return Response(content=TRANSPARENT_PNG_BYTES, media_type="image/png", headers=headers)

# =============================================================================
# Settings & In-App Credential Vault APIs
# =============================================================================

class ConfigUpdateRequest(BaseModel):
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    email_provider: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None
    use_notion: Optional[bool] = None
    tracking_server_url: Optional[str] = None
    min_delay_seconds: Optional[int] = None
    max_delay_seconds: Optional[int] = None
    daily_send_limit: Optional[int] = None
    pause_on_weekends: Optional[bool] = None
    default_track_name: Optional[str] = None
    default_stream_link: Optional[str] = None
    default_bio_link: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

@app.get("/api/config")
def get_config():
    conf = ConfigStore.load()
    return conf

@app.post("/api/config")
def update_config(req: ConfigUpdateRequest):
    updates = req.model_dump(exclude_unset=True)
    if updates.get("sender_email") and not updates.get("smtp_user"):
        updates["smtp_user"] = updates["sender_email"]
    saved = ConfigStore.save(updates)
    return {"status": "success", "message": "Settings saved successfully", "config": saved}

class TestEmailRequest(BaseModel):
    recipient_email: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

@app.post("/api/test-credentials")
def test_credentials(req: TestEmailRequest):
    """
    Sends an immediate test email to verify SMTP credentials.
    Automatically applies & saves any credentials passed from Settings form,
    and defaults the destination to the current sender Gmail.
    """
    updates = req.model_dump(exclude_unset=True)
    recipient = updates.pop("recipient_email", None)
    if updates:
        if updates.get("sender_email") and not updates.get("smtp_user"):
            updates["smtp_user"] = updates["sender_email"]
        ConfigStore.save(updates)

    target_email = (recipient or req.sender_email or settings.sender_email or "").strip()
    if not _valid_email(target_email):
        raise HTTPException(status_code=422, detail=f"Invalid recipient/sender email address: '{target_email}'")

    dispatcher = EmailDispatcher()
    dummy_lead = Lead(
        id="test_verify_001",
        name=settings.sender_name,
        email=target_email,
        publication="Diagnostic Verification",
        persona="Journalist",
        recent_work="system diagnostic verification",
        status="To Contact"
    )
    orch = OutreachOrchestrator()
    raw_template = Personalizer.load_template(orch.blog_template_path)
    subject, text_body, html_body = Personalizer.render(raw_template, dummy_lead, inject_pixel=True)

    result = dispatcher.send(
        recipient_email=target_email,
        subject=f"[Diagnostic Test] Outreach Engine Active: {settings.sender_name}",
        text_body=text_body,
        html_body=html_body
    )

    if result.success:
        return {
            "status": "success",
            "message": f"Diagnostic email dispatched to {target_email}! Message-ID: {result.message_id}",
            "sent_to": target_email
        }
    return JSONResponse(
        status_code=400,
        content={"status": "error", "message": result.error or "Unknown error while sending test email."}
    )

class TestPitchRequest(BaseModel):
    recipient_email: str
    lead_id: Optional[str] = None
    template_type: Optional[str] = "blog"
    track_name: Optional[str] = None
    stream_link: Optional[str] = None
    bio_link: Optional[str] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    custom_template: Optional[str] = None

@app.post("/api/test-pitch")
def send_test_pitch(req: TestPitchRequest):
    """Dispatches a live rendered pitch or custom edited pitch to any test email."""
    if not _valid_email(req.recipient_email):
        raise HTTPException(status_code=422, detail="Invalid recipient email address.")

    notion = NotionClient()
    lead = None
    if req.lead_id and _LEAD_ID_RE.match(req.lead_id):
        lead = notion.get_lead_by_id(req.lead_id)
    if not lead:
        lead = Lead(
            id="test_sim_lead",
            name="Test Reviewer",
            email=req.recipient_email,
            publication="Indie Tastemaker Blog",
            persona="Journalist" if req.template_type != "playlist" else "Playlist Curator",
            recent_work="fresh underground electronic and indie spotlights",
            status="To Contact"
        )
    orch = OutreachOrchestrator()
    if req.custom_template:
        raw_template = req.custom_template
    elif req.template_type == "playlist":
        raw_template = Personalizer.load_template(orch.playlist_template_path)
    elif req.template_type == "follow_up":
        raw_template = Personalizer.load_template(orch.followup_template_path)
    else:
        raw_template = Personalizer.load_template(orch.blog_template_path)

    extra_vars = {
        "track_name": req.track_name or settings.default_track_name,
        "stream_link": req.stream_link or settings.default_stream_link,
        "bio_link": req.bio_link or settings.default_bio_link,
    }
    subject, text_body, html_body = Personalizer.render(
        template_str=raw_template,
        lead=lead,
        extra_vars=extra_vars,
        inject_pixel=True
    )
    if req.custom_subject:
        subject = req.custom_subject
    if req.custom_body:
        html_body = req.custom_body
        text_body = re.sub(r'<[^>]+>', '', req.custom_body)

    dispatcher = EmailDispatcher()
    result = dispatcher.send(
        recipient_email=req.recipient_email,
        subject=f"[TEST PREVIEW] {subject}",
        text_body=text_body,
        html_body=html_body
    )
    if result.success:
        return {"status": "success", "message": f"Test pitch sent to {req.recipient_email}! Message-ID: {result.message_id}"}
    return JSONResponse(
        status_code=400,
        content={"status": "error", "message": result.error or "Failed to send test pitch."}
    )


@app.post("/api/test-notion")
def test_notion():
    """Tests connection to Notion API."""
    notion = NotionClient()
    res = notion.verify_connection()
    return res

# =============================================================================
# Leads & CRM Pipeline APIs
# =============================================================================

class CreateLeadRequest(BaseModel):
    name: str
    email: str
    publication: Optional[str] = "your platform"
    persona: Optional[str] = "Journalist"
    recent_work: Optional[str] = ""

class UpdateLeadRequest(BaseModel):
    status: Optional[str] = None
    publication: Optional[str] = None
    persona: Optional[str] = None
    recent_work: Optional[str] = None

@app.get("/api/leads")
def list_leads():
    notion = NotionClient()
    leads = notion.get_all_leads()
    orch = OutreachOrchestrator()
    summary = orch.get_pipeline_summary()
    summary["Blacklisted"] = sum(1 for l in leads if l.status == "Blacklisted")
    return {
        "leads": [l.model_dump(mode="json") for l in leads],
        "summary": summary,
        "is_weekend": RateLimiter.is_weekend(),
    }

@app.post("/api/leads")
def create_lead(req: CreateLeadRequest):
    if not _valid_email(req.email):
        raise HTTPException(status_code=422, detail=f"Invalid email address: {req.email}")

    notion = NotionClient()
    existing = notion.get_all_leads()
    if any(l.email.strip().lower() == req.email.strip().lower() for l in existing):
        raise HTTPException(
            status_code=409,
            detail=f"A lead with email '{req.email}' already exists in the CRM."
        )

    new_id = notion.add_lead(
        name=req.name,
        email=req.email,
        publication=req.publication or "your platform",
        persona=req.persona or "Journalist",
        recent_work=req.recent_work or ""
    )
    if new_id:
        return {"status": "success", "id": new_id, "message": "Lead added to CRM"}
    raise HTTPException(status_code=500, detail="Failed to create lead")

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: str, req: UpdateLeadRequest):
    if not _LEAD_ID_RE.match(lead_id):
        raise HTTPException(status_code=422, detail="Invalid lead ID format.")
    notion = NotionClient()
    updates = req.model_dump(exclude_unset=True)
    success = notion.update_lead_fields(lead_id, updates)
    if success:
        return {"status": "success", "message": "Lead updated"}
    raise HTTPException(status_code=400, detail="Failed to update lead")

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: str):
    if not _LEAD_ID_RE.match(lead_id):
        raise HTTPException(status_code=422, detail="Invalid lead ID format.")
    notion = NotionClient()
    success = notion.delete_lead(lead_id)
    if success:
        return {"status": "success", "message": "Lead deleted"}
    raise HTTPException(status_code=400, detail="Failed to delete lead")


def _parse_pasted_leads(content: str) -> List[Dict[str, str]]:
    """
    Intelligently parses pasted lead data:
    - Supports Tab-separated (Google Sheets / Excel paste)
    - Supports Comma, Semicolon, Pipe-delimited CSV
    - Case-insensitive, fuzzy header matching
    - Fallback: extracts email from any column even if no headers exist
    """
    lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
    if not lines:
        return []

    # Detect delimiter using first non-empty line
    first_line = lines[0]
    delimiter = ","
    for d in ["\t", ";", "|", ","]:
        if d in first_line:
            delimiter = d
            break

    try:
        reader = list(csv.reader(lines, delimiter=delimiter))
    except Exception:
        reader = [ln.split(delimiter) for ln in lines]

    if not reader:
        return []

    raw_headers = [str(col).strip() for col in reader[0]]
    header_keywords = {"email", "mail", "name", "curator", "publication", "outlet", "persona", "work", "role"}
    has_header = any(any(kw in h.lower() for kw in header_keywords) for h in raw_headers)

    data_rows = reader[1:] if has_header else reader
    results = []

    for row in data_rows:
        if not row or not any(str(cell).strip() for cell in row):
            continue

        lead_data = {
            "name": "",
            "email": "",
            "publication": "your platform",
            "persona": "Journalist",
            "recent_work": ""
        }

        if has_header:
            for idx, cell_val in enumerate(row):
                if idx >= len(raw_headers):
                    break
                val = str(cell_val).strip()
                hdr = re.sub(r'[^a-z0-9]', '', raw_headers[idx].lower())
                if any(x in hdr for x in ["email", "mail"]):
                    lead_data["email"] = val
                elif any(x in hdr for x in ["name", "curator", "contact", "artist", "person"]):
                    lead_data["name"] = val
                elif any(x in hdr for x in ["pub", "outlet", "media", "blog", "mag", "company", "playlist"]):
                    lead_data["publication"] = val
                elif any(x in hdr for x in ["persona", "role", "type", "tag"]):
                    lead_data["persona"] = val
                elif any(x in hdr for x in ["work", "recent", "article", "hook", "notes"]):
                    lead_data["recent_work"] = val

        # Fallback to scan cells for email if not populated
        if not lead_data["email"]:
            for cell in row:
                cell_s = str(cell).strip()
                if _valid_email(cell_s):
                    lead_data["email"] = cell_s
                    break

        if not lead_data["name"]:
            for cell in row:
                cell_s = str(cell).strip()
                if cell_s and not _valid_email(cell_s):
                    lead_data["name"] = cell_s
                    break
            if not lead_data["name"]:
                lead_data["name"] = "Curator"

        if lead_data["email"] and _valid_email(lead_data["email"]):
            results.append(lead_data)

    return results


class CsvTextImportRequest(BaseModel):
    csv_content: str

@app.post("/api/leads/import-csv")
def import_csv_text(req: CsvTextImportRequest):
    if len(req.csv_content.encode("utf-8")) > 400_000:
        raise HTTPException(status_code=413, detail="CSV content too large. Maximum size is 400KB.")

    notion = NotionClient()
    existing = notion.get_all_leads()
    existing_emails = {l.email.strip().lower() for l in existing}

    parsed_rows = _parse_pasted_leads(req.csv_content)
    if not parsed_rows:
        return {
            "status": "success",
            "imported": 0,
            "skipped": 0,
            "message": "No valid leads found. Please ensure each row contains an email address."
        }

    count = 0
    skipped = 0
    updated = 0

    for item in parsed_rows:
        em = item["email"].strip().lower()
        if em in existing_emails:
            # Update existing lead with newly provided publication/recent work if present
            lead_obj = next((l for l in existing if l.email.strip().lower() == em), None)
            if lead_obj and (item["recent_work"] or item["publication"] != "your platform"):
                notion.update_lead_fields(lead_obj.id, {
                    "publication": item["publication"],
                    "recent_work": item["recent_work"]
                })
                updated += 1
            else:
                skipped += 1
            continue

        notion.add_lead(
            name=item["name"] or "Curator",
            email=item["email"],
            publication=item["publication"] or "your platform",
            persona=item["persona"] or "Journalist",
            recent_work=item["recent_work"] or ""
        )
        existing_emails.add(em)
        count += 1

    msg = f"Successfully imported {count} new leads."
    if updated:
        msg += f" Updated {updated} existing."
    if skipped:
        msg += f" Skipped {skipped} (already in CRM)."
    return {"status": "success", "imported": count, "updated": updated, "skipped": skipped, "message": msg}

# =============================================================================
# Pitch Composer, Template Management & Spintax Previewer APIs
# =============================================================================

@app.get("/api/templates/{template_type}")
def get_template(template_type: str):
    orch = OutreachOrchestrator()
    path_map = {
        "blog": orch.blog_template_path,
        "playlist": orch.playlist_template_path,
        "follow_up": orch.followup_template_path,
    }
    path = path_map.get(template_type, orch.blog_template_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Template not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"template_type": template_type, "content": content}

class TemplateUpdateRequest(BaseModel):
    content: str

@app.post("/api/templates/{template_type}")
def save_template(template_type: str, req: TemplateUpdateRequest):
    orch = OutreachOrchestrator()
    path_map = {
        "blog": orch.blog_template_path,
        "playlist": orch.playlist_template_path,
        "follow_up": orch.followup_template_path,
    }
    path = path_map.get(template_type, orch.blog_template_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(req.content)
    return {"status": "success", "message": f"Template '{template_type}' updated successfully."}

class PreviewRequest(BaseModel):
    lead_id: Optional[str] = None
    template_type: Optional[str] = "blog"
    track_name: Optional[str] = None
    stream_link: Optional[str] = None
    bio_link: Optional[str] = None
    custom_template: Optional[str] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None

@app.post("/api/preview")
def preview_pitch(req: PreviewRequest):
    notion = NotionClient()
    lead = None
    if req.lead_id and _LEAD_ID_RE.match(req.lead_id):
        lead = notion.get_lead_by_id(req.lead_id)

    if not lead:
        lead = Lead(
            id="demo_sample_lead",
            name="Amit Sharma",
            email="amit.sharma@wildcity.test",
            publication="Wild City India",
            persona="Journalist" if req.template_type != "playlist" else "Playlist Curator",
            recent_work="underground electronic beats and emerging bedroom producers",
            status="To Contact"
        )

    orch = OutreachOrchestrator()
    if req.custom_template:
        raw_template = req.custom_template
    elif req.template_type == "playlist":
        raw_template = Personalizer.load_template(orch.playlist_template_path)
    elif req.template_type == "follow_up":
        raw_template = Personalizer.load_template(orch.followup_template_path)
    else:
        raw_template = Personalizer.load_template(orch.blog_template_path)

    extra_vars = {
        "track_name": req.track_name or settings.default_track_name,
        "stream_link": req.stream_link or settings.default_stream_link,
        "bio_link": req.bio_link or settings.default_bio_link,
    }
    subject, text_body, html_body = Personalizer.render(
        template_str=raw_template,
        lead=lead,
        extra_vars=extra_vars,
        inject_pixel=True
    )
    if req.custom_subject:
        subject = req.custom_subject
    if req.custom_body:
        html_body = req.custom_body
        text_body = re.sub(r'<[^>]+>', '', req.custom_body)

    return {
        "subject": subject,
        "text_body": text_body,
        "html_body": html_body,
        "raw_template": raw_template,
        "lead": lead.model_dump(mode="json"),
        "template_type": req.template_type
    }

# =============================================================================
# Campaign Dispatcher & Inbox Scanner APIs
# =============================================================================

class DispatchBatchRequest(BaseModel):
    limit: Optional[int] = 5
    dry_run: bool = False
    track_name: Optional[str] = None
    stream_link: Optional[str] = None
    ignore_weekend: Optional[bool] = False
    custom_template: Optional[str] = None

@app.post("/api/campaign/dispatch")
def dispatch_batch(req: DispatchBatchRequest):
    orch = OutreachOrchestrator()
    extra_vars = {}
    if req.track_name:
        extra_vars["track_name"] = req.track_name
    if req.stream_link:
        extra_vars["stream_link"] = req.stream_link
    if req.custom_template:
        extra_vars["custom_template"] = req.custom_template

    if not req.dry_run:
        can_send, reason = RateLimiter.check_can_send(ignore_weekend=req.ignore_weekend)
        if not can_send:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "blocked",
                    "message": reason,
                    "is_weekend": RateLimiter.is_weekend()
                }
            )

    sent = orch.process_outreach_queue(
        limit=req.limit,
        dry_run=req.dry_run,
        extra_vars=extra_vars,
        ignore_weekend=req.ignore_weekend
    )
    return {
        "status": "success",
        "sent_count": sent,
        "dry_run": req.dry_run,
        "today_sent": RateLimiter.get_today_sent_count(),
        "daily_limit": settings.daily_send_limit
    }

@app.post("/api/inbox/scan")
def scan_inbox():
    orch = OutreachOrchestrator()
    raw_replies = orch.reply_detector.scan_for_replies()

    reply_details = []
    for r in raw_replies:
        lead = r.get("lead")
        reply_details.append({
            "lead_name":   lead.name if lead else "Unknown",
            "from_email":  r.get("from_email", ""),
            "subject":     r.get("subject", ""),
            "action":      r.get("action", "replied"),
        })

    return {
        "status": "success",
        "new_replies": len(raw_replies),
        "replies": reply_details,
        "message": f"Inbox scan complete. Found {len(raw_replies)} new replies."
    }
