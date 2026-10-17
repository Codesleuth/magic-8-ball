"""Configuration from flags, the environment and a .env file."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_MS = 5000
MAX_TIMEOUT_MS = 2**31 - 1  # SPEC 6: larger values are used as this; it fits every platform


class ConfigError(Exception):
    """A configuration problem. The message is user-facing."""


@dataclass(frozen=True)
class Config:
    base_url: str  # trailing "/" stripped
    api_key: str | None  # None when empty
    model: str | None  # None when empty
    timeout_ms: int


def read_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple .env file. A missing or unreadable file gives an empty dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def load_config(
    env: Mapping[str, str],
    dotenv_path: Path | None,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> Config:
    """Build a Config. Precedence: flag > real environment > .env > default."""
    merged: dict[str, str] = {**(read_dotenv(dotenv_path) if dotenv_path else {}), **env}

    def pick(flag: str | None, name: str) -> str:
        if flag:
            return flag
        return merged.get(name, "")

    url = pick(base_url, "MAGIC8_BASE_URL") or DEFAULT_BASE_URL
    api_key = pick(None, "MAGIC8_API_KEY") or None
    model_name = pick(model, "MAGIC8_MODEL") or None

    raw = merged.get("MAGIC8_TIMEOUT_MS", "")
    if raw == "":
        timeout_ms = DEFAULT_TIMEOUT_MS
    else:
        try:
            timeout_ms = int(raw)
        except ValueError:
            timeout_ms = 0
        if timeout_ms <= 0:
            raise ConfigError(
                f"MAGIC8_TIMEOUT_MS must be a positive whole number of milliseconds, got {raw!r}."
            )
        timeout_ms = min(timeout_ms, MAX_TIMEOUT_MS)

    # The key goes in an HTTP header. Never echo it.
    if api_key is not None and not (api_key.isascii() and api_key.isprintable()):
        raise ConfigError("MAGIC8_API_KEY must hold only printable ASCII characters.")

    return Config(
        base_url=url.rstrip("/"),
        api_key=api_key,
        model=model_name,
        timeout_ms=timeout_ms,
    )
