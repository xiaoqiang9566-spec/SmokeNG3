import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

import watch_ui_automation.artifacts.writer as writer_module
from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.models import CaseResult, RunManifest


class _FrozenDateTime:
    @staticmethod
    def utcnow() -> datetime:
        return datetime(2026, 6, 24, 10, 0, 0)


def test_artifact_writer_normalizes_unsafe_directory_names_but_preserves_original_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)

    writer = ArtifactWriter(tmp_path)
    manifest = RunManifest(
        device_serial="device::A/01",
        sds_url="ws://localhost:65534",
        selected_tests=["device", "smoke"],
        framework_version="0.1.0",
    )
    case_result = CaseResult(
        case_name="suite::case/name:retry",
        status="failed",
        error_type="assertion_failure",
        evidence_refs=[],
    )

    run_dir = writer.start_run(manifest)
    writer.write_case_result(case_result)

    assert run_dir == tmp_path / "run-20260624-100000-device-A-01"
    assert json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8")) == {
        "device_serial": "device::A/01",
        "sds_url": "ws://localhost:65534",
        "selected_tests": ["device", "smoke"],
        "framework_version": "0.1.0",
    }

    case_dir = run_dir / "cases" / (
        "suite-case-name-retry-"
        + hashlib.sha256("suite::case/name:retry".encode("utf-8")).hexdigest()[:8]
    )
    assert case_dir.is_dir()
    assert json.loads((case_dir / "result.json").read_text(encoding="utf-8")) == {
        "case_name": "suite::case/name:retry",
        "status": "failed",
        "error_type": "assertion_failure",
        "evidence_refs": [],
    }


def test_artifact_writer_defaults_to_repo_artifacts_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)

    writer = ArtifactWriter()
    monkeypatch.chdir(tmp_path)

    run_dir = writer.start_run(
        RunManifest(
            device_serial="TEST123",
            sds_url="ws://localhost:65534",
            selected_tests=["device", "smoke"],
            framework_version="0.1.0",
        )
    )

    assert writer.root_dir == Path("artifacts")
    assert run_dir == tmp_path / "artifacts" / "run-20260624-100000-TEST123"


def test_artifact_writer_uses_stable_unique_case_directories_for_normalization_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)
    writer = ArtifactWriter(tmp_path)
    writer.start_run(
        RunManifest(
            device_serial="TEST123",
            sds_url="ws://localhost:65534",
            selected_tests=["device", "smoke"],
            framework_version="0.1.0",
        )
    )

    first_case_name = "suite::case/name"
    second_case_name = "suite??case//name"

    writer.write_case_result(
        CaseResult(
            case_name=first_case_name,
            status="failed",
            error_type="assertion_failure",
            evidence_refs=[],
        )
    )
    writer.write_case_result(
        CaseResult(
            case_name=second_case_name,
            status="error",
            error_type="device_error",
            evidence_refs=[],
        )
    )

    case_dirs = sorted((writer.run_dir / "cases").iterdir())
    expected_dir_names = {
        "suite-case-name-" + hashlib.sha256(first_case_name.encode("utf-8")).hexdigest()[:8],
        "suite-case-name-" + hashlib.sha256(second_case_name.encode("utf-8")).hexdigest()[:8],
    }

    assert len(case_dirs) == 2
    assert case_dirs[0].name != case_dirs[1].name
    assert {case_dir.name for case_dir in case_dirs} == expected_dir_names
    assert json.loads((case_dirs[0] / "result.json").read_text(encoding="utf-8"))["case_name"] in {
        first_case_name,
        second_case_name,
    }
    assert json.loads((case_dirs[1] / "result.json").read_text(encoding="utf-8"))["case_name"] in {
        first_case_name,
        second_case_name,
    }
    assert {
        json.loads((case_dir / "result.json").read_text(encoding="utf-8"))["case_name"]
        for case_dir in case_dirs
    } == {first_case_name, second_case_name}


@pytest.mark.parametrize("status", ["skipped", "running"])
def test_case_result_rejects_unknown_status(status: str) -> None:
    with pytest.raises(ValueError, match="unsupported case status"):
        CaseResult(
            case_name="alarm_case",
            status=status,
            error_type=None,
            evidence_refs=[],
        )


@pytest.mark.parametrize("error_type", ["bad:value", "with/slash"])
def test_case_result_rejects_unknown_error_type(error_type: str) -> None:
    with pytest.raises(ValueError, match="unsupported error_type"):
        CaseResult(
            case_name="alarm_case",
            status="failed",
            error_type=error_type,
            evidence_refs=[],
        )


@pytest.mark.parametrize("status", ["failed", "error"])
def test_case_result_requires_error_type_for_non_passing_status(status: str) -> None:
    with pytest.raises(ValueError, match="requires error_type"):
        CaseResult(
            case_name="alarm_case",
            status=status,
            error_type=None,
            evidence_refs=[],
        )


def test_case_result_rejects_error_type_for_passed_status() -> None:
    with pytest.raises(ValueError, match="passed cases must not define error_type"):
        CaseResult(
            case_name="alarm_case",
            status="passed",
            error_type="assertion_failure",
            evidence_refs=[],
        )


def test_artifact_writer_rejects_non_mapping_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)
    writer = ArtifactWriter(tmp_path)
    writer.start_run(
        RunManifest(
            device_serial="TEST123",
            sds_url="ws://localhost:65534",
            selected_tests=["device", "smoke"],
            framework_version="0.1.0",
        )
    )

    with pytest.raises(TypeError, match="payload must be a mapping"):
        writer.write_step("test_case", ["not", "a", "mapping"])  # type: ignore[arg-type]


def test_artifact_writer_rejects_non_json_serializable_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)
    writer = ArtifactWriter(tmp_path)
    writer.start_run(
        RunManifest(
            device_serial="TEST123",
            sds_url="ws://localhost:65534",
            selected_tests=["device", "smoke"],
            framework_version="0.1.0",
        )
    )

    with pytest.raises(TypeError, match="payload must be JSON serializable"):
        writer.write_snapshot("test_case", {"bad": object()})


def test_artifact_writer_persists_plan_manifest_and_case_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)

    writer = ArtifactWriter(tmp_path)
    manifest = RunManifest(
        device_serial="TEST123",
        sds_url="ws://localhost:65534",
        selected_tests=["device", "smoke"],
        framework_version="0.1.0",
    )
    case_result = CaseResult(
        case_name="test_case",
        status="failed",
        error_type="assertion_failure",
        evidence_refs=["steps.jsonl:1", "state_snapshot.json"],
    )

    run_dir = writer.start_run(manifest)
    writer.write_step(
        "test_case",
        {
            "timestamp": "2026-06-24T10:01:05Z",
            "name": "open widget",
            "status": "passed",
        },
    )
    writer.write_transport(
        "test_case",
        {
            "timestamp": "2026-06-24T10:01:06Z",
            "request": {"uri": "suunto://watch/page"},
            "response": {"page": "Training"},
        },
    )
    writer.write_assertion(
        "test_case",
        {
            "timestamp": "2026-06-24T10:01:07Z",
            "name": "widget title",
            "status": "failed",
        },
    )
    writer.write_snapshot(
        "test_case",
        {"page": "Training", "widget": "Timer", "focused_item": "Start"},
    )
    writer.write_case_result(case_result)
    writer.write_failure_summary(
        "test_case",
        "# Failure Summary\n\nExpected widget title to match\n",
    )

    assert run_dir == tmp_path / "run-20260624-100000-TEST123"
    assert (run_dir / "cases").is_dir()
    assert json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8")) == {
        "device_serial": "TEST123",
        "sds_url": "ws://localhost:65534",
        "selected_tests": ["device", "smoke"],
        "framework_version": "0.1.0",
    }

    case_dir = run_dir / "cases" / (
        "test_case-" + hashlib.sha256("test_case".encode("utf-8")).hexdigest()[:8]
    )
    assert json.loads((case_dir / "result.json").read_text(encoding="utf-8")) == {
        "case_name": "test_case",
        "status": "failed",
        "error_type": "assertion_failure",
        "evidence_refs": ["steps.jsonl:1", "state_snapshot.json"],
    }
    assert json.loads((case_dir / "state_snapshot.json").read_text(encoding="utf-8")) == {
        "page": "Training",
        "widget": "Timer",
        "focused_item": "Start",
    }
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
            "status": "failed",
        }
    ]


def test_start_run_rejects_existing_plan_run_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(writer_module, "datetime", _FrozenDateTime, raising=False)
    manifest = RunManifest(
        device_serial="TEST123",
        sds_url="ws://localhost:65534",
        selected_tests=["device", "smoke"],
        framework_version="0.1.0",
    )
    existing_run_dir = tmp_path / "run-20260624-100000-TEST123"
    existing_run_dir.mkdir(parents=True)

    writer = ArtifactWriter(tmp_path)

    with pytest.raises(FileExistsError):
        writer.start_run(manifest)


def test_plan_models_to_dict_match_expected_fields() -> None:
    manifest = RunManifest(
        device_serial="TEST456",
        sds_url="ws://localhost:65534",
        selected_tests=["device", "regression"],
        framework_version="0.1.0",
    )
    case_result = CaseResult(
        case_name="alarm_case",
        status="passed",
        error_type=None,
        evidence_refs=[],
    )

    assert manifest.to_dict() == {
        "device_serial": "TEST456",
        "sds_url": "ws://localhost:65534",
        "selected_tests": ["device", "regression"],
        "framework_version": "0.1.0",
    }
    assert case_result.to_dict() == {
        "case_name": "alarm_case",
        "status": "passed",
        "error_type": None,
        "evidence_refs": [],
    }
