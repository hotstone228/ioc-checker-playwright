# IOC Checker with Playwright

This project demonstrates a small microservice-style application that accepts Indicators of Compromise (IOCs) and fetches their reputations from services such as Kaspersky OpenTIP. Kaspersky requests use the official REST API. Parsing of IOCs relies on the [iocsearcher](https://github.com/malicialab/iocsearcher) library.

## Components

- **FastAPI web UI** – parse and submit IOCs with progress updates.
- **Worker** – consumes a queue and performs lookups against the configured providers (e.g., Kaspersky OpenTIP via HTTP API).
- **Queue** – in-memory task queue coordinating the two components.

## Running

```bash
pip install -r requirements.txt
playwright install chromium
python run.py
```

The entry script `run.py` configures the Proactor event loop on Windows before
starting Hypercorn so that Playwright can spawn browser subprocesses.

Open <http://localhost:8000> and paste any text containing IOCs. The left pane auto-parses as you type (or after uploading a file) and the right pane groups detected IOCs by type such as IPv4/IPv6, domains, URLs, hashes, emails and many others. Only IOCs supported by the chosen provider expose a **Scan** button, or use **Scan all** to submit every scannable IOC. Scan results appear inline next to each IOC with icons and tags, and **Copy malicious** copies all detected malicious IOCs to your clipboard.

Use the **Provider** dropdown in the **Advanced Settings** section to select which reputation service to query. Results are rendered inline with icons and a concise summary of reputation, detection counts, and any tags associated with the IOC.

### Configuration

Runtime options live in `config.toml`:

```toml
worker_count = 2        # number of worker tasks
headless = false        # show browser windows for debugging
log_level = "DEBUG"     # logging verbosity
wait_until = "domcontentloaded" # page load milestone for browser automation
providers = ["kaspersky"] # enabled reputation services
```

Adjust these values to change worker pool size, toggle headless mode, or modify log levels for all services. `wait_until` accepts
any Playwright load milestone: `commit`, `domcontentloaded`, `load`, or `networkidle`.

Provider API tokens must be supplied through the web interface under **Advanced Settings**.


### API

- `POST /parse` – body `{ "text": "..." }` returns detected IOCs grouped by type.
- `POST /parse-file` – multipart upload of a file (text, HTML, PDF, or Word `.docx`) returning detected IOCs.
- `POST /scan` – body `{ "service": "kaspersky", "iocs": ["..."], "token": "..." }` queues IOCs for the specified service (token required when the provider mandates it).
- `GET /status/{id}` – retrieve task progress and results.

## Notes

The implementation uses an internal asyncio queue and a single Playwright browser per worker. For larger deployments replace the queue and storage with external services (Redis, etc.) and run multiple worker instances. The API is unified to allow adding more validation services in the future.
