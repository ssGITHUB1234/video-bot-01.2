"""
Gunicorn configuration for Telegram bot
This ensures the bot initializes AFTER the worker process forks
"""
import logging
import os

logger = logging.getLogger(__name__)

# Server socket
port = os.getenv('PORT', '5000')
bind = f"0.0.0.0:{port}"
workers = 1
threads = 4
worker_class = "gthread"
timeout = 300

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    This is the right place to initialize the bot to avoid threading issues.
    """
    logger.info(f"Worker {worker.pid} spawned - initializing bot...")
    
    # Import here to avoid loading before fork
    from main import initialize_bot
    
    try:
        initialize_bot()
        logger.info(f"Bot initialized successfully in worker {worker.pid}")
    except Exception as e:
        logger.error(f"Failed to initialize bot in worker {worker.pid}: {e}", exc_info=True)
