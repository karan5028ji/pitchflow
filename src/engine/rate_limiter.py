import os
import json
import time
from datetime import datetime, date
from typing import Dict, Any, Tuple
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from config.settings import settings

class RateLimiter:
    """
    Controls sending pace to protect sender domain reputation:
    1. Human jitter (randomized sleep 3-7 mins between emails)
    2. Daily volume cap tracking (warmup protection)
    3. Weekend Blocker (pauses outreach on Saturday & Sunday to prevent graveyard pile-ups)
    """

    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "daily_stats.json")

    @classmethod
    def _load_stats(cls) -> Dict[str, Any]:
        if not os.path.exists(cls.LOG_FILE):
            return {"date": str(date.today()), "sent_count": 0}
        try:
            with open(cls.LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") != str(date.today()):
                    return {"date": str(date.today()), "sent_count": 0}
                return data
        except Exception:
            return {"date": str(date.today()), "sent_count": 0}

    @classmethod
    def _save_stats(cls, stats: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(cls.LOG_FILE), exist_ok=True)
        with open(cls.LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

    @classmethod
    def get_today_sent_count(cls) -> int:
        return cls._load_stats().get("sent_count", 0)

    @classmethod
    def is_weekend(cls) -> bool:
        """Returns True if today is Saturday (5) or Sunday (6)."""
        return datetime.now().weekday() in (5, 6)

    @classmethod
    def check_can_send(cls, ignore_weekend: bool = False) -> Tuple[bool, str]:
        """
        Validates whether outreach can be sent right now.
        Returns (can_send: bool, reason: str).
        """
        pause_weekends = getattr(settings, "pause_on_weekends", True)
        if pause_weekends and not ignore_weekend and cls.is_weekend():
            day_name = "Saturday" if datetime.now().weekday() == 5 else "Sunday"
            return False, f"Weekend Blocker Active ({day_name}): Outreach paused to prevent emails piling up in Monday morning trash. (Can override if needed)"

        sent = cls.get_today_sent_count()
        if sent >= settings.daily_send_limit:
            return False, f"Daily send limit of {settings.daily_send_limit} reached. Warmup safety active."

        return True, "Ready to send"

    @classmethod
    def can_send(cls, ignore_weekend: bool = False) -> bool:
        ok, _ = cls.check_can_send(ignore_weekend=ignore_weekend)
        return ok

    @classmethod
    def record_send(cls) -> int:
        stats = cls._load_stats()
        stats["sent_count"] = stats.get("sent_count", 0) + 1
        stats["last_sent_at"] = datetime.now().isoformat()
        cls._save_stats(stats)
        return stats["sent_count"]

    @classmethod
    def throttle(cls, dry_run: bool = False) -> None:
        """Waits for a randomized jitter delay with a visual progress bar."""
        if dry_run:
            return

        delay = settings.get_random_delay()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]Anti-spam jitter: waiting {delay}s before next email...", total=delay)
            for _ in range(delay):
                time.sleep(1)
                progress.advance(task, 1)
