"""SPEC section 9: exactly 20 answers, stable keys."""

from collections import Counter

from magic8.answers import ANSWERS, BY_KEY


def test_exactly_twenty_answers():
    assert len(ANSWERS) == 20


def test_keys_unique():
    keys = [a.key for a in ANSWERS]
    assert len(set(keys)) == len(keys)


def test_matches_answers_md_exactly(answer_rows):
    assert len(answer_rows) == 20
    assert [(a.key, a.text, a.group) for a in ANSWERS] == answer_rows


def test_group_counts():
    counts = Counter(a.group for a in ANSWERS)
    assert counts == {"affirmative": 10, "non-committal": 5, "negative": 5}


def test_by_key_has_same_keys(answer_rows):
    assert set(BY_KEY) == {key for key, _, _ in answer_rows}
    assert len(BY_KEY) == 20
    for a in ANSWERS:
        assert BY_KEY[a.key] == a
