import itertools
import os
import shutil
import sys
import threading
import time
from contextlib import contextmanager

FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\r\033[2K"
DISABLE_WRAP = "\033[?7l"
ENABLE_WRAP = "\033[?7h"


def _terminal_columns() -> int:
    try:
        return os.get_terminal_size(sys.stderr.fileno()).columns
    except (AttributeError, OSError, ValueError):
        return shutil.get_terminal_size((80, 20)).columns


def _fit(frame: str, text: str, elapsed: float, cols: int) -> str:
    suffix = f" {elapsed:.0f}s"
    prefix = f"{frame} "
    max_len = max(10, cols - 1)
    if len(prefix) + len(text) + len(suffix) <= max_len:
        return f"{prefix}{text}{suffix}"
    avail = max_len - len(prefix) - len(suffix)
    if avail > 3:
        return f"{prefix}{text[:avail - 1]}…{suffix}"
    return f"{prefix}{text[:max(0, avail)]}{suffix}"


@contextmanager
def spin(text: str):
    """Render a spinner on stderr while the body runs. No-op when stderr
    isn't a terminal (hooks, daemon, pipes, logs)."""
    if not sys.stderr.isatty():
        yield
        return

    stop = threading.Event()
    start = time.monotonic()

    def _spin():
        for frame in itertools.cycle(FRAMES):
            if stop.is_set():
                return
            elapsed = time.monotonic() - start
            cols = _terminal_columns()
            line = _fit(frame, text, elapsed, cols)
            sys.stderr.write(f"{CLEAR_LINE}{line}")
            sys.stderr.flush()
            time.sleep(0.08)

    thread = threading.Thread(target=_spin, daemon=True)
    sys.stderr.write(HIDE_CURSOR + DISABLE_WRAP)
    sys.stderr.flush()
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()
        sys.stderr.write(CLEAR_LINE + SHOW_CURSOR + ENABLE_WRAP)
        sys.stderr.flush()

