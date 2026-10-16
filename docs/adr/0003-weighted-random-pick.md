# 0003. Pick the answer by weighted random sample

- Status: Accepted
- Date: 2026-10-17

## Context

The decision model returns a probability for each of the 20 answers and its
own top `choice`. The ball can always show the top choice (argmax), or pick
at random using the probabilities as weights.

## Decision

Pick at random, weighted by the returned `probabilities`. Ignore keys that
are not in the answer set and normalise the rest. If no valid weight is left,
treat it as a backend error ([ADR 0004](0004-fail-on-backend-error.md)).

## Consequences

- The ball feels like the toy: asking again can give a different answer.
- The model still sets the odds, so the answer fits the question most of the
  time.
- The shown answer is sometimes not the model's top `choice`. `--json` and
  `--verbose` show both.
- The random source must accept a seed so tests are repeatable.
- Laya's probabilities can be overconfident. With sampling this only makes
  the ball less random; it does not break it.
