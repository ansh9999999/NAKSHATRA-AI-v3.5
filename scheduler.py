from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scanner import market_scan
from logger import logger
from config import SCAN_INTERVAL

scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler():
    try:
        if scheduler.running:
            logger.info("Scheduler is already running.")
            return

        scheduler.add_job(
            market_scan,
            trigger=IntervalTrigger(seconds=SCAN_INTERVAL),
            id="market_scan",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60
        )

        scheduler.start()

        logger.info("===================================")
        logger.info("NAKSHATRA AI Scheduler Started")
        logger.info(f"Scan Interval : {SCAN_INTERVAL} seconds")
        logger.info("===================================")

        # First scan immediately
        market_scan()

    except Exception as e:
        logger.exception(f"Scheduler Start Error: {e}")


def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler Stopped")

    except Exception as e:
        logger.exception(f"Scheduler Stop Error: {e}")
