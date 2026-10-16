"""SPEC 8: the shake."""

import io
import time

import pytest

from magic8.answers import ANSWERS
from magic8.client import BackendError
from magic8.shake import (
    FRAMES,
    PROMPT,
    WIDTH,
    answer_line,
    run_with_shake,
    use_color,
    wait_for_enter,
)


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def test_use_color_false_with_no_color():
    assert use_color({"NO_COLOR": "1"}, FakeTTY()) is False


def test_use_color_false_for_non_tty():
    assert use_color({}, io.StringIO()) is False


def test_use_color_true_for_tty_without_no_color():
    assert use_color({}, FakeTTY()) is True


def test_use_color_empty_no_color_is_ignored():
    assert use_color({"NO_COLOR": ""}, FakeTTY()) is True


def test_answer_line_plain_and_colored():
    plain = answer_line("Outlook good.", False)
    assert "\033" not in plain
    assert "Outlook good." in plain
    colored = answer_line("Outlook good.", True)
    assert "\033" in colored
    assert "Outlook good." in colored


def test_widths_fit_80_columns():
    assert WIDTH == 79
    assert FRAMES
    for frame in FRAMES:
        assert len(frame) <= 79
    assert len(PROMPT) <= 79
    longest = max((a.text for a in ANSWERS), key=len)
    assert len(answer_line(longest, False)) <= 79


def test_quick_call_still_takes_min_seconds():
    out = io.StringIO()
    start = time.perf_counter()
    result = run_with_shake(lambda: "value", out, min_seconds=0.3, frame_seconds=0.05)
    elapsed = time.perf_counter() - start
    assert result == "value"
    assert elapsed >= 0.3
    assert elapsed < 1.5
    text = out.getvalue()
    assert any(frame in text for frame in FRAMES)
    assert text.endswith("\r" + " " * WIDTH + "\r")


def test_error_reraised_immediately():
    def boom():
        raise BackendError("unreachable", "nope")

    out = io.StringIO()
    start = time.perf_counter()
    with pytest.raises(BackendError) as exc:
        run_with_shake(boom, out, min_seconds=1.0, frame_seconds=0.05)
    assert time.perf_counter() - start < 0.2
    assert exc.value.code == "unreachable"
    assert out.getvalue().endswith("\r" + " " * WIDTH + "\r")


def test_slow_call_is_not_cut_short():
    def slow():
        time.sleep(0.5)
        return 7

    out = io.StringIO()
    start = time.perf_counter()
    result = run_with_shake(slow, out, min_seconds=0.1, frame_seconds=0.05)
    elapsed = time.perf_counter() - start
    assert result == 7
    assert 0.5 <= elapsed < 0.9


def test_wait_for_enter_writes_prompt_and_reads_one_line():
    stdin = io.StringIO("\nsecond line\n")
    out = io.StringIO()
    wait_for_enter(stdin, out)
    assert out.getvalue() == PROMPT
    assert stdin.readline() == "second line\n"
