"""
Background Task Scheduler for NileConnect AI Contact Center.

Configures and manages background jobs (such as periodic AI Follow-up checks)
using APScheduler BackgroundScheduler.
"""
from __future__ import annotations

from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logging import logger
from app.scheduler.jobs.ai_followup_job import run_ai_followups_job

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Returns or creates the global BackgroundScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler(interval_minutes: int = 5) -> BackgroundScheduler:
    """
    Initializes and starts the periodic scheduler for AI follow-ups.
    """
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.add_job(
            func=run_ai_followups_job,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="ai_outbound_followups",
            name="Periodic AI Outbound Follow-up Caller",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("[Scheduler] Background scheduler started with %d-min interval", interval_minutes)
    return scheduler


def stop_scheduler() -> None:
    """Shuts down the background scheduler if active."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Background scheduler stopped")
