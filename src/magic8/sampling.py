"""Weighted random choice of an answer key."""

import random
from collections.abc import Mapping

from magic8.answers import ANSWERS


def pick(probabilities: Mapping[str, float], rng: random.Random) -> str:
    keys = [a.key for a in ANSWERS]
    weights = [probabilities.get(key, 0.0) for key in keys]
    return rng.choices(keys, weights=weights, k=1)[0]
