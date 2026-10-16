# Architecture decision records

We record significant design choices here, one file per decision.

- Name files `NNNN-short-title.md`, numbered in order.
- Copy [0000-template.md](0000-template.md).
- Do not edit an accepted ADR to change the decision. Write a new ADR that
  supersedes it.

| # | Title | Status |
| --- | --- | --- |
| [0001](0001-use-systemone-api.md) | Talk to decision models through the `/v1/systemone` API | Proposed |
| [0002](0002-python.md) | Build the CLI in Python, install with pipx | Accepted |
| [0003](0003-weighted-random-pick.md) | Pick the answer by weighted random sample | Accepted |
| [0004](0004-fail-on-backend-error.md) | Show an error when the decision model is not available | Accepted |
| [0005](0005-default-backend-local-laya.md) | Use a local Laya server as the default backend | Accepted |
