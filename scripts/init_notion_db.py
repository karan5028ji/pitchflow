import sys
import os

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rich.console import Console
from src.crm.notion_client import NotionClient
from config.settings import settings

# Force safe encoding on Windows console
console = Console(highlight=False)

SAMPLE_LEADS = [
    {
        "name": "Amit Sharma",
        "email": "amit.sharma@wildcity.test",
        "publication": "Wild City India",
        "persona": "Journalist",
        "recent_work": "deep-dive into underground electronic and chillout beats",
        "status": "To Contact",
        "send_count": 0,
        "open_count": 0
    },
    {
        "name": "Pooja Verma",
        "email": "pooja.v@rollingstoneindia.test",
        "publication": "Rolling Stone India",
        "persona": "Journalist",
        "recent_work": "the rise of self-produced Desi Lo-Fi beatmakers",
        "status": "To Contact",
        "send_count": 0,
        "open_count": 0
    },
    {
        "name": "Rohan Deshmukh",
        "email": "rohan@spotify-indiecurators.test",
        "publication": "Desi Lo-Fi Chill Spotify Playlist",
        "persona": "Playlist Curator",
        "recent_work": "tracks with melodic guitars and nostalgic late-night vibes",
        "status": "To Contact",
        "send_count": 0,
        "open_count": 0
    },
    {
        "name": "Sarah Jenkins",
        "email": "sarah@indiemusicfilter.test",
        "publication": "Indie Music Filter",
        "persona": "Journalist",
        "recent_work": "spotlight on international bedroom pop and downtempo producers",
        "status": "To Contact",
        "send_count": 0,
        "open_count": 0
    }
]

def main():
    console.print("[bold cyan]Initializing PR Outreach Automator Environment...[/bold cyan]\n")
    notion = NotionClient()
    conn = notion.verify_connection()

    if conn.get("status") == "connected":
        console.print(f"[bold green][OK] Successfully connected to Notion Database: '{conn.get('database_name')}'[/bold green]")
    else:
        console.print(f"[yellow][INFO] Notion API not configured yet: {conn.get('message')}[/yellow]")
        console.print("[dim]Populating sample music industry leads into local offline database (data/local_leads.json)...[/dim]")
        
        existing = notion.get_all_leads()
        if not existing:
            for lead_data in SAMPLE_LEADS:
                notion.add_lead(
                    name=lead_data["name"],
                    email=lead_data["email"],
                    publication=lead_data["publication"],
                    persona=lead_data["persona"],
                    recent_work=lead_data["recent_work"]
                )
            console.print(f"[bold green][OK] Created {len(SAMPLE_LEADS)} sample leads ready for dry-run testing![/bold green]")
        else:
            console.print(f"[bold green][OK] Local database already contains {len(existing)} leads.[/bold green]")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Run [cyan]python main.py status[/cyan] to view your pipeline.")
    console.print("2. Run [cyan]python main.py send --dry-run[/cyan] to preview personalized pitches.")
    console.print("3. Configure your [cyan].env[/cyan] file when ready for live sending.\n")

if __name__ == "__main__":
    main()
