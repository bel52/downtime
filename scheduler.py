from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Create a single instance of the scheduler
scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the scheduler if not already running."""
    if not scheduler.running:
        scheduler.start()
        logging.info("Scheduler started.")
    else:
        logging.info("Scheduler is already running.")
