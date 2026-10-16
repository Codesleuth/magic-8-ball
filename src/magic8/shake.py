"""The "shake" step: prompt, text animation and colour."""

import threading
import time
from collections.abc import Callable, Mapping
from typing import TypeVar

T = TypeVar("T")

WIDTH = 79  # every line written is <= 79 visible chars (80-column terminal)
PROMPT = "  🎱  Shake the ball... (press Enter)"
FRAMES: tuple[str, ...] = (
    "  ~ ~ ~ the die floats up ~ ~ ~",
    "  ~ ~ the die floats up ~ ~",
    "  ~ the die tumbles in the dark ~",
    "  ~ ~ the die tumbles in the dark ~ ~",
    "  ~ ~ ~ the answer swims into view ~ ~ ~",
)
MIN_SECONDS = 1.5
FRAME_SECONDS = 0.15


def use_color(env: Mapping[str, str], stream) -> bool:
    if env.get("NO_COLOR"):
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def answer_line(text: str, color: bool) -> str:
    line = f"  ▲  {text}  ▲"
    if color:
        return f"\033[1;34m{line}\033[0m"
    return line


def wait_for_enter(stdin, out) -> None:
    out.write(PROMPT)
    out.flush()
    stdin.readline()


def run_with_shake(
    call: Callable[[], T],
    out,
    *,
    min_seconds: float = MIN_SECONDS,
    frame_seconds: float = FRAME_SECONDS,
) -> T:
    finished = threading.Event()
    box: dict[str, object] = {}

    def worker() -> None:
        try:
            box["result"] = call()
        except BaseException as exc:
            box["error"] = exc
        finally:
            finished.set()

    started = time.monotonic()
    threading.Thread(target=worker, daemon=True).start()
    try:
        i = 0
        while not (
            finished.is_set() and ("error" in box or time.monotonic() - started >= min_seconds)
        ):
            out.write("\r" + FRAMES[i % len(FRAMES)].ljust(WIDTH))
            out.flush()
            i += 1
            if finished.is_set():
                time.sleep(frame_seconds)
            else:
                finished.wait(frame_seconds)
    finally:
        out.write("\r" + " " * WIDTH + "\r")
        out.flush()
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["result"]  # type: ignore[return-value]
