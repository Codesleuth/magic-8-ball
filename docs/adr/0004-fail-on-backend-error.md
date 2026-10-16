# 0004. Show an error when the decision model is not available

- Status: Accepted
- Date: 2026-10-17

## Context

The backend can be missing (server not started), fail, time out, or send a
bad response. The ball could fall back to a uniform random classic answer,
like the real toy, or it could stop with an error.

## Decision

Do not fall back. Stop the animation, print a short error to stderr that
says what to do next, show no answer, and exit with code `2`. The error
messages are listed in SPEC section 7.3.

## Consequences

- Every answer the ball shows comes from the decision model. Users are never
  misled about where an answer came from.
- With the local Laya default, the most common error will be "server not
  running". The message must tell the user to run `laya-serve`.
- The ball does not work offline without a local server. This is accepted.
