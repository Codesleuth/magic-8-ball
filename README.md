# Magic 8 Ball

A command-line Magic 8 Ball, like the 1970s/80s toy. It has one change: a
**decision model** picks the answer, not chance alone.

```text
$ magic8 "Will it rain tomorrow?"
  Shake the ball... (press Enter)
  ...
  ▲  OUTLOOK GOOD  ▲
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

**Spec approved for v0.1.** The repo has the spec and design notes. The v0.1
build is in progress.

| Document | What it is |
| --- | --- |
| [docs/SPEC.md](docs/SPEC.md) | Product spec (approved for v0.1) and decisions |
| [docs/answers.md](docs/answers.md) | The 20 classic answers, the fixed answer set |
| [docs/decision-models.md](docs/decision-models.md) | Notes on Jev, Laya and the shared `/v1/systemone` API |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [AGENTS.md](AGENTS.md) | Rules for humans and AI agents who work in this repo |

## Setup (planned)

The ball is a Python CLI, installed with `pipx`. By default it uses a local
[Laya](https://huggingface.co/convaiinnovations/laya) server. Questions stay
on your machine.

```sh
pip install "laya[serve]"
LAYA_PRELOAD=1 laya-serve        # first run downloads about 2.3 GB
```

If the model server is not running, the ball shows an error. It does not
guess an answer.

To use another `/v1/systemone` server (for example hosted Jev), copy
`.env.example` to `.env` and set the values. See
[docs/decision-models.md](docs/decision-models.md).

## Contributing

Read [AGENTS.md](AGENTS.md) first. Use the issue templates for features and
bugs. Record significant design choices as an ADR in [docs/adr/](docs/adr/).
