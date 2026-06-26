from __future__ import annotations

from pathlib import Path

import pytest

from watch_ui_automation.models import CaseResult
from watch_ui_automation.session.runtime import WatchSession


class FakeDevice:
    def __init__(self) -> None:
        self.actions: list[str] = []
        self.view_commands: list[tuple[str, str]] = []
        self.payloads = {
            "page://current": {"Content": "Watchface"},
            "widget://current": {"Content": "Weather"},
        }

    def read_json(self, uri: str, body=None):
        return self.payloads[uri]

    def perform_action(self, action_name: str) -> None:
        self.actions.append(action_name)

    def perform_actions(self, action_names: list[str]) -> None:
        self.actions.extend(action_names)

    def open_view(self, view_name: str) -> None:
        self.view_commands.append(("open", view_name))

    def close_view(self, view_name: str) -> None:
        self.view_commands.append(("close", view_name))


class FakeArtifactWriter:
    def __init__(self) -> None:
        self.steps = []
        self.assertions = []
        self.snapshots = []
        self.failures = []
        self.results = []

    def write_step(self, case_name: str, payload: dict[str, object]) -> Path:
        self.steps.append((case_name, payload))
        return Path("steps.jsonl")

    def write_assertion(self, case_name: str, payload: dict[str, object]) -> Path:
        self.assertions.append((case_name, payload))
        return Path("assertions.jsonl")

    def write_snapshot(self, case_name: str, payload: dict[str, object]) -> Path:
        self.snapshots.append((case_name, payload))
        return Path("state_snapshot.json")

    def write_failure_summary(self, case_name: str, markdown: str) -> Path:
        self.failures.append((case_name, markdown))
        return Path("failure_summary.md")

    def write_case_result(self, result: CaseResult) -> Path:
        self.results.append(result)
        return Path("result.json")


def test_watch_session_proxies_device_calls_and_records_outputs() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    assert session.read_json("page://current") == {"Content": "Watchface"}

    session.perform_action("press_middle")
    session.perform_actions(["swipe_left", "press_bottom_left"])
    session.open_view("s-main")
    session.close_view("s-main")
    session.record_step("case_a", "open_settings", "running", detail="start")
    session.record_assertion("case_a", "on_watchface", "passed", actual="Watchface")
    session.finalize_case(
        CaseResult(
            case_name="case_a",
            status="passed",
            error_type=None,
            evidence_refs=["steps.jsonl"],
        )
    )

    assert device.actions == ["press_middle", "swipe_left", "press_bottom_left"]
    assert device.view_commands == [("open", "s-main"), ("close", "s-main")]
    assert writer.steps[0][0] == "case_a"
    assert writer.assertions[0][0] == "case_a"
    assert writer.results[0].case_name == "case_a"


def test_watch_session_ensure_baseline_executes_recovery_actions_when_needed() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    device.payloads["page://current"] = {"Content": "Settings"}
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left", "press_bottom_left"],
    )

    session.ensure_baseline("case_b", expected_page="Watchface")

    assert device.actions == ["press_bottom_left", "press_bottom_left"]
    assert writer.steps[-1][1]["name"] == "baseline_recovery"


def test_watch_session_capture_failure_state_writes_snapshot_and_summary() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    session.capture_failure_state(
        "case_c",
        error_type="assertion_failure",
        error=AssertionError("page mismatch"),
    )

    assert writer.snapshots[0][0] == "case_c"
    assert "page mismatch" in writer.failures[0][1]


def test_watch_session_case_finalizes_success_result() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    with session.case("case_success"):
        session.record_step("case_success", "inside_case", "running")

    assert writer.results[0].case_name == "case_success"
    assert writer.results[0].status == "passed"
    assert writer.steps[0][1]["name"] == "case_start"
    assert writer.steps[-1][1]["name"] == "case_end"


def test_watch_session_case_captures_assertion_failure_and_finalizes_result() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    with pytest.raises(AssertionError, match="expected failure"):
        with session.case("case_failure"):
            raise AssertionError("expected failure")

    assert writer.snapshots[0][0] == "case_failure"
    assert writer.results[0].case_name == "case_failure"
    assert writer.results[0].status == "failed"
    assert writer.results[0].error_type == "assertion_failure"


def test_watch_session_case_recovers_baseline_before_running_body() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    device.payloads["page://current"] = {"Content": "Settings"}
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    def recover_to_watchface(actions: list[str]) -> None:
        device.actions.extend(actions)
        device.payloads["page://current"] = {"Content": "Watchface"}

    device.perform_actions = recover_to_watchface

    with session.case("case_recover"):
        session.record_step("case_recover", "inside_case", "running")

    assert device.actions == ["press_bottom_left"]
    assert writer.assertions[0][1]["name"] == "baseline_ready"
    assert writer.assertions[0][1]["status"] == "passed"
    assert writer.results[0].status == "passed"


def test_watch_session_case_fails_when_baseline_recovery_does_not_return_expected_page() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    device.payloads["page://current"] = {"Content": "Settings"}
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    with pytest.raises(AssertionError, match="baseline recovery did not return"):
        with session.case("case_bad_baseline"):
            session.record_step("case_bad_baseline", "inside_case", "running")

    assert writer.assertions[0][1]["name"] == "baseline_ready"
    assert writer.assertions[0][1]["status"] == "failed"
    assert writer.results[0].status == "failed"
    assert writer.results[0].error_type == "assertion_failure"


def test_watch_session_case_waits_for_baseline_to_reach_expected_page() -> None:
    class DelayedBaselineDevice(FakeDevice):
        def __init__(self) -> None:
            super().__init__()
            self.read_count = 0
            self.payloads["page://current"] = {"Content": "c-lowp"}

        def read_json(self, uri: str):
            if uri == "page://current":
                self.read_count += 1
                if self.read_count >= 4:
                    return {"Content": "main"}
            return super().read_json(uri)

    device = DelayedBaselineDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_middle"],
    )

    with session.case("case_wait_baseline", expected_page="main"):
        session.record_step("case_wait_baseline", "inside_case", "running")

    assert device.actions == ["press_middle"]
    assert writer.assertions[0][1]["name"] == "baseline_ready"
    assert writer.assertions[0][1]["status"] == "passed"
    assert writer.results[0].status == "passed"


def test_watch_session_case_captures_non_assertion_exceptions_as_device_error() -> None:
    device = FakeDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    with pytest.raises(RuntimeError, match="device disconnected"):
        with session.case("case_device_error"):
            raise RuntimeError("device disconnected")

    assert writer.snapshots[0][0] == "case_device_error"
    assert writer.results[0].status == "error"
    assert writer.results[0].error_type == "device_error"


def test_watch_session_capture_failure_state_survives_snapshot_read_errors() -> None:
    class BrokenDevice(FakeDevice):
        def read_json(self, uri: str):
            raise RuntimeError(f"unreadable resource: {uri}")

    device = BrokenDevice()
    writer = FakeArtifactWriter()
    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
    )

    session.capture_failure_state(
        "case_snapshot_error",
        error_type="device_error",
        error=RuntimeError("original failure"),
    )

    snapshot_payload = writer.snapshots[0][1]
    assert snapshot_payload["error_type"] == "device_error"
    assert snapshot_payload["error"] == "original failure"
    assert snapshot_payload["current_page"]["snapshot_error_type"] == "RuntimeError"
    assert "unreadable resource" in snapshot_payload["current_page"]["snapshot_error"]
