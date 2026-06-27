from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry(operation: Callable[[], T], *, attempts: int = 3, interval_seconds: float = 0.2) -> T:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return operation()
        except Exception as error:
            last_error = error
            time.sleep(interval_seconds)
    if last_error is None:
        raise RuntimeError("retry attempts must be greater than zero")
    raise last_error
