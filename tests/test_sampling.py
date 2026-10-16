"""SPEC 7.2: seeded weighted sampling."""

import random
from collections import Counter

import pytest

from magic8.answers import ANSWERS
from magic8.sampling import pick

KEYS = [a.key for a in ANSWERS]


def sequence(weights, seed, n=50):
    rng = random.Random(seed)
    return [pick(weights, rng) for _ in range(n)]


def test_same_seed_same_sequence():
    weights = {key: 1.0 / 20 for key in KEYS}
    assert sequence(weights, 7) == sequence(weights, 7)


def test_different_seeds_differ():
    weights = {key: 1.0 / 20 for key in KEYS}
    assert sequence(weights, 1) != sequence(weights, 2)


@pytest.mark.parametrize("key", ["yes", "very_doubtful", "it_is_certain"])
def test_single_weighted_key_always_wins(key):
    weights = {k: 0.0 for k in KEYS}
    weights[key] = 1.0
    rng = random.Random(99)
    assert {pick(weights, rng) for _ in range(200)} == {key}


def test_zero_weight_keys_never_picked():
    weights = {k: 0.0 for k in KEYS}
    weights["yes"] = 0.5
    weights["my_reply_is_no"] = 0.5
    picks = set(sequence(weights, 3, n=500))
    assert picks <= {"yes", "my_reply_is_no"}
    assert picks == {"yes", "my_reply_is_no"}


def test_missing_keys_count_as_zero():
    rng = random.Random(5)
    assert {pick({"yes": 1.0}, rng) for _ in range(100)} == {"yes"}


def test_distribution_follows_weights():
    weights = {"yes": 0.7, "my_reply_is_no": 0.2, "outlook_good": 0.1}
    rng = random.Random(1234)
    n = 20_000
    counts = Counter(pick(weights, rng) for _ in range(n))
    assert set(counts) <= set(weights)
    for key, weight in weights.items():
        assert abs(counts[key] / n - weight) < 0.02


def test_independent_of_dict_insertion_order():
    forward = {"yes": 0.3, "my_reply_is_no": 0.3, "outlook_good": 0.2, "most_likely": 0.2}
    backward = dict(reversed(list(forward.items())))
    assert list(forward) != list(backward)
    assert sequence(forward, 42, n=100) == sequence(backward, 42, n=100)
