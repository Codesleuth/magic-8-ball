# Decision models

Research notes, October 2026. Check the vendor docs before you build on any
detail here. Some public benchmark claims about these models are from vendor
or vendor-adjacent sources and are not verified.

## What a decision model is

A decision model does not write text. You give it some **state** (text) and
one or more **questions**. It returns bounded answers:

| Question type | Returns |
| --- | --- |
| `choice` | One option from a list, a probability for every option, and a confidence value |
| `score` | A number from ordered levels, with a confidence value |
| `noul` | A 0–1 probability of "yes" |

This fits the Magic 8 Ball well. The ball must pick one of 20 fixed answers,
and must never show free text.

## Candidates

| | Jev | Laya | Span-02 |
| --- | --- | --- | --- |
| Maker | TypeSafe AI | Convai Innovations | Respan |
| Delivery | Hosted API only | Open weights, run locally or self-host | Open weights and hosted API |
| License | Proprietary | Apache 2.0 | Apache 2.0 |
| Max `choice` options | 255 | ~20 at default settings (`predict_shortlist` for more) | Not checked |
| Context | Up to 64k tokens | 512 (English), 1,024 (multilingual / typed) | Not checked |
| Cost | ~$0.042 / 1M input tokens, output free | Free (your own compute) | ~$0.01 / 1M input tokens |
| Latency (reported) | ~70–500 ms | ~40 ms on a T4 GPU; ~450 ms on CPU | Not checked |

Links:

- Jev: <https://typesafe.ai>, API docs <https://docs.typesafe.ai/api>,
  confidence guide <https://docs.typesafe.ai/confidence>
- Laya: <https://huggingface.co/convaiinnovations/laya>,
  code <https://github.com/NandhaKishorM/laya>, `pip install "laya[serve]"`
- Span-02: <https://huggingface.co/respanai/span-02>,
  docs <https://www.respan.ai/docs/documentation/overview>
- Hosted access to both Jev and Laya is also sold by Runware
  (`typesafe:jev@latest`, `runware:laya@1`).

## The shared API: `POST /v1/systemone`

Jev's hosted API and Laya's `laya-serve` server use the **same wire
protocol**. Span-02 also says it is Jev-compatible. So the ball needs only one
HTTP client. The user picks the backend with a base URL and an API key.

| Backend | Base URL | Auth |
| --- | --- | --- |
| Jev (hosted) | `https://api.typesafe.ai` | `Authorization: Bearer <key>` |
| Laya (local) | `http://127.0.0.1:8000` (default `laya-serve` port) | Optional: set `LAYA_API_KEY` on the server |

Start a local Laya server:

```sh
pip install "laya[serve]"
LAYA_PRELOAD=1 laya-serve          # CPU works; CUDA / MPS used if present
```

The three Laya checkpoints are about 2.3 GB on disk. They download on first
use.

### Example request for the ball

```json
{
  "model": "jev-latest",
  "state": "Question from the user: \"Will it rain tomorrow?\"",
  "questions": {
    "answer": {
      "type": "choice",
      "instructions": "You are a Magic 8 Ball. Pick the answer that best fits the user's yes/no question.",
      "criteria": {
        "it_is_certain": "It is certain.",
        "it_is_decidedly_so": "It is decidedly so.",
        "...": "(all 20 keys from docs/answers.md)",
        "very_doubtful": "Very doubtful."
      }
    }
  }
}
```

### Example response (Jev, shape from the docs)

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "answer": {
      "type": "choice",
      "choice": "outlook_good",
      "probabilities": { "it_is_certain": 0.04, "outlook_good": 0.31, "...": 0.0 },
      "confidence": 0.42
    }
  },
  "usage": { "input_tokens": 512, "output_tokens": 34 }
}
```

`probabilities` sums to 1. `choice` is the option with the highest
probability. `confidence` is 0–1.

## Points to keep in mind

- **Calibration.** Laya's model cards warn that its probabilities can be
  overconfident. This matters less for a toy, but do not treat the numbers as
  true odds.
- **Option limit.** 20 answers is at Laya's comfortable limit. A two-step
  design (first pick a group, then an answer in the group) avoids this. See
  the open questions in [SPEC.md](SPEC.md).
- **Prompt injection.** The user's question goes into `state`. A decision
  model can only return one of our option keys, so the user cannot make the
  ball print other text. Still validate that the returned key is one of the
  20.
- **Offline / no key.** Decide what the ball does if no backend is set or the
  call fails. See [SPEC.md](SPEC.md).
