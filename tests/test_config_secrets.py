import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from ioc_checker.config import load_settings


def test_secrets_override():
    root = pathlib.Path(__file__).resolve().parent.parent
    secret = root / "secrets.toml"
    secret.write_text('kaspersky_token = "secret"\n')
    try:
        s = load_settings()
        assert s.kaspersky_token == "secret"
    finally:
        secret.unlink()
