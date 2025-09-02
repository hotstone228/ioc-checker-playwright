# IOC Checker with Playwright

This project demonstrates a small microservice-style application that accepts Indicators of Compromise (IOCs) and fetches their reputations from services such as VirusTotal and Kaspersky OpenTIP. VirusTotal lookups are performed via [Playwright](https://playwright.dev) while Kaspersky requests use the official REST API. Parsing of IOCs relies on the [iocparser](https://pypi.org/project/iocparser/) library.

## Components

- **FastAPI web UI** – parse and submit IOCs with progress updates.
- **Worker** – consumes a queue and performs lookups against the configured providers (VirusTotal via Playwright, Kaspersky OpenTIP via HTTP API).
- **Queue** – in-memory task queue coordinating the two components.

## Running

```bash
pip install -r requirements.txt
playwright install chromium
python run.py
```

The entry script `run.py` configures the Proactor event loop on Windows before
starting Hypercorn so that Playwright can spawn browser subprocesses.

Open <http://localhost:8000> and paste any text containing IOCs. The left pane auto-parses as you type (or after uploading a file) and the right pane groups supported IOCs (IPv4, FQDN, hashes). Each group provides its own **Scan** button, or use **Scan all** to submit everything. Scan results appear inline next to each IOC with icons and tags, and **Copy malicious** copies all detected malicious IOCs to your clipboard.

Use the **Provider** dropdown to select which reputation service to query. Results are rendered inline with icons and a concise summary of reputation, detection counts, and any tags associated with the IOC.

### Configuration

Runtime options live in `config.toml`:

```toml
worker_count = 2        # number of worker tasks
headless = false        # show browser windows for debugging
log_level = "DEBUG"     # logging verbosity
wait_until = "domcontentloaded" # page load milestone for VirusTotal navigation
providers = ["virustotal", "kaspersky"] # enabled reputation services
# API tokens can be supplied via secrets.toml (see secrets.toml.example)
kaspersky_token = ""
```

Adjust these values to change worker pool size, toggle headless mode, or modify log levels for all services. `wait_until` accepts
any Playwright load milestone: `commit`, `domcontentloaded`, `load`, or `networkidle`.

If present, `secrets.toml` overrides settings from `config.toml` and is ignored by git; copy `secrets.toml.example` and place your `kaspersky_token` there to keep credentials out of version control.

### API

- `POST /parse` – body `{ "text": "..." }` returns detected IOCs grouped by type.
- `POST /parse-file` – multipart upload of a text-based file (`.txt`, `.log`, `.csv`, `.json`) returning detected IOCs.
- `POST /scan` – body `{ "service": "virustotal" | "kaspersky", "iocs": ["..."] }` queues IOCs for the specified service.
- `GET /status/{id}` – retrieve task progress and results.

## Notes

The implementation uses an internal asyncio queue and a single Playwright browser per worker. For larger deployments replace the queue and storage with external services (Redis, etc.) and run multiple worker instances. The API is unified to allow adding more validation services in the future.
