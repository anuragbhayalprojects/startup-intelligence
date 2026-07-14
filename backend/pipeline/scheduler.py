"""
backend/pipeline/scheduler.py
--------------------------------
In-process async background loop for polling RSS feeds and dispatching email digests.
Launched on FastAPI startup.
"""

from __future__ import annotations
import os
import json
import asyncio
import logging
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from backend.pipeline.news_processor import NewsProcessor
from backend.services.email_service import load_email_config, dispatch_gmail_digest

logger = logging.getLogger("startup_intelligence.pipeline.scheduler")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SCHEDULER_CONFIG_PATH = os.path.join(PROJECT_ROOT, "backend", "config", "scheduler.json")

# In-memory execution states to prevent duplicate trigger loops
_LAST_POLL_TIME: datetime = datetime.now(timezone.utc)
_SENT_DIGESTS_TODAY: set[str] = set()  # set of keys: "YYYY-MM-DD:HH:MM"


def load_scheduler_config() -> dict:
    """Loads scheduler configurations."""
    if not os.path.exists(SCHEDULER_CONFIG_PATH):
        return {"polling_enabled": True, "default_poll_interval_minutes": 60, "scheduler_tick_seconds": 30}
    try:
        with open(SCHEDULER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load scheduler config: {e}")
        return {"polling_enabled": True, "default_poll_interval_minutes": 60, "scheduler_tick_seconds": 30}


async def scheduler_loop():
    """Main in-process background worker task loop."""
    global _LAST_POLL_TIME
    
    logger.info("Initializing Startup News Scheduler background loop...")
    
    # Wait a short delay on startup to let Uvicorn launch cleanly
    await asyncio.sleep(10)
    
    while True:
        try:
            config = load_scheduler_config()
            if not config.get("polling_enabled", True):
                await asyncio.sleep(config.get("scheduler_tick_seconds", 30))
                continue

            now = datetime.now(timezone.utc)
            
            # --- Job 1: Ingestion Scraper Polling ---
            poll_interval_min = config.get("default_poll_interval_minutes", 60)
            should_poll = False
            
            if _LAST_POLL_TIME is None:
                should_poll = True
            else:
                elapsed = now - _LAST_POLL_TIME
                if elapsed.total_seconds() >= (poll_interval_min * 60):
                    should_poll = True
            
            if should_poll:
                _LAST_POLL_TIME = now
                logger.info(f"⏰ Scheduler triggering periodic news aggregation at {now.isoformat()}...")
                # Run the processor in a separate thread so it doesn't block the main asyncio loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _run_processor_sync)
                
            # --- Job 2: Email Digest Dispatches ---
            if config.get("digest_scheduler_enabled", True):
                await check_and_dispatch_email_digests()

        except Exception as e:
            logger.error(f"Error inside scheduler background loop: {e}", exc_info=True)
            
        # Sleep for config tick interval (e.g. 30 seconds)
        config = load_scheduler_config()
        await asyncio.sleep(config.get("scheduler_tick_seconds", 30))


def _run_processor_sync():
    """Sync wrapper to execute pipeline runs inside threads."""
    try:
        processor = NewsProcessor(silent=True)
        # Cap articles per source to avoid overloading Ollama on local loops
        processor.run_ingestion_pipeline(limit_per_source=3)
    except Exception as e:
        logger.error(f"Ingestion run failed during scheduled execution: {e}")


async def check_and_dispatch_email_digests():
    """Checks current time against configured digest times and triggers dispatch."""
    global _SENT_DIGESTS_TODAY
    
    email_config = load_email_config()
    if not email_config.get("enabled", True):
        return
        
    tz_name = email_config.get("timezone", "Asia/Kolkata")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")
        
    local_now = datetime.now(tz)
    date_key = local_now.strftime("%Y-%m-%d")
    current_time_str = local_now.strftime("%H:%M")
    
    # Times inside email_config.json, e.g., ["09:00", "18:00"]
    scheduled_times = email_config.get("times") or ["09:00", "18:00"]
    
    for t_str in scheduled_times:
        try:
            # Parse hour/minute
            sch_h, sch_m = map(int, t_str.split(":"))
            sch_time = time(sch_h, sch_m)
            
            # Compare current local time within a 5-minute window of the schedule
            # to avoid missed ticks or repeating sends on the same minute
            sch_datetime = datetime.combine(local_now.date(), sch_time, tzinfo=tz)
            time_diff = abs((local_now - sch_datetime).total_seconds())
            
            digest_key = f"{date_key}:{t_str}"
            
            # Trigger dispatch if:
            # 1. We are within 5 minutes of the scheduled time
            # 2. We haven't sent this specific digest today yet
            if time_diff <= 300 and digest_key not in _SENT_DIGESTS_TODAY:
                _SENT_DIGESTS_TODAY.add(digest_key)
                
                # Determine edition
                edition = "Morning" if sch_h < 12 else "Evening"
                logger.info(f"✉️ Scheduler triggering {edition} Email Digest dispatch at {local_now.isoformat()}...")
                
                # Dispatch in a thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, dispatch_gmail_digest, edition)
                
        except Exception as e:
            logger.error(f"Failed checking/dispatching scheduled digest time '{t_str}': {e}")


def start_background_scheduler(app):
    """Spawns the scheduler loop task inside FastAPI startup event context."""
    logger.info("Spawning scheduler loop task in the background...")
    asyncio.create_task(scheduler_loop())
