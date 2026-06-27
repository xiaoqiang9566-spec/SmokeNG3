from __future__ import annotations


def assert_not_empty(value: object, message: str = "value must not be empty") -> None:
    if value is None or str(value).strip() == "":
        raise AssertionError(message)


def assert_contains(container: object, member: object, message: str | None = None) -> None:
    if member not in container:
        raise AssertionError(message or f"{member!r} not found")
