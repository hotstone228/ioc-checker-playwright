from dataclasses import dataclass
from pathlib import Path
import logging
import tomllib
from typing import Literal


@dataclass
class Settings:
    worker_count: int = 2
    headless: bool = False
    log_level: str = "INFO"
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "networkidle"


def load_settings() -> Settings:
    path = Path(__file__).resolve().parent.parent / "config.toml"
    data = {}
    if path.exists():
        data = tomllib.loads(path.read_text())
    valid = {"commit", "domcontentloaded", "load", "networkidle"}
    if data.get("wait_until") not in valid:
        data.pop("wait_until", None)
    return Settings(**data)


settings = load_settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
