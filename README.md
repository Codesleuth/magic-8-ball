# Magic 8 Ball

A command-line Magic 8 Ball, like the 1970s/80s toy. It has one change: a
**decision model** picks the answer, not chance alone.

```text
$ magic8 "Will it rain tomorrow?"
  Shake the ball... (press Enter)
  ...
  ▲  Outlook good.  ▲
```

## How it works

1. You type a yes/no question.
2. You "shake" the ball.
3. The ball sends your question and the 20 classic answers to a decision
   model (for example [Jev](https://typesafe.ai) or
   [Laya](https://huggingface.co/convaiinnovations/laya)).
4. The model gives a probability for each answer. The ball shows one of them.

The ball only ever shows one of the
[20 classic answers](docs/answers.md). It never shows generated text.

## Status

**v0.1.** The spec is approved and the CLI is built to it.

| Document | What it is |
| --- | --- |
| [docs/SPEC.md](docs/SPEC.md) | Product spec (approved for v0.1) and decisions |
| [docs/answers.md](docs/answers.md) | The 20 classic answers, the fixed answer set |
| [docs/decision-models.md](docs/decision-models.md) | Notes on Jev, Laya and the shared `/v1/systemone` API |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [AGENTS.md](AGENTS.md) | Rules for humans and AI agents who work in this repo |

## Install

Install with [uv](https://docs.astral.sh/uv/). uv downloads Python 3.11 or
later if it is missing.

```sh
uv tool install git+https://github.com/Codesleuth/magic-8-ball
```

Or from a clone: `uv tool install .`

To try the ball without installing it (start the decision model first, see
below):

```sh
uvx --from git+https://github.com/Codesleuth/magic-8-ball magic8 "Will it rain?"
```

pipx also works (needs Python 3.11 or later):
`pipx install git+https://github.com/Codesleuth/magic-8-ball`

### Start the decision model

By default the ball uses a local
[Laya](https://huggingface.co/convaiinnovations/laya) server at
`http://127.0.0.1:8000`. Questions stay on your machine.

```sh
pip install "laya[serve]"
LAYA_PRELOAD=1 laya-serve        # first run downloads about 2.3 GB
```

If the model server is not running, the ball shows an error and exits with
code `2`. It does not guess an answer.

## Usage

```text
magic8 [QUESTION]            Ask a question. Prompts if QUESTION is missing.
  --no-shake                 Skip the shake step and animation.
  --backend <url>            Override MAGIC8_BASE_URL.
  --model <name>             Override MAGIC8_MODEL.
  --json                     Print the answer key, text, group and probabilities as JSON.
  --verbose                  Show the model, confidence and latency.
  --version, --help
```

```sh
magic8 "Should I learn the accordion?"     # press Enter to shake
magic8 --no-shake "Will it rain tomorrow?"
magic8 --json "Is this a good idea?"
```

Exit codes: `0` answer shown, `1` usage error, `2` backend error, `130`
stopped with Ctrl-C.

### Configuration

Settings come from environment variables, or from a `.env` file in the
current directory. Copy `.env.example` to `.env` to start.

| Variable | Default |
| --- | --- |
| `MAGIC8_BASE_URL` | `http://127.0.0.1:8000` (local `laya-serve`) |
| `MAGIC8_API_KEY` | empty (no `Authorization` header) |
| `MAGIC8_MODEL` | empty (no `model` field; the server picks) |
| `MAGIC8_TIMEOUT_MS` | `5000` |

To use hosted Jev instead, set `MAGIC8_BASE_URL=https://api.typesafe.ai`,
`MAGIC8_API_KEY` and `MAGIC8_MODEL=jev-latest`. See
[docs/decision-models.md](docs/decision-models.md).

Set `NO_COLOR` to turn off colour.

## Contributing

Read [AGENTS.md](AGENTS.md) first. Use the issue templates for features and
bugs. Record significant design choices as an ADR in [docs/adr/](docs/adr/).
