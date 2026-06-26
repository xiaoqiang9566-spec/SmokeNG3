from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Sequence
from typing import Any, Iterator

from watch_ui_automation.assertions.wait import wait_until
from watch_ui_automation.models import CaseResult

_SUCCESS_EVIDENCE_REFS = ["steps.jsonl", "assertions.jsonl", "result.json"]
_FAILURE_EVIDENCE_REFS = [
    "steps.jsonl",
    "assertions.jsonl",
    "state_snapshot.json",
    "failure_summary.md",
    "result.json",
]


class WatchSession:
    def __init__(
        self,
        device: Any,
        artifact_writer: Any,
        current_page_uri: str,
        baseline_actions: Sequence[str],
        settle_seconds: float = 1.0,
        poll_interval_seconds: float = 0.0,
    ) -> None:
        self.device = device
        self.artifact_writer = artifact_writer
        self.current_page_uri = current_page_uri
        self.baseline_actions = list(baseline_actions)
        self.settle_seconds = settle_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def read_json(self, uri: str, body: Any | None = None) -> Any:
        if body is None:
            return self.device.read_json(uri)
        return self.device.read_json(uri, body=body)

    def perform_action(self, action_name: str) -> None:
        self.device.perform_action(action_name)

    def perform_actions(self, actions: Sequence[str]) -> None:
        self.device.perform_actions(list(actions))

    def open_view(self, view_name: str) -> None:
        self.device.open_view(view_name)

    def close_view(self, view_name: str) -> None:
        self.device.close_view(view_name)

    def record_step(
        self, case_name: str, name: str, status: str, **extra: object
    ) -> None:
        self.artifact_writer.write_step(
            case_name,
            {"name": name, "status": status, **extra},
        )

    def record_assertion(
        self, case_name: str, name: str, status: str, **extra: object
    ) -> None:
        self.artifact_writer.write_assertion(
            case_name,
            {"name": name, "status": status, **extra},
        )

    def ensure_baseline(self, case_name: str, expected_page: str) -> None:
        current = self.read_json(self.current_page_uri).get("Content")
        if current == expected_page:
            return

        self.perform_actions(self.baseline_actions)
        self.record_step(
            case_name,
            "baseline_recovery",
            "performed",
            actual=current,
            expected=expected_page,
        )

    def wait_for_expected_page(self, expected_page: str) -> str:
        try:
            return str(
                wait_until(
                    probe=lambda: self.read_json(self.current_page_uri).get('Content'),
                    matcher=lambda current: current == expected_page,
                    timeout_seconds=self.settle_seconds,
                    poll_interval_seconds=self.poll_interval_seconds,
                    description='page reaches expected baseline',
                )
            )
        except AssertionError:
            return str(self.read_json(self.current_page_uri).get('Content'))

    def capture_failure_state(
        self, case_name: str, error_type: str, error: BaseException
    ) -> None:
        current_page: object
        try:
            current_page = self.read_json(self.current_page_uri)
        except Exception as snapshot_error:
            current_page = {
                "snapshot_error": str(snapshot_error),
                "snapshot_error_type": type(snapshot_error).__name__,
            }
        self.artifact_writer.write_snapshot(
            case_name,
            {
                "error_type": error_type,
                "error": str(error),
                "current_page": current_page,
            },
        )
        self.artifact_writer.write_failure_summary(
            case_name,
            "\n".join(
                [
                    f"# Failure Summary: {case_name}",
                    "",
                    f"- error_type: `{error_type}`",
                    f"- error: `{error}`",
                    f"- current_page: `{current_page}`",
                ]
            ),
        )

    def finalize_case(self, result: CaseResult) -> None:
        self.artifact_writer.write_case_result(result)

    def assert_condition(
        self,
        case_name: str,
        name: str,
        condition: bool,
        *,
        actual: object,
        expected: object,
        detail: str | None = None,
    ) -> None:
        self.record_assertion(
            case_name,
            name,
            "passed" if condition else "failed",
            actual=actual,
            expected=expected,
            detail=detail,
        )
        if condition:
            return

        message = detail or f"{name} failed: expected={expected!r}, actual={actual!r}"
        raise AssertionError(message)

    @contextmanager
    def case(self, case_name: str, expected_page: str = "Watchface") -> Iterator[None]:
        self.record_step(
            case_name,
            "case_start",
            "running",
            expected_page=expected_page,
        )

        try:
            current_page = self.read_json(self.current_page_uri).get("Content")
            if current_page != expected_page:
                self.ensure_baseline(case_name, expected_page)
                recovered_page = self.wait_for_expected_page(expected_page)
                self.assert_condition(
                    case_name,
                    "baseline_ready",
                    recovered_page == expected_page,
                    actual=recovered_page,
                    expected=expected_page,
                    detail="baseline recovery did not return to the expected page",
                )

            yield
        except AssertionError as error:
            self.record_step(
                case_name,
                "case_end",
                "failed",
                error_type="assertion_failure",
            )
            self.capture_failure_state(case_name, "assertion_failure", error)
            self.finalize_case(
                CaseResult(
                    case_name=case_name,
                    status="failed",
                    error_type="assertion_failure",
                    evidence_refs=list(_FAILURE_EVIDENCE_REFS),
                )
            )
            raise
        except Exception as error:
            self.record_step(
                case_name,
                "case_end",
                "error",
                error_type="device_error",
            )
            self.capture_failure_state(case_name, "device_error", error)
            self.finalize_case(
                CaseResult(
                    case_name=case_name,
                    status="error",
                    error_type="device_error",
                    evidence_refs=list(_FAILURE_EVIDENCE_REFS),
                )
            )
            raise
        else:
            self.record_step(case_name, "case_end", "passed")
            self.finalize_case(
                CaseResult(
                    case_name=case_name,
                    status="passed",
                    error_type=None,
                    evidence_refs=list(_SUCCESS_EVIDENCE_REFS),
                )
            )
