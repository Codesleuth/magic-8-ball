# 0005. Use a local Laya server as the default backend

- Status: Accepted
- Date: 2026-10-17

## Context

Two backends use the same `/v1/systemone` API
([ADR 0001](0001-use-systemone-api.md)): Jev (hosted, needs an API key, paid)
and Laya (open weights, Apache 2.0, runs locally with `laya-serve`, about
2.3 GB to download).

## Decision

The default `MAGIC8_BASE_URL` is `http://127.0.0.1:8000`, the default
`laya-serve` address. `MAGIC8_API_KEY` and `MAGIC8_MODEL` are empty by
default. When `MAGIC8_MODEL` is empty, the request has no `model` field and
the Laya router picks a checkpoint. Jev stays supported by setting the base
URL, key and model.

## Consequences

- Free and private: questions stay on the user's machine.
- First-time setup is heavier: `pip install "laya[serve]"`, then a 2.3 GB
  download on first use. The README must explain this.
- The first request after a cold start can be slow. Recommend
  `LAYA_PRELOAD=1 laya-serve` and check the 5 s default timeout during the
  smoke test.
- 20 options is near Laya's comfortable limit for `choice`. Watch answer
  quality in the smoke test; the two-step design (SPEC Q2) is the fallback
  plan.
