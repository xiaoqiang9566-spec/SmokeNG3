import pytest

from watch_ui_automation.assertions.wait import assert_eventually, wait_until


def test_wait_until_returns_first_matching_value() -> None:
    attempts = iter(["booting", "booting", "ready"])

    value = wait_until(
        probe=lambda: next(attempts),
        matcher=lambda current: current == "ready",
        timeout_seconds=0.2,
        poll_interval_seconds=0.0,
        description="device becomes ready",
    )

    assert value == "ready"


def test_wait_until_raises_assertion_error_on_timeout() -> None:
    with pytest.raises(AssertionError, match="device becomes ready"):
        wait_until(
            probe=lambda: "booting",
            matcher=lambda current: current == "ready",
            timeout_seconds=0.01,
            poll_interval_seconds=0.0,
            description="device becomes ready",
        )


def test_assert_eventually_delegates_to_wait_until() -> None:
    attempts = iter([0, 1, 2])

    assert_eventually(
        probe=lambda: next(attempts),
        matcher=lambda current: current == 2,
        timeout_seconds=0.2,
        poll_interval_seconds=0.0,
        description="counter reaches expected value",
    )
