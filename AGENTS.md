# Working in this repo

These rules apply to humans and AI coding agents.

## Read first

1. [docs/SPEC.md](docs/SPEC.md) — what we are building. The spec wins over
   code comments and old issues.
2. [docs/answers.md](docs/answers.md) — the fixed answer set.
3. [docs/decision-models.md](docs/decision-models.md) — the backend API.
4. [docs/adr/](docs/adr/) — decisions already made.

## Rules

- **The answer set is fixed.** The ball shows only the 20 answers in
  `docs/answers.md`, with the exact text. Changing them needs an ADR.
- **No free text from the model.** Only use decision-model answers (option
  keys and probabilities). Always check the returned key is one of the 20.
- **No real model calls in tests or CI.** Use a fake `/v1/systemone` server
  or an HTTP mock. Seed any randomness in tests.
- **No secrets in the repo.** Keys go in `.env` (git-ignored). Keep
  `.env.example` up to date when you add a setting.
- **Spec first.** If the code needs to do something the spec does not say,
  update `docs/SPEC.md` in the same change, or open an issue.
- **Small changes.** One topic per pull request. Fill in the PR template.

## Stack

Python, installed with `pipx` ([ADR 0002](docs/adr/0002-python.md)). The
CLI talks to the model over HTTP only. Do not add ML libraries to the CLI.

The code is in `src/magic8/`, the tests in `tests/`. Development uses
[uv](https://docs.astral.sh/uv/):

```sh
uv sync                      # create .venv with the package and dev tools
uv run pytest -q             # tests (fake server and HTTP mocks only)
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run magic8 --help         # run the CLI from the checkout
```

CI (`.github/workflows/ci.yml`) runs lint and the tests on Python 3.11–3.14
for every push and pull request.
