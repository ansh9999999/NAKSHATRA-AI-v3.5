from apscheduler.schedulers.background import BackgroundScheduler
from scanner import market_scan
from logger import logger

scheduler = BackgroundScheduler()


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running.")
        return

    scheduler.add_job(
        market_scan,
        "interval",
        minutes=5,
        id="market_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    scheduler.start()

    logger.info("Scheduler Started")

    # Run immediately on startup
    market_scan()
