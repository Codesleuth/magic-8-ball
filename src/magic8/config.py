"""Configuration from flags, the environment and a .env file."""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_MS = 5000
MAX_TIMEOUT_MS = 2**31 - 1  # SPEC 6: larger values are used as this; it fits every platform

_DIGIT_GROUPS = re.compile(r"\d(?:_?\d)*")  # digits, with the single "_" int() allows between them


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


def _parse_timeout_ms(raw: str) -> int | None:
    """The value as int() reads it, capped at MAX_TIMEOUT_MS; None if it is not above 0.

    int() refuses more than 4300 digits, but such a value is still a whole number (SPEC 6).
    So int() checks the form on a copy with each group of digits (and the "_" between them)
    cut to one digit, and the digits are read here.
    """
    try:
        sign = int(_DIGIT_GROUPS.sub("1", raw))
    except ValueError:
        return None
    digits = "".join(str(unicodedata.decimal(c)) for c in raw if c.isdecimal()).lstrip("0")
    if sign < 0 or not digits:
        return None
    return min(int(digits[:11]), MAX_TIMEOUT_MS)  # 11 digits are already above the cap


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
        parsed = _parse_timeout_ms(raw)
        if parsed is None:
            raise ConfigError(
                f"MAGIC8_TIMEOUT_MS must be a positive whole number of milliseconds, got {raw!r}."
            )
        timeout_ms = parsed

    # The key goes in an HTTP header, which can't start or end with a space. Never echo it.
    if api_key is not None and not (
        api_key.isascii() and api_key.isprintable() and api_key.strip() == api_key
    ):
        raise ConfigError(
            "MAGIC8_API_KEY must hold only printable ASCII characters, "
            "with no space at the start or end."
        )

    return Config(
        base_url=url.rstrip("/"),
        api_key=api_key,
        model=model_name,
        timeout_ms=timeout_ms,
    )
