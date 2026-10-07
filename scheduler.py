"""
NAKSHATRA AI
Scheduler
"""

import os

from apscheduler.schedulers.background import BackgroundScheduler


from logger import logger


scheduler = BackgroundScheduler()


def start_scheduler():

    # Render runs the web API in the same process. The market scanner can be
    # memory/CPU heavy and may cause the web service to be restarted/recovered.
    # Keep the scheduler opt-in; enable it explicitly when desired.
    enabled = os.getenv("NAKSHATRA_SCHEDULER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        logger.info("NAKSHATRA background scheduler disabled (set NAKSHATRA_SCHEDULER_ENABLED=true to enable)")
        return

    if scheduler.running:
        logger.info("Scheduler already running")
        return

    # Lazy-import heavy modules only when scheduler is explicitly enabled.
    from scanner import market_scan
    from monitor.trade_monitor import monitor_open_trades

    # Run market scanner every 5 minutes
    scheduler.add_job(
        market_scan,
        "interval",
        minutes=5,
        id="market_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )

    # Monitor open trades every 1 minute
    scheduler.add_job(
        monitor_open_trades,
        "interval",
        minutes=1,
        id="trade_monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )

    scheduler.start()

    logger.info("===================================")
    logger.info("NAKSHATRA AI Scheduler Started")
    logger.info("Market Scan : Every 5 Minutes")
    logger.info("Trade Monitor : Every 1 Minute")
    logger.info("===================================")


def stop_scheduler():

    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler Stopped")
