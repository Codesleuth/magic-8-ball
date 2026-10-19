# 0006. Install with uv; pipx still works

- Status: Accepted
- Date: 2026-10-17

## Context

[ADR 0002](0002-python.md) says users install the CLI with `pipx install`.
Development and CI already use uv (`uv sync`, `uv.lock`, `setup-uv`). So a
contributor needs uv, and a user needs pipx and Python 3.11 or later.

`uv tool install` does the same job as `pipx install`: one isolated
environment per tool, with the `magic8` command on the `PATH`. uv also
downloads Python 3.11 or later if it is missing, and `uvx` runs the ball once
without installing it.

## Decision

uv is the main install path:

- Install: `uv tool install git+https://github.com/Codesleuth/magic-8-ball`
- Try without installing:
  `uvx --from git+https://github.com/Codesleuth/magic-8-ball magic8 "Will it rain?"`

`pipx install git+https://github.com/Codesleuth/magic-8-ball` still works,
because the CLI is a standard Python package. We keep it as an alternative.

This supersedes only the install part of [ADR 0002](0002-python.md). The
rest of ADR 0002 still holds: Python, a normal package with a `magic8`
console script, PyPI later.

## Consequences

- One tool, uv, for users and contributors.
- Users do not need to install Python first.
- Users who have pipx and not uv can keep using pipx.
- The package must stay standard (no uv-only build settings), so that pipx
  keeps working.
- No change to the code, `pyproject.toml`, `uv.lock` or CI.
- The Laya server instructions do not change with this ADR.
