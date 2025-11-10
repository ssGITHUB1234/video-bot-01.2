"""
WSGI Entry Point for Production Deployment
Use this file with Gunicorn for production deployment on Render

NOTE: Bot initialization happens in gunicorn_config.py post_fork hook
to avoid threading issues with process forking.
"""

from main import app
import logging

logger = logging.getLogger(__name__)

logger.info("WSGI module loaded - bot will initialize after worker fork")

if __name__ == "__main__":
    app.run()
