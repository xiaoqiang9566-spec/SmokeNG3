from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(
    probe: Callable[[], T],
    matcher: Callable[[T], bool],
    timeout_seconds: float,
    poll_interval_seconds: float,
    description: str,
) -> T:
    deadline = time.monotonic() + timeout_seconds
    last_value = probe()

    while True:
        if matcher(last_value):
            return last_value
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"wait_until timeout: {description}; last_value={last_value!r}"
            )
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)
        last_value = probe()


def assert_eventually(
    probe: Callable[[], T],
    matcher: Callable[[T], bool],
    timeout_seconds: float,
    poll_interval_seconds: float,
    description: str,
) -> None:
    wait_until(
        probe=probe,
        matcher=matcher,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        description=description,
    )
