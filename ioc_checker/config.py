from dataclasses import dataclass
from pathlib import Path
import logging
import tomllib


@dataclass
class Settings:
    worker_count: int = 2
    headless: bool = False
    log_level: str = "INFO"


def load_settings() -> Settings:
    path = Path(__file__).resolve().parent.parent / "config.toml"
    data = {}
    if path.exists():
        data = tomllib.loads(path.read_text())
    return Settings(**data)


settings = load_settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
