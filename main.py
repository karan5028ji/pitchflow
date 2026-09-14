import csv
import sys
import typer
import uvicorn
from typing import Optional
from rich.console import Console

from src.orchestrator import OutreachOrchestrator
from src.crm.notion_client import NotionClient
from src.engine.personalizer import Personalizer
from src.crm.schemas import Lead
from config.settings import settings

app = typer.Typer(
    help="PR Outreach Automator (Kxrn Edition) - Music PR & Cold Pitching Engine",
    add_completion=False
)
console = Console(highlight=False)

@app.command()
def status():
    """Display the current Notion CRM pipeline statistics and sending limits."""
    orch = OutreachOrchestrator()
    orch.print_pipeline_dashboard()

@app.command()
def send(
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum emails to send in this batch"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview pitches in terminal without sending"),
    track_name: Optional[str] = typer.Option(None, "--track", "-t", help="Track name to pitch"),
    stream_link: Optional[str] = typer.Option(None, "--link", help="Streaming link (Spotify/Apple)"),
):
    """Process leads in the 'To Contact' queue and dispatch pitches."""
    orch = OutreachOrchestrator()
    extra_vars = {}
    if track_name:
        extra_vars["track_name"] = track_name
    if stream_link:
        extra_vars["stream_link"] = stream_link

    sent = orch.process_outreach_queue(limit=limit, dry_run=dry_run, extra_vars=extra_vars)
    if dry_run:
        console.print(f"[bold yellow]Dry run finished. Generated {sent} pitch previews.[/bold yellow]")
    else:
        console.print(f"[bold green]Batch complete. Dispatched {sent} emails.[/bold green]")

@app.command()
def follow_ups(
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max follow-ups to send"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview follow-ups without sending"),
):
    """Scan and dispatch in-thread follow-ups for contacts waiting >= 4 days."""
    orch = OutreachOrchestrator()
    sent = orch.process_due_follow_ups(limit=limit, dry_run=dry_run)
    if dry_run:
        console.print(f"[bold yellow]Dry run finished. Generated {sent} follow-up previews.[/bold yellow]")
    else:
        console.print(f"[bold green]Follow-up batch complete. Sent {sent} emails.[/bold green]")

@app.command()
def check_replies():
    """Scan Gmail inbox via IMAP to detect incoming replies and update Notion CRM."""
    orch = OutreachOrchestrator()
    orch.check_for_replies()

@app.command()
def add_lead(
    name: str = typer.Option(..., "--name", "-n", prompt="Curator/Journalist Full Name"),
    email: str = typer.Option(..., "--email", "-e", prompt="Curator Email Address"),
    publication: str = typer.Option("your platform", "--pub", "-p", prompt="Publication or Playlist"),
    persona: str = typer.Option("Journalist", "--persona", prompt="Persona (Journalist/Playlist Curator)"),
    recent_work: str = typer.Option("", "--recent", prompt="Recent Article / Vibe (optional)"),
):
    """Add a single lead into the Notion CRM pipeline."""
    notion = NotionClient()
    lead_id = notion.add_lead(
        name=name,
        email=email,
        publication=publication,
        persona=persona,
        recent_work=recent_work
    )
    if lead_id:
        console.print(f"[bold green][OK] Added '{name}' ({email}) to CRM with ID: {lead_id}[/bold green]")
    else:
        console.print(f"[bold red][FAIL] Failed to add lead. Check your connection.[/bold red]")

@app.command()
def import_csv(
    file_path: str = typer.Argument(..., help="Path to CSV file with Name, Email, Publication, etc."),
):
    """Import contacts in bulk from a CSV export (e.g. Apollo, Apify, or spreadsheet)."""
    notion = NotionClient()
    count = 0
    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name") or row.get("First Name") or "Curator"
                email = row.get("Email") or row.get("Contact Email")
                publication = row.get("Publication") or row.get("Company") or "your platform"
                persona = row.get("Persona") or row.get("Role") or "Journalist"
                recent_work = row.get("Recent Work") or row.get("Article") or ""

                if email:
                    notion.add_lead(name=name, email=email, publication=publication, persona=persona, recent_work=recent_work)
                    count += 1
        console.print(f"[bold green][OK] Successfully imported {count} leads into CRM.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error reading CSV: {e}[/bold red]")

@app.command()
def test_send(
    recipient: str = typer.Option(..., "--to", "-t", prompt="Your test email address"),
):
    """Send a self-test email to verify formatting, email delivery, and tracking pixel."""
    orch = OutreachOrchestrator()
    dummy_lead = Lead(
        id="test_lead_001",
        name="Kxrn Test",
        email=recipient,
        publication="Test Music Blog",
        persona="Journalist",
        recent_work="an exploration of modern Indian Lo-Fi and Chillhop",
        status="To Contact"
    )
    raw_template = Personalizer.load_template(orch.blog_template_path)
    subject, text_body, html_body = Personalizer.render(
        template_str=raw_template,
        lead=dummy_lead,
        inject_pixel=True
    )
    console.print(f"[cyan]Dispatching diagnostic test email to {recipient}...[/cyan]")
    res = orch.dispatcher.send(recipient, subject, text_body, html_body)
    if res.success:
        console.print(f"[bold green][OK] Test email sent successfully! Message-ID: {res.message_id}[/bold green]")
        console.print(f"[dim]Check your inbox. When opened, the pixel will ping: {settings.tracking_server_url}/t/{dummy_lead.id}.png[/dim]")
    else:
        console.print(f"[bold red][FAIL] Send failed: {res.error}[/bold red]")

@app.command()
def gui(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run Web Dashboard"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open browser automatically")
):
    """Launch the SaaS Web GUI Dashboard and open in default browser."""
    import threading
    import webbrowser
    import time

    url = f"http://localhost:{port}"
    console.print(f"[bold green]Starting Kxrn PR Outreach Studio on {url}...[/bold green]")

    if not no_browser:
        def _open():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run("api.index:app", host=host, port=port, log_level="info")

@app.command()
def serve_tracker(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run tracking server"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host address"),
):
    """Run local FastAPI tracking pixel server with hot-reloading."""
    console.print(f"[bold cyan]Starting PR Tracking Server on http://{host}:{port}...[/bold cyan]")
    uvicorn.run("api.index:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    app()

