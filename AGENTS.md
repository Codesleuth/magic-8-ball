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

Not chosen yet (see SPEC open question Q5). When it is chosen, add the build,
test and lint commands here.
