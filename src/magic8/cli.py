"""Command-line interface."""

import argparse
import json
import os
import random
import sys
from collections.abc import Mapping
from pathlib import Path

import httpx

from magic8 import __version__
from magic8.answers import ANSWERS, BY_KEY
from magic8.client import BackendError, ask
from magic8.config import ConfigError, load_config
from magic8.sampling import pick
from magic8.shake import answer_line, run_with_shake, use_color, wait_for_enter


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that never exits with 2 and writes to injected streams."""

    out = sys.stdout

    def _print_message(self, message, file=None):
        if not message:
            return
        if file is None or file is sys.stdout:
            file = self.out
        file.write(message)

    def error(self, message):
        self.print_usage(self.err)
        self.err.write(f"{self.prog}: error: {message}\n")
        raise _UsageError(message)


def _build_parser(out, err) -> _Parser:
    parser = _Parser(
        prog="magic8",
        description="Ask the Magic 8 Ball a yes/no question.",
    )
    parser.out = out
    parser.err = err
    parser.add_argument("question", nargs="?", help="the yes/no question (prompted if missing)")
    parser.add_argument("--no-shake", action="store_true", help="skip the shake step and animation")
    parser.add_argument("--backend", metavar="URL", help="override MAGIC8_BASE_URL")
    parser.add_argument("--model", metavar="NAME", help="override MAGIC8_MODEL")
    parser.add_argument(
        "--json", action="store_true", help="print the answer and probabilities as JSON"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="show the model, confidence and latency"
    )
    parser.add_argument("--version", action="version", version=f"magic8 {__version__}")
    return parser


def _isatty(stream) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def main(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    stdin=None,
    stdout=None,
    stderr=None,
    cwd: Path | None = None,
    rng: random.Random | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    cwd = Path.cwd() if cwd is None else cwd
    rng = random.Random() if rng is None else rng
    try:
        return _run(argv, env, stdin, stdout, stderr, cwd, rng, transport)
    except KeyboardInterrupt:
        stderr.write("\n")
        return 130


def _run(argv, env, stdin, stdout, stderr, cwd, rng, transport) -> int:
    parser = _build_parser(stdout, stderr)
    try:
        args = parser.parse_args(argv)
    except _UsageError:
        return 1
    except SystemExit as exc:  # --help and --version
        code = exc.code
        return code if isinstance(code, int) else 0

    try:
        config = load_config(env, cwd / ".env", base_url=args.backend, model=args.model)
    except ConfigError as exc:
        stderr.write(f"{exc}\n")
        return 1

    question = args.question
    if question is None:
        if _isatty(stdin):
            stderr.write("  Ask a yes/no question: ")
            stderr.flush()
        question = stdin.readline()
    question = question.strip()
    if not question:
        stderr.write("magic8: error: ask a yes/no question.\n")
        return 1

    shake = not args.no_shake and not args.json and _isatty(stdin) and _isatty(stdout)
    try:
        if shake:
            wait_for_enter(stdin, stdout)
            result = run_with_shake(lambda: ask(question, config, transport=transport), stdout)
        else:
            result = ask(question, config, transport=transport)
    except BackendError as exc:
        stderr.write(exc.message + "\n")
        if args.verbose and exc.detail:
            stderr.write(f"Server said: {exc.detail}\n")
        if args.json:
            stdout.write(json.dumps({"error": exc.code, "message": exc.message}) + "\n")
        return 2

    key = pick(result.probabilities, rng)
    answer = BY_KEY[key]

    if args.json:
        payload = {
            "key": answer.key,
            "text": answer.text,
            "group": answer.group,
            "probabilities": {a.key: result.probabilities[a.key] for a in ANSWERS},
            "model_choice": result.model_choice,
            "confidence": result.confidence,
            "model": result.model,
            "latency_ms": result.latency_ms,
        }
        stdout.write(json.dumps(payload) + "\n")
        return 0

    stdout.write(answer_line(answer.text, use_color(env, stdout)) + "\n")
    if args.verbose:
        confidence = "(not given)" if result.confidence is None else f"{result.confidence:.2f}"
        lines = [
            f"  model: {result.model or '(not given)'}",
            f"  confidence: {confidence}",
            f"  latency: {result.latency_ms} ms",
            f"  model's top choice: {result.model_choice or '(not given)'}",
            f"  picked: {key}",
            "  probabilities:",
        ]
        for a in ANSWERS:
            mark = "*" if a.key == key else " "
            lines.append(f"    {mark} {a.key:<26} {result.probabilities[a.key]:.3f}")
        stdout.write("\n".join(lines) + "\n")
    return 0


def run() -> None:
    sys.exit(main())
