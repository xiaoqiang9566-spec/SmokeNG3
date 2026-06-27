from __future__ import annotations

import hashlib
import json
from pathlib import Path

from watch_ui_automation.actions import create_default_registry
from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.models import RunManifest
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.loader import load_scenarios
from watch_ui_automation.scenarios.models import ScenarioCase, ScenarioStep
from watch_ui_automation.scenarios.runner import run_case
from watch_ui_automation.session.runtime import WatchSession
import pytest


class FakeDevice:
    def __init__(self) -> None:
        self.current_page = "main"
        self.current_widget = "/_watch-face(c)/main"
        self.workout_state = "ready"

    def read_json(self, uri: str, body=None):
        if uri == "page://current":
            return {"Content": self.current_page}
        if uri == "widget://current":
            return {"Content": self.current_widget}
        if uri == "workout://state":
            return {"Content": self.workout_state}
        raise KeyError(uri)

    def perform_action(self, action_name: str) -> None:
        self.perform_actions([action_name])

    def perform_actions(self, actions: list[str]) -> None:
        if actions == ["swipe_up"]:
            self.current_widget = "/widgets/weather"
        elif actions == ["press_top"] and self.current_page == "main":
            self.current_page = "workout"
            self.workout_state = "running"
        elif actions == ["press_bottom_left"]:
            self.current_page = "main"
            self.current_widget = "/_watch-face(c)/main"
        elif actions == ["press_top"]:
            self.workout_state = "paused" if self.workout_state == "running" else "running"

    def open_view(self, view_name: str) -> None:
        self.current_page = view_name

    def close_view(self, view_name: str) -> None:
        self.current_page = "main"


class FakeWidget:
    def __init__(self, session: WatchSession) -> None:
        self.session = session

    def current_name(self) -> str:
        return str(self.session.read_json("widget://current").get("Content"))

    def go_back(self, case_name: str) -> None:
        self.session.record_step(case_name, "widget_back", "running")
        self.session.perform_actions(["press_bottom_left"])


class FakeWorkout:
    def __init__(self, session: WatchSession) -> None:
        self.session = session

    def state(self) -> str:
        return str(self.session.read_json("workout://state").get("Content"))

    def pause_or_resume(self, case_name: str) -> None:
        self.session.record_step(case_name, "workout_pause_resume", "running")
        self.session.perform_actions(["press_top"])

    def stop(self, case_name: str) -> None:
        self.session.record_step(case_name, "workout_stop", "running")
        self.session.perform_actions(["press_bottom_left"])


class FakeWatchface:
    def __init__(self, session: WatchSession) -> None:
        self.session = session

    def open_widget(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_widget", "running")
        self.session.perform_actions(["swipe_up"])

    def open_workout(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_workout", "running")
        self.session.perform_actions(["press_top"])


class FakeDsl:
    def __init__(self, session: WatchSession) -> None:
        self.session = session
        self.resources = {
            "current_page": "page://current",
            "current_widget": "widget://current",
            "workout_state": "workout://state",
        }
        self.watchface = FakeWatchface(session)
        self.widget = FakeWidget(session)
        self.workout = FakeWorkout(session)


def case_dir(run_dir: Path, case_name: str) -> Path:
    suffix = hashlib.sha256(case_name.encode("utf-8")).hexdigest()[:8]
    return run_dir / "cases" / f"{case_name}-{suffix}"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_yaml_smoke_runner_writes_core_artifacts(tmp_path: Path) -> None:
    writer = ArtifactWriter(tmp_path)
    run_dir = writer.start_run(
        RunManifest(
            device_serial="FAKE123",
            sds_url="fake://local",
            selected_tests=["yaml"],
            framework_version="0.1.0",
        )
    )
    session = WatchSession(
        device=FakeDevice(),
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
        settle_seconds=0,
        poll_interval_seconds=0,
    )
    dsl = FakeDsl(session)
    registry = create_default_registry()
    cases = load_scenarios(
        "tests/yaml_cases",
        suite="smoke",
        registry=registry,
    )

    for case in cases:
        ctx = ScenarioContext(
            dsl=dsl,
            session=session,
            case_id=case.id,
            baseline=case.baseline,
        )
        run_case(case, ctx, registry)

    for case_name in ["smoke_widget_yaml", "smoke_workout_yaml"]:
        output_dir = case_dir(run_dir, case_name)
        assert (output_dir / "steps.jsonl").is_file()
        assert (output_dir / "assertions.jsonl").is_file()
        assert (output_dir / "result.json").is_file()

        result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
        assert result["status"] == "passed"
        assert result["evidence_refs"] == [
            "steps.jsonl",
            "assertions.jsonl",
            "result.json",
        ]
        step_names = [entry["name"] for entry in read_jsonl(output_dir / "steps.jsonl")]
        assert "case_start" in step_names
        assert "yaml_step_start" in step_names
        assert "yaml_step_end" in step_names
        assert "case_end" in step_names
        assert read_jsonl(output_dir / "assertions.jsonl")


def test_yaml_runner_writes_artifacts_when_asserting_structured_objects(
    tmp_path: Path,
) -> None:
    writer = ArtifactWriter(tmp_path)
    run_dir = writer.start_run(
        RunManifest(
            device_serial="FAKE123",
            sds_url="fake://local",
            selected_tests=["yaml"],
            framework_version="0.1.0",
        )
    )
    session = WatchSession(
        device=FakeDevice(),
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
        settle_seconds=0,
        poll_interval_seconds=0,
    )
    dsl = FakeDsl(session)
    registry = create_default_registry()
    case = ScenarioCase(
        id="yaml_structured_assertion",
        title="YAML structured assertion",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="capture baseline widget",
                action="capture.current_widget",
                params={},
                save_as="baseline_widget",
            ),
            ScenarioStep(name="open widget", action="navigation.open_widget", params={}),
            ScenarioStep(
                name="capture widget after open",
                action="capture.current_widget",
                params={},
                save_as="widget_after_open",
            ),
            ScenarioStep(
                name="widget object changed",
                action="assert.changed",
                params={
                    "actual": "${widget_after_open}",
                    "from": "${baseline_widget}",
                },
            ),
        ],
        source_file="inline.yaml",
    )
    ctx = ScenarioContext(
        dsl=dsl,
        session=session,
        case_id=case.id,
        baseline=case.baseline,
    )

    run_case(case, ctx, registry)

    output_dir = case_dir(run_dir, "yaml_structured_assertion")
    assertion = read_jsonl(output_dir / "assertions.jsonl")[-1]
    assert assertion["actual"] == {
        "name": "/widgets/weather",
        "path": "/widgets/weather",
        "raw": {"Content": "/widgets/weather"},
    }
    assert assertion["expected"] == {
        "operator": "!=",
        "value": {
            "name": "/_watch-face(c)/main",
            "path": "/_watch-face(c)/main",
            "raw": {"Content": "/_watch-face(c)/main"},
        },
    }
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "passed"


def test_yaml_assertion_failure_writes_failure_artifacts(tmp_path: Path) -> None:
    writer = ArtifactWriter(tmp_path)
    run_dir = writer.start_run(
        RunManifest(
            device_serial="FAKE123",
            sds_url="fake://local",
            selected_tests=["yaml"],
            framework_version="0.1.0",
        )
    )
    session = WatchSession(
        device=FakeDevice(),
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
        settle_seconds=0,
        poll_interval_seconds=0,
    )
    dsl = FakeDsl(session)
    registry = create_default_registry()
    case = ScenarioCase(
        id="yaml_failure",
        title="YAML failure",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="capture page",
                action="capture.current_page",
                params={},
                save_as="page",
            ),
            ScenarioStep(
                name="assert wrong page",
                action="assert.equals",
                params={"actual": "${page.name}", "expected": "not-main"},
            ),
        ],
        source_file="inline.yaml",
    )
    ctx = ScenarioContext(
        dsl=dsl,
        session=session,
        case_id=case.id,
        baseline=case.baseline,
    )

    with pytest.raises(AssertionError):
        run_case(case, ctx, registry)

    output_dir = case_dir(run_dir, "yaml_failure")
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["error_type"] == "assertion_failure"
    assert (output_dir / "state_snapshot.json").is_file()
    assert (output_dir / "failure_summary.md").is_file()


def test_yaml_non_assertion_error_writes_device_error_result(tmp_path: Path) -> None:
    writer = ArtifactWriter(tmp_path)
    run_dir = writer.start_run(
        RunManifest(
            device_serial="FAKE123",
            sds_url="fake://local",
            selected_tests=["yaml"],
            framework_version="0.1.0",
        )
    )
    session = WatchSession(
        device=FakeDevice(),
        artifact_writer=writer,
        current_page_uri="page://current",
        baseline_actions=["press_bottom_left"],
        settle_seconds=0,
        poll_interval_seconds=0,
    )
    dsl = FakeDsl(session)
    registry = create_default_registry()
    registry.register("debug.explode", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
    case = ScenarioCase(
        id="yaml_error",
        title="YAML error",
        markers=["yaml"],
        baseline="main",
        steps=[ScenarioStep(name="explode", action="debug.explode", params={})],
        source_file="inline.yaml",
    )
    ctx = ScenarioContext(
        dsl=dsl,
        session=session,
        case_id=case.id,
        baseline=case.baseline,
    )

    with pytest.raises(Exception):
        run_case(case, ctx, registry)

    output_dir = case_dir(run_dir, "yaml_error")
    result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "error"
    assert result["error_type"] == "device_error"
