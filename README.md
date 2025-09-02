# IOC Checker with Playwright

This project demonstrates a small microservice-style application that accepts Indicators of Compromise (IOCs) and fetches their VirusTotal web results using [Playwright](https://playwright.dev). Parsing of IOCs relies on the [iocparser](https://pypi.org/project/iocparser/) library.

## Components

- **FastAPI web UI** – parse and submit IOCs with progress updates.
- **Worker** – consumes a queue and performs VirusTotal lookups through the public web interface (no API key required).
- **Queue** – in-memory task queue coordinating the two components.

## Running

```bash
pip install -r requirements.txt
playwright install chromium
python run.py
```

The entry script `run.py` configures the Proactor event loop on Windows before
starting Hypercorn so that Playwright can spawn browser subprocesses.

Open <http://localhost:8000> and paste any text containing IOCs. The interface parses the text into categories (IP addresses, domains, hashes, etc.) and lets you submit them for checking. Each IOC is queued and processed by Playwright workers with live status updates.

### Configuration

Runtime options live in `config.toml`:

```toml
worker_count = 2        # number of Playwright workers
headless = false        # show browser windows for debugging
log_level = "INFO"      # logging verbosity
wait_until = "networkidle" # page load milestone for VirusTotal navigation
```

Adjust these values to change worker pool size, toggle headless mode, or modify log levels for all services. `wait_until` accepts
any Playwright load milestone: `commit`, `domcontentloaded`, `load`, or `networkidle`.

### API

- `POST /parse` – body `{ "text": "..." }` returns detected IOCs grouped by type.
- `POST /parse-file` – multipart upload of a text-based file (`.txt`, `.log`, `.csv`, `.json`) returning detected IOCs.
- `POST /scan` – body `{ "service": "virustotal", "iocs": ["..."] }` queues IOCs for the specified service.
- `GET /status/{id}` – retrieve task progress and results.

## Notes

The implementation uses an internal asyncio queue and a single Playwright browser per worker. For larger deployments replace the queue and storage with external services (Redis, etc.) and run multiple worker instances. The API is unified to allow adding more validation services in the future.
