# Magic 8 Ball — Spec (draft)

Status: **draft**. Items marked **OPEN** need a decision before the build
starts. Each one has a recommended default.

## 1. Goal

A CLI toy that feels like the 1970s/80s Magic 8 Ball. The user asks a yes/no
question, shakes the ball, and sees one of the
[20 classic answers](answers.md). A decision model picks the answer.

## 2. Non-goals

- No free-text or chat replies. The ball shows only the 20 answers.
- No GUI or web app (for now).
- No answer history, accounts or telemetry.
- No training or fine-tuning of models.

## 3. User flow

1. User runs the CLI, with the question as an argument or at a prompt.
2. The ball asks the user to shake it (for example, press Enter).
3. While the "shake" plays, the ball calls the decision model.
4. The ball shows the answer in the window of the ball, then exits.

```text
$ magic8 "Should I learn the accordion?"
  🎱  Shake the ball... (press Enter)
  ~ ~ ~ the die floats up ~ ~ ~
  ▲  SIGNS POINT TO YES  ▲
```

## 4. CLI interface (proposed)

```text
magic8 [QUESTION]            Ask a question. Prompts if QUESTION is missing.
  --no-shake                 Skip the shake step and animation.
  --backend <url>            Override MAGIC8_BASE_URL.
  --model <name>             Override MAGIC8_MODEL.
  --json                     Print the answer key, text, group and probabilities as JSON.
  --verbose                  Show the model, confidence and latency.
  --version, --help
```

Exit codes: `0` answer shown, `1` usage error, `2` backend error (only if
fallback is off, see 6.3).

## 5. Configuration

Read from environment variables (and from `.env` in the working directory).

| Variable | Meaning | Example |
| --- | --- | --- |
| `MAGIC8_BASE_URL` | Base URL of a `/v1/systemone` server | `https://api.typesafe.ai` or `http://127.0.0.1:8000` |
| `MAGIC8_API_KEY` | Bearer token, if the server needs one | — |
| `MAGIC8_MODEL` | Model name sent in the request | `jev-latest` |
| `MAGIC8_TIMEOUT_MS` | Request timeout | `5000` |

## 6. How the decision works

### 6.1 The request

One `POST {MAGIC8_BASE_URL}/v1/systemone` with:

- `state`: the user's question, wrapped in a short fixed frame.
- one `choice` question. `criteria` has the 20 answer keys from
  [answers.md](answers.md). The value for each key is the answer text.

See [decision-models.md](decision-models.md) for the full shape.

### 6.2 Picking the answer from the response

The model returns a probability for each of the 20 answers.

**OPEN Q1 — argmax or sample?**

- *Argmax*: always show `choice`. The same question gives the same answer.
  This feels less like a toy.
- *Sample* (recommended): pick an answer at random, weighted by
  `probabilities`. The model sets the odds; the shake adds chance. Asking
  again can give a different answer, like the real ball.

**OPEN Q2 — one step or two steps?**

- *One step* (recommended to start): one `choice` over all 20 answers.
- *Two steps*: first a `choice` over the 3 groups (affirmative /
  non-committal / negative), then a random answer in that group. Fewer
  options per call (better for Laya), but less nuance.

**OPEN Q3 — use `confidence`?** Proposal: if `confidence` is below a
threshold (for example 0.2), show a non-committal answer ("Reply hazy, try
again."). This matches the toy and handles questions that are not yes/no.

### 6.3 When the backend fails

**OPEN Q4 — fallback.** If there is no backend, or the call fails or times
out:

- *Fallback to classic* (recommended): pick one of the 20 answers uniformly
  at random, like the real toy. Show a short note only with `--verbose`.
- *Fail*: print an error and exit `2`.

Always check that the returned key is one of the 20. If not, treat it as a
failure.

## 7. The "shake"

- Default: wait for Enter, then play a short text animation (about 1–2 s)
  while the request runs. The answer shows when both are done.
- `--no-shake` and non-TTY output (pipes, CI) skip the wait and animation.
- Animation must work in a plain 80-column terminal. Colour is optional and
  off when `NO_COLOR` is set.

## 8. Quality

- Unit tests for: answer set (exactly 20, stable keys), response parsing,
  sampling (seeded), confidence rule, fallback.
- A fake `/v1/systemone` server or HTTP mock for tests. No real model calls
  in CI.
- One optional, manual smoke test against a real backend (Jev or local Laya).

## 9. Open questions

| # | Question | Recommended default |
| --- | --- | --- |
| Q1 | Argmax or sample from probabilities? | Sample |
| Q2 | One `choice` over 20, or group first? | One step |
| Q3 | Low confidence → non-committal answer? | Yes, threshold to tune |
| Q4 | Fallback when the backend fails? | Classic random answer |
| Q5 | Language and runtime? | TypeScript on Node.js (single `npx` install) — or Python, which matches Laya's own tooling |
| Q6 | Default backend? | Jev hosted (no 2.3 GB download); document local Laya as the private, free option |
| Q7 | License? | Not chosen yet — owner decides |
| Q8 | How to distribute? | npm package (if TS) or PyPI / `pipx` (if Python) |

When a question is decided, update this file and add an ADR in
[adr/](adr/).
