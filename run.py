import asyncio
import sys
import logging

from hypercorn.asyncio import serve
from hypercorn.config import Config

from ioc_checker.config import settings

# Configure the proper event loop on Windows before importing the app
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from ioc_checker.main import app

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    config = Config()
    config.bind = ["127.0.0.1:8000"]
    config.use_reloader = True
    logger.info("Starting Hypercorn on %s", config.bind)
    asyncio.run(serve(app, config))
