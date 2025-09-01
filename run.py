import asyncio
import sys
import uvicorn

# Configure the proper event loop on Windows before importing the app
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from ioc_checker.main import app

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000, reload=True)
