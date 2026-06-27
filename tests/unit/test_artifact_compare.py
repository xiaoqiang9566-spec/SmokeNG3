from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from watch_ui_automation.artifacts.compare import (
    _parse_case_map,
    compare_case_artifacts,
    compare_run_artifacts,
    suggest_case_map,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_ROOT) if not existing else f"{SRC_ROOT}{os.pathsep}{existing}"
    )
    return env


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def make_case_dir(root: Path, case_name: str, *, status: str = "passed") -> Path:
    case_dir = root / case_name
    write_json(
        case_dir / "result.json",
        {
            "case_name": case_name,
            "status": status,
            "error_type": None if status == "passed" else "assertion_failure",
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_jsonl(
        case_dir / "steps.jsonl",
        [{"name": "case_start", "status": "running"}, {"name": "case_end", "status": status}],
    )
    write_jsonl(
        case_dir / "assertions.jsonl",
        [{"name": "returned_to_watchface", "status": "passed"}],
    )
    return case_dir


def write_run_manifest(
    run_dir: Path,
    *,
    selected_tests: list[str] | None = None,
) -> None:
    write_json(
        run_dir / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": selected_tests or ["device", "smoke"],
            "framework_version": "test",
        },
    )


def make_run_case_dir(root: Path, case_name: str, *, status: str = "passed") -> Path:
    safe_name = case_name.replace("_", "-")
    case_dir = root / "cases" / f"{safe_name}-abcdef12"
    return make_case_dir(case_dir.parent, case_dir.name, status=status)


def test_compare_case_artifacts_accepts_equivalent_core_outputs(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is True
    assert result.differences == []
    assert result.python_status == "passed"
    assert result.yaml_status == "passed"


def test_compare_case_artifacts_reports_missing_yaml_assertions(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    (yaml_case / "assertions.jsonl").unlink()

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml missing assertions.jsonl" in result.differences


def test_compare_case_artifacts_requires_jsonl_row_status(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_jsonl(yaml_case / "steps.jsonl", [{"name": "case_start"}])

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml steps.jsonl:1 status must be a string" in result.differences


def test_compare_case_artifacts_requires_jsonl_row_name(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_jsonl(yaml_case / "assertions.jsonl", [{"name": 123, "status": "passed"}])

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml assertions.jsonl:1 name must be a string" in result.differences


def test_compare_case_artifacts_rejects_unsupported_step_status(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_jsonl(yaml_case / "steps.jsonl", [{"name": "case_start", "status": "unknown"}])

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml steps.jsonl:1 unsupported status unknown" in result.differences


def test_compare_case_artifacts_rejects_unsupported_assertion_status(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_jsonl(
        yaml_case / "assertions.jsonl",
        [{"name": "returned_to_watchface", "status": "running"}],
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml assertions.jsonl:1 unsupported status running" in result.differences


def test_compare_case_artifacts_reports_missing_core_evidence_ref(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml result.json missing evidence ref assertions.jsonl" in result.differences


def test_compare_case_artifacts_requires_status_field(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "python result.json status must be a string" in result.differences
    assert "yaml result.json status must be a string" in result.differences


def test_compare_case_artifacts_rejects_non_string_status(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": True,
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml result.json status must be a string" in result.differences


def test_compare_case_artifacts_rejects_unsupported_status(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "skipped",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "python result.json unsupported status skipped" in result.differences
    assert "yaml result.json unsupported status skipped" in result.differences


def test_compare_case_artifacts_rejects_passed_case_error_type(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": "assertion_failure",
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml passed result.json must not define error_type" in result.differences


def test_compare_case_artifacts_requires_error_type_for_failed_case(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget", status="failed")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml", status="failed")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "failed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "python failed result.json requires error_type" in result.differences
    assert "yaml failed result.json requires error_type" in result.differences


def test_compare_case_artifacts_rejects_unsupported_error_type(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget", status="failed")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml", status="failed")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "failed",
                "error_type": "bad_error",
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "python result.json unsupported error_type bad_error" in result.differences
    assert "yaml result.json unsupported error_type bad_error" in result.differences


def test_compare_case_artifacts_rejects_error_type_mismatch(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget", status="failed")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml", status="failed")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "failed",
            "error_type": "device_error",
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert (
        "error_type mismatch: python='assertion_failure', yaml='device_error'"
        in result.differences
    )


def test_compare_case_artifacts_requires_case_name_field(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "python result.json case_name must be a string" in result.differences
    assert "yaml result.json case_name must be a string" in result.differences


def test_compare_case_artifacts_rejects_non_string_case_name(
    tmp_path: Path,
) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": ["smoke_widget_yaml"],
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_case_artifacts(python_case, yaml_case)

    assert result.ok is False
    assert "yaml result.json case_name must be a string" in result.differences


def test_artifact_compare_cli_reports_success(tmp_path: Path) -> None:
    python_case = make_case_dir(tmp_path / "python", "smoke_widget")
    yaml_case = make_case_dir(tmp_path / "yaml", "smoke_widget_yaml")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_case),
            str(yaml_case),
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 0
    assert "Artifact comparison passed" in result.stdout


def test_compare_run_artifacts_uses_case_name_mapping(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    write_run_manifest(python_run, selected_tests=["device", "smoke"])
    write_run_manifest(yaml_run, selected_tests=["device", "yaml", "smoke"])
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is True
    assert result.differences == []


def test_compare_run_artifacts_rejects_empty_case_mapping(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    make_run_case_dir(python_run, "smoke_widget")
    make_run_case_dir(yaml_run, "smoke_widget_yaml")

    result = compare_run_artifacts(python_run, yaml_run, {})

    assert result.ok is False
    assert "case_map must include at least one mapping" in result.differences


def test_compare_run_artifacts_reports_missing_run_manifest(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert "python missing run_manifest.json" in result.differences
    assert "yaml missing run_manifest.json" in result.differences


def test_compare_run_artifacts_rejects_invalid_run_manifest_fields(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        python_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "selected_tests": ["device", "smoke"],
            "framework_version": "test",
        },
    )
    write_json(
        yaml_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": "smoke_widget_yaml",
            "framework_version": "test",
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert "python run_manifest.json sds_url must be a string" in result.differences
    assert (
        "yaml run_manifest.json selected_tests must be a string list"
        in result.differences
    )


def test_compare_run_artifacts_rejects_environment_manifest_mismatch(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        python_run / "run_manifest.json",
        {
            "device_serial": "PYTHON123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device", "smoke"],
            "framework_version": "test",
        },
    )
    write_json(
        yaml_run / "run_manifest.json",
        {
            "device_serial": "YAML456",
            "sds_url": "ws://localhost:65535",
            "selected_tests": ["device", "yaml", "smoke"],
            "framework_version": "test",
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert (
        "run_manifest.json device_serial mismatch: "
        "python='PYTHON123', yaml='YAML456'"
    ) in result.differences
    assert (
        "run_manifest.json sds_url mismatch: "
        "python='ws://localhost:65534', yaml='ws://localhost:65535'"
    ) in result.differences


def test_compare_run_artifacts_rejects_framework_version_mismatch(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        python_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device", "smoke"],
            "framework_version": "python-framework",
        },
    )
    write_json(
        yaml_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device", "yaml", "smoke"],
            "framework_version": "yaml-framework",
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert (
        "run_manifest.json framework_version mismatch: "
        "python='python-framework', yaml='yaml-framework'"
    ) in result.differences


def test_compare_run_artifacts_accepts_non_case_selected_test_labels(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    write_run_manifest(python_run, selected_tests=["device", "smoke"])
    write_run_manifest(yaml_run, selected_tests=["device", "yaml", "smoke"])
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke_widget": "smoke_widget_yaml"},
    )

    assert result.ok is True
    assert result.differences == []


def test_compare_run_artifacts_rejects_duplicate_indexed_case_names(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    make_case_dir(python_run / "cases", "smoke-widget-a")
    duplicate_case = make_case_dir(python_run / "cases", "smoke-widget-b")
    write_json(
        duplicate_case / "result.json",
        {
            "case_name": "smoke-widget-a",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = compare_run_artifacts(
        python_run,
        yaml_run,
        {"smoke-widget-a": "smoke_widget_yaml"},
    )

    assert result.ok is False
    assert "python duplicate case_name smoke-widget-a" in result.differences


def test_suggest_case_map_pairs_cases_by_yaml_suffix(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    python_workout_case = make_run_case_dir(python_run, "smoke_workout")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    yaml_workout_case = make_run_case_dir(yaml_run, "smoke_workout_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (python_workout_case, "smoke_workout"),
        (yaml_case, "smoke_widget_yaml"),
        (yaml_workout_case, "smoke_workout_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "passed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = suggest_case_map(python_run, yaml_run)

    assert result == {
        "smoke_widget": "smoke_widget_yaml",
        "smoke_workout": "smoke_workout_yaml",
    }


def test_suggest_case_map_rejects_unmatched_python_case(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "passed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )
    write_json(
        make_run_case_dir(python_run, "orphan_case") / "result.json",
        {
            "case_name": "orphan_case",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    try:
        suggest_case_map(python_run, yaml_run)
    except ValueError as error:
        assert "python unmatched cases" in str(error)
    else:
        raise AssertionError("expected unmatched python case to fail")


def test_parse_case_map_rejects_duplicate_python_case_names() -> None:
    try:
        _parse_case_map(
            [
                "smoke_widget:smoke_widget_yaml",
                "smoke_widget:other_widget_yaml",
            ]
        )
    except SystemExit as error:
        assert "Duplicate --case-map python case: smoke_widget" in str(error)
    else:
        raise AssertionError("expected duplicate python case to fail")


def test_parse_case_map_rejects_duplicate_yaml_case_names() -> None:
    try:
        _parse_case_map(
            [
                "smoke_widget:smoke_widget_yaml",
                "other_widget:smoke_widget_yaml",
            ]
        )
    except SystemExit as error:
        assert "Duplicate --case-map yaml case: smoke_widget_yaml" in str(error)
    else:
        raise AssertionError("expected duplicate yaml case to fail")


def test_artifact_compare_cli_accepts_run_case_map(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    write_run_manifest(python_run, selected_tests=["device", "smoke"])
    write_run_manifest(yaml_run, selected_tests=["device", "yaml", "smoke"])
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--case-map",
            "smoke_widget:smoke_widget_yaml",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 0
    assert "Artifact comparison passed" in result.stdout


def test_artifact_compare_cli_suggests_run_case_map(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    python_workout_case = make_run_case_dir(python_run, "smoke_workout")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    yaml_workout_case = make_run_case_dir(yaml_run, "smoke_workout_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (python_workout_case, "smoke_workout"),
        (yaml_case, "smoke_widget_yaml"),
        (yaml_workout_case, "smoke_workout_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "passed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--suggest-case-map",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 0
    assert "smoke_widget:smoke_widget_yaml" in result.stdout
    assert "smoke_workout:smoke_workout_yaml" in result.stdout


def test_artifact_compare_cli_rejects_unmatched_case_map_suggestion(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    orphan_case = make_run_case_dir(python_run, "orphan_case")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (orphan_case, "orphan_case"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "passed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--suggest-case-map",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode != 0
    assert "Unable to suggest case_map" in result.stderr
    assert "python unmatched cases" in result.stderr


def test_artifact_compare_cli_rejects_case_map_with_suggest_case_map(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    for case_dir, case_name in (
        (python_case, "smoke_widget"),
        (yaml_case, "smoke_widget_yaml"),
    ):
        write_json(
            case_dir / "result.json",
            {
                "case_name": case_name,
                "status": "passed",
                "error_type": None,
                "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
            },
        )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--suggest-case-map",
            "--case-map",
            "smoke_widget:smoke_widget_yaml",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode != 0
    assert "--suggest-case-map cannot be combined with --case-map" in result.stderr


def test_artifact_compare_cli_reports_framework_version_mismatch_for_run_compare(
    tmp_path: Path,
) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    python_case = make_run_case_dir(python_run, "smoke_widget")
    yaml_case = make_run_case_dir(yaml_run, "smoke_widget_yaml")
    write_json(
        python_case / "result.json",
        {
            "case_name": "smoke_widget",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        yaml_case / "result.json",
        {
            "case_name": "smoke_widget_yaml",
            "status": "passed",
            "error_type": None,
            "evidence_refs": ["steps.jsonl", "assertions.jsonl", "result.json"],
        },
    )
    write_json(
        python_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device", "smoke"],
            "framework_version": "python-framework",
        },
    )
    write_json(
        yaml_run / "run_manifest.json",
        {
            "device_serial": "TEST123",
            "sds_url": "ws://localhost:65534",
            "selected_tests": ["device", "yaml", "smoke"],
            "framework_version": "yaml-framework",
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--case-map",
            "smoke_widget:smoke_widget_yaml",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode != 0
    assert "Artifact comparison failed" in result.stderr
    assert (
        "run_manifest.json framework_version mismatch: "
        "python='python-framework', yaml='yaml-framework'"
    ) in result.stderr


def test_artifact_compare_cli_rejects_duplicate_case_map(tmp_path: Path) -> None:
    python_run = tmp_path / "python-run"
    yaml_run = tmp_path / "yaml-run"
    make_run_case_dir(python_run, "smoke_widget")
    make_run_case_dir(yaml_run, "smoke_widget_yaml")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.artifacts.compare",
            str(python_run),
            str(yaml_run),
            "--case-map",
            "smoke_widget:smoke_widget_yaml",
            "--case-map",
            "smoke_widget:other_widget_yaml",
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode != 0
    assert "Duplicate --case-map python case: smoke_widget" in result.stderr
