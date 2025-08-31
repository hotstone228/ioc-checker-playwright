# IOC Checker with Playwright

This project demonstrates a small microservice-style application that accepts Indicators of Compromise (IOCs) and fetches their VirusTotal web results using [Playwright](https://playwright.dev).

## Components

- **FastAPI web UI** – submit IOCs and view progress.
- **Worker** – consumes a queue and performs VirusTotal lookups through the public web interface (no API key required).
- **Queue** – in-memory task queue coordinating the two components.

## Running

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn ioc_checker.main:app --reload
```

Open <http://localhost:8000> and paste IOCs (IPs, domains, or hashes). Each IOC is queued and processed by Playwright workers with live status updates.

## Notes

The implementation uses an internal asyncio queue and a single Playwright browser per worker. For larger deployments replace the queue and storage with external services (Redis, etc.) and run multiple worker instances.
