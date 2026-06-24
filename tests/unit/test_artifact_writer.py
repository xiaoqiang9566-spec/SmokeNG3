import json
from pathlib import Path

from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.models import CaseResult, RunManifest


def test_run_manifest_and_case_artifacts_are_written(tmp_path: Path) -> None:
    writer = ArtifactWriter(tmp_path)
    manifest = RunManifest(
        run_id="run-001",
        suite_name="smoke",
        device_serial="TEST123",
        started_at="2026-06-24T10:00:00Z",
    )
    case_result = CaseResult(
        case_id="case-001",
        status="failed",
        started_at="2026-06-24T10:01:00Z",
        finished_at="2026-06-24T10:02:00Z",
        error_message="Expected widget title to match",
    )

    run_dir = writer.start_run(manifest)
    writer.write_step(
        "case-001",
        {
            "timestamp": "2026-06-24T10:01:05Z",
            "name": "open widget",
            "status": "passed",
        },
    )
    writer.write_transport(
        "case-001",
        {
            "timestamp": "2026-06-24T10:01:06Z",
            "request": {"uri": "suunto://watch/page"},
            "response": {"page": "Training"},
        },
    )
    writer.write_assertion(
        "case-001",
        {
            "timestamp": "2026-06-24T10:01:07Z",
            "name": "widget title",
            "passed": False,
        },
    )
    writer.write_snapshot(
        "case-001",
        {"page": "Training", "widget": "Timer", "focused_item": "Start"},
    )
    writer.write_case_result(case_result)
    writer.write_failure_summary(
        "case-001",
        "# Failure Summary\n\nExpected widget title to match\n",
    )

    assert run_dir == tmp_path / "run-001"
    assert json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8")) == {
        "run_id": "run-001",
        "suite_name": "smoke",
        "device_serial": "TEST123",
        "started_at": "2026-06-24T10:00:00Z",
    }

    case_dir = run_dir / "cases" / "case-001"
    assert json.loads((case_dir / "result.json").read_text(encoding="utf-8")) == {
        "case_id": "case-001",
        "status": "failed",
        "started_at": "2026-06-24T10:01:00Z",
        "finished_at": "2026-06-24T10:02:00Z",
        "error_message": "Expected widget title to match",
    }
    assert (case_dir / "state_snapshot.json").read_text(encoding="utf-8") == json.dumps(
        {"page": "Training", "widget": "Timer", "focused_item": "Start"},
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    assert (case_dir / "failure_summary.md").read_text(encoding="utf-8").startswith(
        "# Failure Summary"
    )

    step_lines = (case_dir / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    transport_lines = (
        case_dir / "transport.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assertion_lines = (
        case_dir / "assertions.jsonl"
    ).read_text(encoding="utf-8").splitlines()

    assert [json.loads(line) for line in step_lines] == [
        {
            "timestamp": "2026-06-24T10:01:05Z",
            "name": "open widget",
            "status": "passed",
        }
    ]
    assert [json.loads(line) for line in transport_lines] == [
        {
            "timestamp": "2026-06-24T10:01:06Z",
            "request": {"uri": "suunto://watch/page"},
            "response": {"page": "Training"},
        }
    ]
    assert [json.loads(line) for line in assertion_lines] == [
        {
            "timestamp": "2026-06-24T10:01:07Z",
            "name": "widget title",
            "passed": False,
        }
    ]


def test_model_to_dict_preserves_optional_fields() -> None:
    manifest = RunManifest(
        run_id="run-002",
        suite_name="regression",
        device_serial="TEST456",
        started_at="2026-06-24T11:00:00Z",
    )
    case_result = CaseResult(
        case_id="case-002",
        status="passed",
        started_at="2026-06-24T11:01:00Z",
        finished_at="2026-06-24T11:01:30Z",
    )

    assert manifest.to_dict() == {
        "run_id": "run-002",
        "suite_name": "regression",
        "device_serial": "TEST456",
        "started_at": "2026-06-24T11:00:00Z",
    }
    assert case_result.to_dict() == {
        "case_id": "case-002",
        "status": "passed",
        "started_at": "2026-06-24T11:01:00Z",
        "finished_at": "2026-06-24T11:01:30Z",
        "error_message": None,
    }
