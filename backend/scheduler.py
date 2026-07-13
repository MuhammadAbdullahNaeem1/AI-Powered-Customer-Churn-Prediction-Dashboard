"""APScheduler-based daily scoring job (runs at midnight)."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: BackgroundScheduler | None = None


def _daily_scoring_job():
    """Score all customers and trigger interventions. Runs in the scheduler thread."""
    from db.database import SessionLocal
    from ml.score import score_all_customers

    db = SessionLocal()
    try:
        summary = score_all_customers(db)
        print(f"[scheduler] Daily scoring complete: {summary}")
    except Exception as exc:  # noqa: BLE001
        print(f"[scheduler] Daily scoring failed: {exc}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler with a midnight daily scoring trigger."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    _scheduler.add_job(
        _daily_scoring_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_scoring",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    print("[scheduler] Started. Daily scoring scheduled for 00:00 UTC.")
    return _scheduler


if __name__ == "__main__":
    # Allow running the scoring job on demand for testing.
    _daily_scoring_job()
