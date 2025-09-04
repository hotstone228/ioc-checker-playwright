from dataclasses import dataclass, field
from pathlib import Path
import logging
import tomllib
from typing import Literal


@dataclass
class Settings:
    worker_count: int = 2
    headless: bool = False
    log_level: str = "DEBUG"
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "domcontentloaded"
    providers: list[str] = field(default_factory=lambda: ["kaspersky"])
    database_url: str = "sqlite+aiosqlite:///./cache.db"


def load_settings() -> Settings:
    base = Path(__file__).resolve().parent.parent
    path = base / "config.toml"
    data = {}
    if path.exists():
        data = tomllib.loads(path.read_text())
    valid = {"commit", "domcontentloaded", "load", "networkidle"}
    if data.get("wait_until") not in valid:
        data.pop("wait_until", None)
    if not isinstance(data.get("providers"), list):
        data.pop("providers", None)
    return Settings(**data)


settings = load_settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
