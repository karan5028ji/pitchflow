import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table

from config.settings import settings
from src.crm.notion_client import NotionClient
from src.crm.schemas import Lead
from src.engine.personalizer import Personalizer
from src.engine.email_dispatcher import EmailDispatcher
from src.engine.rate_limiter import RateLimiter
from src.inbox.reply_detector import ReplyDetector

console = Console(highlight=False)

class OutreachOrchestrator:
    """
    Central controller managing the outreach lifecycle:
    queue processing, template selection, rate limiting, and follow-ups.
    """

    def __init__(self):
        self.notion = NotionClient()
        self.dispatcher = EmailDispatcher()
        self.reply_detector = ReplyDetector(self.notion)

        # Template paths
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.blog_template_path = os.path.join(base_dir, "config", "templates", "blog_pitch.txt")
        self.playlist_template_path = os.path.join(base_dir, "config", "templates", "playlist_pitch.txt")
        self.followup_template_path = os.path.join(base_dir, "config", "templates", "follow_up.txt")

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Calculates current CRM pipeline metrics."""
        all_leads = self.notion.get_all_leads()
        stats = {
            "Total Leads": len(all_leads),
            "To Contact": 0,
            "Sent": 0,
            "Opened": 0,
            "Replied": 0,
            "Follow-up Sent": 0,
            "Featured": 0,
            "Bounced": 0,
            "Today Sent": RateLimiter.get_today_sent_count(),
            "Daily Limit": settings.daily_send_limit,
        }
        for lead in all_leads:
            if lead.status in stats:
                stats[lead.status] += 1
        return stats

    def print_pipeline_dashboard(self) -> None:
        """Renders an attractive terminal dashboard using Rich."""
        summary = self.get_pipeline_summary()
        table = Table(title="PR Outreach Pipeline (Kxrn Edition)", style="bold cyan")
        table.add_column("Stage / Metric", style="white", justify="left")
        table.add_column("Count", style="bold green", justify="right")

        for key, val in summary.items():
            table.add_row(key, str(val))

        console.print(table)

    def process_outreach_queue(
        self,
        limit: Optional[int] = None,
        dry_run: bool = False,
        extra_vars: Dict[str, Any] = None,
        ignore_weekend: bool = False
    ) -> int:
        """
        Picks leads in 'To Contact' state, generates personalized pitches,
        and sends them respecting anti-spam jitter, daily quotas, and the Weekend Blocker.
        """
        pending_leads = self.notion.get_leads_by_status("To Contact")
        if not pending_leads:
            console.print("[yellow]No leads found in 'To Contact' column.[/yellow]")
            return 0

        target_leads = pending_leads[:limit] if limit else pending_leads
        sent_count = 0

        console.print(f"[bold cyan]Found {len(target_leads)} leads to contact. Processing...[/bold cyan]")

        for idx, lead in enumerate(target_leads):
            if not dry_run:
                can_proceed, reason = RateLimiter.check_can_send(ignore_weekend=ignore_weekend)
                if not can_proceed:
                    console.print(f"[bold red]{reason}[/bold red]")
                    break

            # Select template based on persona or custom_template override
            if extra_vars and extra_vars.get("custom_template"):
                raw_template = extra_vars["custom_template"]
            else:
                template_path = self.playlist_template_path if "playlist" in lead.persona.lower() else self.blog_template_path
                raw_template = Personalizer.load_template(template_path)

            subject, text_body, html_body = Personalizer.render(
                template_str=raw_template,
                lead=lead,
                extra_vars=extra_vars,
                inject_pixel=True
            )

            if dry_run:
                console.print(f"\n[bold magenta]--- [DRY RUN] Pitch Preview for {lead.name} ({lead.email}) ---[/bold magenta]")
                console.print(f"[bold]Subject:[/bold] {subject}")
                console.print(f"[dim]{text_body[:250]}...[/dim]\n")
                sent_count += 1
                continue

            # Live Send
            console.print(f"[bold green]Sending pitch to {lead.name} <{lead.email}>...[/bold green]")
            result = self.dispatcher.send(
                recipient_email=lead.email,
                subject=subject,
                text_body=text_body,
                html_body=html_body
            )

            if result.success:
                self.notion.record_email_sent(lead.id, message_id=result.message_id)
                RateLimiter.record_send()
                sent_count += 1
                console.print(f"  [green][OK] Sent successfully! Message-ID: {result.message_id}[/green]")

                # Human jitter delay if there are more emails to send
                if idx < len(target_leads) - 1:
                    RateLimiter.throttle(dry_run=False)
            else:
                console.print(f"  [red][FAIL] Failed to send to {lead.email}: {result.error}[/red]")

        return sent_count

    def process_due_follow_ups(
        self,
        limit: Optional[int] = None,
        dry_run: bool = False,
        extra_vars: Dict[str, Any] = None,
        ignore_weekend: bool = False
    ) -> int:
        """
        Finds contacts sent >= FOLLOW_UP_AFTER_DAYS ago who haven't replied yet,
        and dispatches a polite in-thread follow-up respecting the Weekend Blocker.
        """
        all_leads = self.notion.get_all_leads()
        cutoff_date = datetime.now() - timedelta(days=settings.follow_up_after_days)

        eligible_leads: List[Lead] = []
        for l in all_leads:
            if l.status in ("Sent", "Opened") and l.send_count == 1:
                if l.sent_at and l.sent_at <= cutoff_date:
                    eligible_leads.append(l)

        if not eligible_leads:
            console.print("[yellow]No follow-ups due at this time.[/yellow]")
            return 0

        target_leads = eligible_leads[:limit] if limit else eligible_leads
        sent_count = 0

        console.print(f"[bold cyan]Found {len(target_leads)} follow-ups due. Processing...[/bold cyan]")

        raw_template = Personalizer.load_template(self.followup_template_path)

        for idx, lead in enumerate(target_leads):
            if not dry_run:
                can_proceed, reason = RateLimiter.check_can_send(ignore_weekend=ignore_weekend)
                if not can_proceed:
                    console.print(f"[bold red]{reason}[/bold red]")
                    break

            subject, text_body, html_body = Personalizer.render(
                template_str=raw_template,
                lead=lead,
                extra_vars=extra_vars,
                inject_pixel=True
            )

            if dry_run:
                console.print(f"\n[bold magenta]--- [DRY RUN] Follow-up for {lead.name} ({lead.email}) ---[/bold magenta]")
                console.print(f"[bold]Subject:[/bold] {subject}")
                console.print(f"[dim]{text_body[:200]}...[/dim]\n")
                sent_count += 1
                continue

            console.print(f"[bold green]Sending in-thread follow-up to {lead.name}...[/bold green]")
            result = self.dispatcher.send(
                recipient_email=lead.email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                in_reply_to=lead.message_id,
                references=lead.message_id
            )

            if result.success:
                self.notion.record_follow_up_sent(lead.id, message_id=result.message_id)
                RateLimiter.record_send()
                sent_count += 1
                console.print(f"  [green][OK] Follow-up delivered! Message-ID: {result.message_id}[/green]")

                if idx < len(target_leads) - 1:
                    RateLimiter.throttle(dry_run=False)
            else:
                console.print(f"  [red][FAIL] Failed to send follow-up: {result.error}[/red]")

        return sent_count

    def check_for_replies(self) -> int:
        """Scans inbox for new replies and updates Notion."""
        console.print("[cyan]Scanning inbox via IMAP for incoming replies...[/cyan]")
        replies = self.reply_detector.scan_for_replies()
        if replies:
            for r in replies:
                lead = r["lead"]
                console.print(f"[bold green][REPLY DETECTED] from {lead.name} ({lead.email})![/bold green]")
                console.print(f"   Subject: {r['subject']}")
        else:
            console.print("[dim]No new replies found.[/dim]")
        return len(replies)
