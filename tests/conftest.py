"""Shared test helpers, exposed as fixtures (no cross-module imports of this file).

Fixtures: ``answer_rows``, ``fake_server``, ``closed_port_url``, ``good_response``, ``run_cli``.
"""

from __future__ import annotations

import io
import json
import random
import re
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent

_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*([\w-]+)\s*\|\s*$")
_UNSET: Any = object()


def parse_answers_md() -> list[tuple[str, str, str]]:
    """Return (key, text, group) for each table row of docs/answers.md, in order."""
    rows = []
    for line in (ROOT / "docs" / "answers.md").read_text(encoding="utf-8").splitlines():
        m = _ROW.match(line)
        if m:
            rows.append((m.group(2), m.group(3), m.group(4)))
    return rows


def build_good_response(
    probabilities: dict[str, float],
    choice: Any = _UNSET,
    confidence: Any = 0.42,
    model: Any = "fake-1",
) -> dict[str, Any]:
    """A well-formed /v1/systemone response. Pass None to omit choice/confidence/model."""
    if choice is _UNSET:
        choice = max(probabilities, key=lambda k: probabilities[k]) if probabilities else None
    answer: dict[str, Any] = {"type": "choice", "probabilities": probabilities}
    if choice is not None:
        answer["choice"] = choice
    if confidence is not None:
        answer["confidence"] = confidence
    data: dict[str, Any] = {"answers": {"answer": answer}}
    if model is not None:
        data["model"] = model
    return data


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    json: Any


@dataclass
class FakeServer:
    """A /v1/systemone stand-in on 127.0.0.1 with a random port."""

    status: int = 200
    body: Any = field(default_factory=lambda: build_good_response({"yes": 1.0}))
    delay: float = 0.0
    requests: list[RecordedRequest] = field(default_factory=list)

    def __post_init__(self) -> None:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    parsed = json.loads(raw) if raw else None
                except ValueError:
                    parsed = None
                outer.requests.append(
                    RecordedRequest(
                        method=self.command,
                        path=self.path,
                        headers={k.lower(): v for k, v in self.headers.items()},
                        json=parsed,
                    )
                )
                if outer.delay:
                    threading.Event().wait(outer.delay)
                body = outer.body
                payload = body if isinstance(body, bytes) else json.dumps(body).encode()
                try:
                    self.send_response(outer.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            do_POST = _handle
            do_GET = _handle

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            block_on_close = False

            def handle_error(self, request: Any, client_address: Any) -> None:
                pass

        self._httpd = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def __enter__(self) -> FakeServer:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


def _closed_port_url() -> str:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def answer_rows() -> list[tuple[str, str, str]]:
    rows = parse_answers_md()
    assert rows, "could not parse docs/answers.md"
    return rows


@pytest.fixture
def fake_server():
    with FakeServer() as server:
        yield server


@pytest.fixture
def closed_port_url() -> Callable[[], str]:
    return _closed_port_url


@pytest.fixture
def good_response() -> Callable[..., dict[str, Any]]:
    return build_good_response


@pytest.fixture
def run_cli(tmp_path: Path) -> Callable[..., tuple[int, str, str]]:
    """Call magic8.cli.main with injected, non-TTY streams and an empty cwd."""

    def _run(
        *argv: str,
        env: dict[str, str] | None = None,
        stdin_text: str = "",
        rng_seed: int = 0,
        transport: Any = None,
    ) -> tuple[int, str, str]:
        from magic8.cli import main

        stdout, stderr = io.StringIO(), io.StringIO()
        code = main(
            list(argv),
            env=env or {},
            stdin=io.StringIO(stdin_text),
            stdout=stdout,
            stderr=stderr,
            cwd=tmp_path,
            rng=random.Random(rng_seed),
            transport=transport,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    return _run
