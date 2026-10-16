# 0001. Talk to decision models through the `/v1/systemone` API

- Status: Accepted
- Date: 2026-10-17

## Context

The ball needs a decision model to pick one of 20 answers. The likely
candidates are Jev (hosted, TypeSafe AI) and Laya (open weights, Convai
Innovations). Span-02 (Respan) is another option.

Jev's hosted API and Laya's `laya-serve` server use the same wire protocol:
`POST /v1/systemone` with `state` and `questions`, and the same `choice` /
`score` / `noul` answer shapes. Span-02 also says it is Jev-compatible.

## Decision

The ball has one HTTP client for `POST /v1/systemone`. The user selects the
backend with `MAGIC8_BASE_URL`, `MAGIC8_API_KEY` and `MAGIC8_MODEL`. We do
not use vendor SDKs or run model weights inside the CLI process.

## Consequences

- One code path for Jev, local Laya and other compatible servers.
- Small CLI: no ML dependencies. Users who want Laya run `laya-serve`
  themselves.
- If a vendor changes its API, we must update the client. Keep the client in
  one module with tests against a fake server.
