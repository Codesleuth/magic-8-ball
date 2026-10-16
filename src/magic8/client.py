"""HTTP client for a /v1/systemone decision-model server."""

import math
import time
from dataclasses import dataclass

import httpx

from magic8.answers import ANSWERS, BY_KEY
from magic8.config import DEFAULT_BASE_URL, Config

INSTRUCTIONS = "You are a Magic 8 Ball. Pick the answer that best fits the user's yes/no question."
QUESTION_ID = "answer"

BAD_RESPONSE_MESSAGE = "The decision model sent a response the ball can't read."


class BackendError(Exception):
    """A backend failure. Codes: unreachable, timeout, auth, http_error, bad_response."""

    def __init__(self, code: str, message: str, detail: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


@dataclass(frozen=True)
class ModelResult:
    probabilities: dict[str, float]  # all 20 keys, ANSWERS order, normalised to sum 1
    model_choice: str | None
    confidence: float | None
    model: str | None
    latency_ms: int


def build_request(question: str, model: str | None) -> dict:
    body: dict = {
        "state": f'Question from the user: "{question}"',
        "questions": {
            QUESTION_ID: {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": {a.key: a.text for a in ANSWERS},
            }
        },
    }
    if model is not None:
        body["model"] = model
    return body


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _bad_response() -> BackendError:
    return BackendError("bad_response", BAD_RESPONSE_MESSAGE)


def parse_response(data: object, latency_ms: int = 0) -> ModelResult:
    if not isinstance(data, dict):
        raise _bad_response()
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise _bad_response()
    answer = answers.get(QUESTION_ID)
    if not isinstance(answer, dict):
        raise _bad_response()
    raw = answer.get("probabilities")
    if not isinstance(raw, dict):
        raise _bad_response()

    known: dict[str, float] = {}
    for key, value in raw.items():
        if key not in BY_KEY:
            continue
        if not _is_number(value) or not math.isfinite(value) or value < 0:
            raise _bad_response()
        known[key] = float(value)
    if not known:
        raise _bad_response()
    total = sum(known.values())
    if total <= 0 or not math.isfinite(total):
        raise _bad_response()

    probabilities = {a.key: known.get(a.key, 0.0) / total for a in ANSWERS}

    choice = answer.get("choice")
    model_choice = choice if isinstance(choice, str) and choice in BY_KEY else None
    conf = answer.get("confidence")
    confidence = float(conf) if _is_number(conf) and math.isfinite(conf) else None
    model = data.get("model")
    return ModelResult(
        probabilities=probabilities,
        model_choice=model_choice,
        confidence=confidence,
        model=model if isinstance(model, str) else None,
        latency_ms=latency_ms,
    )


def ask(
    question: str, config: Config, *, transport: httpx.BaseTransport | None = None
) -> ModelResult:
    headers = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    body = build_request(question, config.model)
    url = f"{config.base_url}/v1/systemone"
    try:
        with httpx.Client(transport=transport, timeout=config.timeout_ms / 1000) as client:
            started = time.monotonic()
            response = client.post(url, json=body, headers=headers)
            latency_ms = round((time.monotonic() - started) * 1000)
    except httpx.TimeoutException as exc:
        secs = f"{config.timeout_ms / 1000:g}"
        raise BackendError("timeout", f"The decision model did not answer in {secs} s.") from exc
    except (httpx.TransportError, httpx.InvalidURL) as exc:
        if config.base_url == DEFAULT_BASE_URL:
            message = (
                f"Can't reach the decision model at {DEFAULT_BASE_URL}. "
                "Start a local Laya server with: laya-serve"
            )
        else:
            message = f"Can't reach the decision model at {config.base_url}."
        raise BackendError("unreachable", message) from exc

    status = response.status_code
    if status in (401, 403):
        raise BackendError("auth", "The decision model rejected the API key. Check MAGIC8_API_KEY.")
    if not 200 <= status <= 299:
        raise BackendError(
            "http_error",
            f"The decision model returned an error (HTTP {status}).",
            response.text.strip()[:500] or None,
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise _bad_response() from exc
    return parse_response(data, latency_ms)
