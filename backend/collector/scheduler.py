"""
APScheduler job definitions — periodic maintenance tasks.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("ghostexodus.scheduler")

scheduler = AsyncIOScheduler()


async def _integrity_check_job():
    """Periodically verify a batch of evidence files."""
    from sqlmodel import Session, select
    from database import engine, EvidenceManifest
    from evidence.archiver import verify_integrity_batch
    await verify_integrity_batch(batch_size=50)
    logger.info("Integrity check batch completed")


async def _entity_link_job():
    """Periodically run entity correlation on unlinked entities."""
    from intelligence.entity_extractor import correlate_new_entities
    await correlate_new_entities()
    logger.info("Entity correlation job completed")


async def _cleanup_frequency_cache():
    """Remove stale frequency cache entries."""
    from datetime import datetime, timedelta
    from sqlmodel import Session, select, delete
    from database import engine, ChannelFrequencyCache
    cutoff = datetime.utcnow() - timedelta(hours=1)
    with Session(engine) as session:
        session.exec(
            delete(ChannelFrequencyCache).where(ChannelFrequencyCache.window_start < cutoff)
        )
        session.commit()


def start_scheduler():
    scheduler.add_job(
        _integrity_check_job,
        trigger=IntervalTrigger(hours=6),
        id="integrity_check",
        replace_existing=True,
    )
    scheduler.add_job(
        _entity_link_job,
        trigger=IntervalTrigger(minutes=30),
        id="entity_link",
        replace_existing=True,
    )
    scheduler.add_job(
        _cleanup_frequency_cache,
        trigger=IntervalTrigger(minutes=15),
        id="freq_cache_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started with jobs: integrity_check, entity_link, freq_cache_cleanup")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
