# Magic 8 Ball — Spec (v0.1)

Status: **approved for v0.1** (2026-10-17). Decided items link to their ADR.
To change a decision, write a new ADR in [adr/](adr/).

## 1. Goal

A CLI toy that feels like the 1970s/80s Magic 8 Ball. The user asks a yes/no
question, shakes the ball, and sees one of the
[20 classic answers](answers.md). A decision model picks the answer.

## 2. Non-goals

- No free-text or chat replies. The ball shows only the 20 answers.
- No GUI or web app (for now).
- No answer history, accounts or telemetry.
- No training or fine-tuning of models.
- No offline fallback. If the model is not available, the ball shows an error
  (see 7.3).

## 3. User flow

1. User runs the CLI, with the question as an argument or at a prompt.
2. The ball asks the user to shake it (for example, press Enter).
3. While the "shake" plays, the ball calls the decision model.
4. The ball shows the answer in the window of the ball, then exits.

```text
$ magic8 "Should I learn the accordion?"
  🎱  Shake the ball... (press Enter)
  ~ ~ ~ the die floats up ~ ~ ~
  ▲  Signs point to yes.  ▲
```

The answer is shown with the exact text from [answers.md](answers.md),
including case and punctuation.

## 4. CLI interface

```text
magic8 [QUESTION]            Ask a question. Prompts if QUESTION is missing.
  --no-shake                 Skip the shake step and animation.
  --backend <url>            Override MAGIC8_BASE_URL.
  --model <name>             Override MAGIC8_MODEL.
  --json                     Print the answer key, text, group and probabilities as JSON.
  --verbose                  Show the model, confidence and latency.
  --version, --help
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Answer shown |
| `1` | Usage error (bad flag, empty question, invalid `MAGIC8_TIMEOUT_MS` or `MAGIC8_API_KEY`) |
| `2` | Backend error (see 7.3) |
| `130` | Stopped with Ctrl-C (shell convention) |

## 5. Stack and install

Decided in [ADR 0002](adr/0002-python.md).

- Python 3.11 or later. The CLI is a normal Python package with a `magic8`
  console script.
- HTTP client: `httpx`.
- Users install it with `pipx install` (PyPI release later).
- Keep runtime dependencies small. No ML libraries in the CLI process: the
  model runs in a separate server ([ADR 0001](adr/0001-use-systemone-api.md)).

## 6. Configuration

Read from environment variables (and from `.env` in the working directory).

| Variable | Meaning | Default |
| --- | --- | --- |
| `MAGIC8_BASE_URL` | Base URL of a `/v1/systemone` server | `http://127.0.0.1:8000` (local `laya-serve`) |
| `MAGIC8_API_KEY` | Bearer token, if the server needs one | empty (not sent) |
| `MAGIC8_MODEL` | Model name sent in the request | empty (field not sent; the server picks) |
| `MAGIC8_TIMEOUT_MS` | Request timeout | `5000` |

The real environment wins over `.env`, and `--backend` / `--model` win over
both. An empty value means "not set". `MAGIC8_TIMEOUT_MS` must be a whole
number above 0; anything else is a usage error (exit `1`). A value above
2147483647 (about 24.8 days) is used as 2147483647. `MAGIC8_API_KEY` is sent
in an HTTP header, so it may hold only printable ASCII characters; anything
else is a usage error (exit `1`), and the message does not show the key.

The default backend is a local Laya server
([ADR 0005](adr/0005-default-backend-local-laya.md)). To use Jev instead, set
`MAGIC8_BASE_URL=https://api.typesafe.ai`, `MAGIC8_API_KEY` and
`MAGIC8_MODEL=jev-latest`.

## 7. How the decision works

### 7.1 The request

One `POST {MAGIC8_BASE_URL}/v1/systemone` with:

- `state`: the user's question, wrapped in a short fixed frame.
- one `choice` question. `criteria` has the 20 answer keys from
  [answers.md](answers.md). The value for each key is the answer text.
- `model`: only if `MAGIC8_MODEL` (or `--model`) is set.

See [decision-models.md](decision-models.md) for the full shape.

### 7.2 Picking the answer from the response

Decided in [ADR 0003](adr/0003-weighted-random-pick.md).

The model returns a probability for each of the 20 answers. The ball picks
one answer at random, **weighted by `probabilities`**. The model sets the
odds; the shake adds chance. Asking the same question again can give a
different answer, like the real ball.

- Use only keys that are in the answer set. Ignore any other keys.
- If the probabilities do not sum to 1, normalise them. If they sum to 0, or
  no valid key is present, treat it as a backend error (7.3).
- The random source must accept a seed so tests are repeatable. The seed is
  not a user flag.
- `--json` and `--verbose` show the full probabilities and which answer was
  picked. They also show the model's own top `choice`, which can be
  different.

**Q2 — one step (decided).** Send one `choice` over all 20 answers. Do not
pick a group first. A two-step flow (group, then answer) can come later if
Laya does badly with 20 options.

**Q3 — no confidence rule in v0.1 (decided).** Do not replace low-confidence
results with "Reply hazy, try again." Weighted sampling already spreads the
odds when the model is unsure. `confidence` is shown only with `--json` and
`--verbose`.

### 7.3 When the backend fails

Decided in [ADR 0004](adr/0004-fail-on-backend-error.md).

If the backend cannot be reached, the call fails or times out, or the
response is not valid, the ball does **not** make up an answer. It:

1. Stops the shake animation.
2. Prints a short error to stderr. No answer is shown.
3. Exits with code `2`.

The error says what went wrong and what to do next:

| Case | `--json` code | Message (example) |
| --- | --- | --- |
| Connection refused at the default URL | `unreachable` | `Can't reach the decision model at http://127.0.0.1:8000. Start a local Laya server with: laya-serve` |
| Connection refused at another URL | `unreachable` | `Can't reach the decision model at <url>.` |
| Timeout | `timeout` | `The decision model did not answer in 5 s.` |
| HTTP 401 / 403 | `auth` | `The decision model rejected the API key. Check MAGIC8_API_KEY.` |
| Other HTTP error | `http_error` | `The decision model returned an error (HTTP <code>).` plus the server message with `--verbose` |
| Bad response (missing fields, no valid key, probabilities sum to 0) | `bad_response` | `The decision model sent a response the ball can't read.` |

With `--json`, print `{"error": "<code>", "message": "<text>"}` to stdout
as well, and still exit `2`.

A response is read like this. `answers.answer.probabilities` must be an
object. A value for one of the 20 keys must be a number (of any size) that
is 0 or more; anything else makes the response bad. `choice`, `confidence`
and `model` are optional: they are shown when present, `choice` only if it is
one of the 20 keys, and `confidence` only if it is a finite number that fits
in a 64-bit float.

The HTTP status is checked first: 401 / 403 is `auth` and any other status
outside 2xx is `http_error`, whatever the body. For a 2xx status, a body that
cannot be decoded or parsed (for example a wrong `Content-Encoding`, or JSON
nested too deep) is a bad response.

## 8. The "shake"

- Default: wait for Enter, then play a short text animation (about 1–2 s)
  while the request runs. The answer shows when both are done.
- `--no-shake`, `--json`, and non-TTY input or output (pipes, CI) skip the
  wait and animation. `--json` skips them so stdout holds only JSON.
- Animation must work in a plain 80-column terminal. Colour is optional and
  off when `NO_COLOR` is set.
- On a backend error, stop the animation at once and show the error.

## 9. Quality

- Unit tests for: answer set (exactly 20, stable keys), response parsing,
  weighted sampling (seeded), error cases and exit codes.
- A fake `/v1/systemone` server or HTTP mock for tests. No real model calls
  in CI.
- One optional, manual smoke test against a local `laya-serve` (and Jev if a
  key is available).

## 10. Decisions

| # | Question | Decision |
| --- | --- | --- |
| Q1 | Argmax or sample from probabilities? | **Decided:** weighted random sample ([ADR 0003](adr/0003-weighted-random-pick.md)) |
| Q2 | One `choice` over 20, or group first? | **Decided:** one step, one `choice` over 20 (7.2) |
| Q3 | Low confidence → non-committal answer? | **Decided:** not in v0.1 (7.2) |
| Q4 | What to do when the backend fails? | **Decided:** show an error, exit `2` ([ADR 0004](adr/0004-fail-on-backend-error.md)) |
| Q5 | Language and runtime? | **Decided:** Python ([ADR 0002](adr/0002-python.md)) |
| Q6 | Default backend? | **Decided:** local Laya server ([ADR 0005](adr/0005-default-backend-local-laya.md)) |
| Q7 | License? | **Decided:** no license for now. Revisit before a public release. |
| Q8 | How to distribute? | **Decided:** `pipx` install; PyPI later ([ADR 0002](adr/0002-python.md)) |
| Q9 | Lowest Python version and HTTP library? | **Decided:** Python 3.11+, `httpx` (section 5) |

To change a decision, update this file and add an ADR in [adr/](adr/).
