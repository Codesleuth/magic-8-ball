"""SPEC 3 and 4: the command line."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from magic8.shake import FRAMES, PROMPT

ROOT = Path(__file__).resolve().parent.parent


def text_of(rows, key):
    return next(text for k, text, _ in rows if k == key)


def group_of(rows, key):
    return next(group for k, _, group in rows if k == key)


def test_success_prints_answer(run_cli, fake_server, good_response, answer_rows):
    fake_server.body = good_response({"outlook_good": 1.0}, choice="outlook_good")
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url)
    assert code == 0
    assert f"▲  {text_of(answer_rows, 'outlook_good')}  ▲" in out
    assert "▲  Outlook good.  ▲" in out
    assert err == ""


def test_pick_follows_weights_not_choice(run_cli, fake_server, good_response, answer_rows):
    fake_server.body = good_response({"yes": 1.0}, choice="very_doubtful")
    code, out, _ = run_cli("Will it rain?", "--backend", fake_server.url)
    assert code == 0
    assert f"▲  {text_of(answer_rows, 'yes')}  ▲" in out
    assert text_of(answer_rows, "very_doubtful") not in out


def test_json_success(run_cli, fake_server, good_response, answer_rows):
    fake_server.body = good_response(
        {"yes": 0.5, "my_reply_is_no": 0.5}, choice="yes", confidence=0.42, model="fake-1"
    )
    code, out, _ = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 0
    assert len(out.strip().splitlines()) == 1
    obj = json.loads(out)
    assert obj["key"] in {"yes", "my_reply_is_no"}
    assert obj["text"] == text_of(answer_rows, obj["key"])
    assert obj["group"] == group_of(answer_rows, obj["key"])
    assert list(obj["probabilities"]) == [k for k, _, _ in answer_rows]
    assert obj["probabilities"]["yes"] == pytest.approx(0.5)
    assert obj["model_choice"] == "yes"
    assert obj["confidence"] == 0.42
    assert obj["model"] == "fake-1"
    assert isinstance(obj["latency_ms"], int)
    assert "▲" not in out


def test_verbose_success(run_cli, fake_server, good_response, answer_rows):
    fake_server.body = good_response(
        {"yes": 0.6, "my_reply_is_no": 0.4}, choice="yes", confidence=0.42, model="fake-1"
    )
    code, out, _ = run_cli("Will it rain?", "--backend", fake_server.url, "--verbose")
    assert code == 0
    assert "confidence: 0.42" in out
    assert "latency:" in out
    assert "model: fake-1" in out
    assert "model's top choice:" in out
    assert "picked:" in out
    for line in out.splitlines():
        assert len(line) <= 79
    lines = out.splitlines()
    for key, _, _ in answer_rows:
        matching = [
            ln
            for ln in lines
            if ln.split()[-2:-1] == [key] and re.fullmatch(r"\d\.\d{3}", ln.split()[-1])
        ]
        assert len(matching) == 1, key


def test_question_from_stdin(run_cli, fake_server):
    code, _, _ = run_cli("--backend", fake_server.url, stdin_text="Will it rain?\n")
    assert code == 0
    assert len(fake_server.requests) == 1
    assert "Will it rain?" in fake_server.requests[0].json["state"]


@pytest.mark.parametrize("argv, stdin_text", [([""], ""), (["   "], ""), ([], ""), ([], "\n")])
def test_empty_question_is_usage_error(run_cli, fake_server, argv, stdin_text):
    code, out, err = run_cli(*argv, "--backend", fake_server.url, stdin_text=stdin_text)
    assert code == 1
    assert out == ""
    assert err.strip() != ""
    assert fake_server.requests == []


def test_bad_flag(run_cli, fake_server):
    code, out, err = run_cli("--nope", "--backend", fake_server.url)
    assert code == 1
    assert out == ""
    assert err.strip() != ""
    assert fake_server.requests == []


def test_two_positionals(run_cli, fake_server):
    code, out, _ = run_cli("one", "two", "--backend", fake_server.url)
    assert code == 1
    assert out == ""
    assert fake_server.requests == []


def test_version(run_cli):
    code, out, _ = run_cli("--version")
    assert code == 0
    assert out.strip() == "magic8 0.1.0"


def test_help_mentions_every_flag(run_cli):
    code, out, _ = run_cli("--help")
    assert code == 0
    for flag in (
        "--no-shake",
        "--backend",
        "--model",
        "--json",
        "--verbose",
        "--version",
        "--help",
    ):
        assert flag in out


def test_non_tty_has_no_shake_output(run_cli, fake_server):
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url)
    assert code == 0
    for stream in (out, err):
        assert PROMPT not in stream
        assert "Shake the ball" not in stream
        assert "\r" not in stream
        for frame in FRAMES:
            assert frame.strip() not in stream


def test_no_shake_flag_accepted(run_cli, fake_server):
    code, out, _ = run_cli("Will it rain?", "--no-shake", "--backend", fake_server.url)
    assert code == 0
    assert "▲" in out


def _subprocess_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("MAGIC8_")}
    src = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (src, env.get("PYTHONPATH")) if p)
    return env


def test_subprocess_backend_error_exit_code(closed_port_url, tmp_path):
    url = closed_port_url()
    proc = subprocess.run(
        [sys.executable, "-m", "magic8", "--backend", url, "q"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=tmp_path,
        env=_subprocess_env(),
        timeout=30,
    )
    assert proc.returncode == 2
    assert f"Can't reach the decision model at {url}." in proc.stderr


def test_subprocess_usage_error_exit_code(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "magic8", "--nope"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=tmp_path,
        env=_subprocess_env(),
        timeout=30,
    )
    assert proc.returncode == 1
