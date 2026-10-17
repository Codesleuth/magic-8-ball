# 0002. Build the CLI in Python, install with pipx

- Status: Accepted. Install part superseded by [0006](0006-install-with-uv.md)
- Date: 2026-10-17

## Context

The ball is a small CLI. The two options were TypeScript on Node.js
(install with `npx`) or Python. The default backend is Laya
([ADR 0005](0005-default-backend-local-laya.md)), and Laya's server is a
Python package (`pip install "laya[serve]"`). Users who run Laya already have
Python.

## Decision

Write the CLI in Python. Ship it as a normal Python package with a `magic8`
console script. Users install it with `pipx install`. Publish to PyPI later.

## Consequences

- One language for the ball and the local model server. Fewer tools for
  users to install.
- The CLI still talks to the model over HTTP
  ([ADR 0001](0001-use-systemone-api.md)). Do not import Laya or other ML
  libraries into the CLI.
- Lowest version Python 3.11; HTTP client `httpx` (SPEC Q9, decided 2026-10-17).
