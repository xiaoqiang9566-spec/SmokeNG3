from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
from typing import Any

from watch_ui_automation.models import CASE_STATUSES, ERROR_TYPES

_CORE_FILES = ("steps.jsonl", "assertions.jsonl", "result.json")
_JSONL_STATUSES = {
    "steps.jsonl": {"running", "performed", "passed", "failed", "error"},
    "assertions.jsonl": {"passed", "failed"},
}
_RUN_MANIFEST_STRING_FIELDS = ("device_serial", "sds_url", "framework_version")


@dataclass(frozen=True)
class ArtifactComparison:
    ok: bool
    differences: list[str]
    python_status: str | None
    yaml_status: str | None


def compare_case_artifacts(
    python_case_dir: str | Path,
    yaml_case_dir: str | Path,
) -> ArtifactComparison:
    python_dir = Path(python_case_dir)
    yaml_dir = Path(yaml_case_dir)
    differences: list[str] = []

    _check_core_files("python", python_dir, differences)
    _check_core_files("yaml", yaml_dir, differences)

    python_result = _read_result("python", python_dir, differences)
    yaml_result = _read_result("yaml", yaml_dir, differences)
    _case_name_from_result("python", python_result, differences)
    _case_name_from_result("yaml", yaml_result, differences)
    _check_core_evidence_refs("python", python_result, differences)
    _check_core_evidence_refs("yaml", yaml_result, differences)
    python_status = _status_from_result("python", python_result, differences)
    yaml_status = _status_from_result("yaml", yaml_result, differences)
    python_error_type = _error_type_from_result(
        "python", python_result, python_status, differences
    )
    yaml_error_type = _error_type_from_result(
        "yaml", yaml_result, yaml_status, differences
    )

    if python_status != yaml_status:
        differences.append(
            f"status mismatch: python={python_status!r}, yaml={yaml_status!r}"
        )
    if python_error_type != yaml_error_type:
        differences.append(
            "error_type mismatch: "
            f"python={python_error_type!r}, yaml={yaml_error_type!r}"
        )

    _check_jsonl_non_empty("python", python_dir, "steps.jsonl", differences)
    _check_jsonl_non_empty("yaml", yaml_dir, "steps.jsonl", differences)
    _check_jsonl_non_empty("python", python_dir, "assertions.jsonl", differences)
    _check_jsonl_non_empty("yaml", yaml_dir, "assertions.jsonl", differences)

    return ArtifactComparison(
        ok=not differences,
        differences=differences,
        python_status=python_status,
        yaml_status=yaml_status,
    )


def compare_run_artifacts(
    python_run_dir: str | Path,
    yaml_run_dir: str | Path,
    case_map: dict[str, str],
) -> ArtifactComparison:
    differences: list[str] = []
    if not case_map:
        differences.append("case_map must include at least one mapping")

    python_run = Path(python_run_dir)
    yaml_run = Path(yaml_run_dir)
    python_manifest = _read_run_manifest("python", python_run, differences)
    yaml_manifest = _read_run_manifest("yaml", yaml_run, differences)
    _compare_run_manifest_environment(python_manifest, yaml_manifest, differences)
    python_cases = _index_run_cases("python", python_run, differences)
    yaml_cases = _index_run_cases("yaml", yaml_run, differences)
    python_status: str | None = None
    yaml_status: str | None = None

    for python_case_name, yaml_case_name in case_map.items():
        python_case_dir = python_cases.get(python_case_name)
        yaml_case_dir = yaml_cases.get(yaml_case_name)
        if python_case_dir is None:
            differences.append(f"python missing case {python_case_name}")
            continue
        if yaml_case_dir is None:
            differences.append(f"yaml missing case {yaml_case_name}")
            continue

        case_result = compare_case_artifacts(python_case_dir, yaml_case_dir)
        if python_status is None:
            python_status = case_result.python_status
        if yaml_status is None:
            yaml_status = case_result.yaml_status
        for difference in case_result.differences:
            differences.append(
                f"{python_case_name}->{yaml_case_name}: {difference}"
            )

    return ArtifactComparison(
        ok=not differences,
        differences=differences,
        python_status=python_status,
        yaml_status=yaml_status,
    )


def suggest_case_map(
    python_run_dir: str | Path,
    yaml_run_dir: str | Path,
    *,
    yaml_suffix: str = "_yaml",
) -> dict[str, str]:
    python_run = Path(python_run_dir)
    yaml_run = Path(yaml_run_dir)
    python_differences: list[str] = []
    yaml_differences: list[str] = []
    python_cases = _index_run_cases("python", python_run, python_differences)
    yaml_cases = _index_run_cases("yaml", yaml_run, yaml_differences)
    if python_differences or yaml_differences:
        problems = python_differences + yaml_differences
        raise ValueError("; ".join(problems))

    mapping: dict[str, str] = {}
    used_yaml_cases: set[str] = set()
    python_unmatched: list[str] = []

    for python_case_name in sorted(python_cases):
        preferred_yaml_case = f"{python_case_name}{yaml_suffix}"
        candidate = None
        if preferred_yaml_case in yaml_cases:
            candidate = preferred_yaml_case
        elif python_case_name in yaml_cases:
            candidate = python_case_name

        if candidate is None:
            python_unmatched.append(python_case_name)
            continue
        if candidate in used_yaml_cases:
            python_unmatched.append(python_case_name)
            continue

        mapping[python_case_name] = candidate
        used_yaml_cases.add(candidate)

    yaml_unmatched = sorted(case_name for case_name in yaml_cases if case_name not in used_yaml_cases)
    if python_unmatched or yaml_unmatched:
        problems: list[str] = []
        if python_unmatched:
            problems.append(f"python unmatched cases: {', '.join(python_unmatched)}")
        if yaml_unmatched:
            problems.append(f"yaml unmatched cases: {', '.join(yaml_unmatched)}")
        raise ValueError("; ".join(problems))

    return mapping


def _check_core_files(label: str, case_dir: Path, differences: list[str]) -> None:
    for filename in _CORE_FILES:
        if not (case_dir / filename).is_file():
            differences.append(f"{label} missing {filename}")


def _read_result(
    label: str,
    case_dir: Path,
    differences: list[str],
) -> dict[str, Any] | None:
    path = case_dir / "result.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        differences.append(f"{label} result.json is invalid JSON: {error}")
        return None
    if not isinstance(payload, dict):
        differences.append(f"{label} result.json must be an object")
        return None
    return payload


def _index_run_cases(
    label: str,
    run_dir: Path,
    differences: list[str],
) -> dict[str, Path]:
    cases_dir = run_dir / "cases"
    if not cases_dir.is_dir():
        differences.append(f"{label} missing cases directory")
        return {}

    index: dict[str, Path] = {}
    for result_path in sorted(cases_dir.glob("*/result.json")):
        result = _read_result(label, result_path.parent, differences)
        if result is None:
            continue
        case_name = result.get("case_name")
        if not isinstance(case_name, str):
            differences.append(f"{label} {result_path} missing case_name")
            continue
        if case_name in index:
            differences.append(f"{label} duplicate case_name {case_name}")
            continue
        index[case_name] = result_path.parent
    return index


def _read_run_manifest(
    label: str,
    run_dir: Path,
    differences: list[str],
) -> dict[str, Any] | None:
    path = run_dir / "run_manifest.json"
    if not path.is_file():
        differences.append(f"{label} missing run_manifest.json")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        differences.append(f"{label} run_manifest.json is invalid JSON: {error}")
        return None
    if not isinstance(payload, dict):
        differences.append(f"{label} run_manifest.json must be an object")
        return None
    valid = True
    for field in _RUN_MANIFEST_STRING_FIELDS:
        if not isinstance(payload.get(field), str):
            differences.append(f"{label} run_manifest.json {field} must be a string")
            valid = False
    selected_tests = payload.get("selected_tests")
    if not isinstance(selected_tests, list) or not all(
        isinstance(item, str) for item in selected_tests
    ):
        differences.append(
            f"{label} run_manifest.json selected_tests must be a string list"
        )
        valid = False
    if not valid:
        return None
    return payload


def _compare_run_manifest_environment(
    python_manifest: dict[str, Any] | None,
    yaml_manifest: dict[str, Any] | None,
    differences: list[str],
) -> None:
    if python_manifest is None or yaml_manifest is None:
        return
    for field in ("device_serial", "sds_url", "framework_version"):
        python_value = python_manifest[field]
        yaml_value = yaml_manifest[field]
        if python_value != yaml_value:
            differences.append(
                f"run_manifest.json {field} mismatch: "
                f"python={python_value!r}, yaml={yaml_value!r}"
            )


def _status_from_result(
    label: str,
    result: dict[str, Any] | None,
    differences: list[str],
) -> str | None:
    if result is None:
        return None
    status = result.get("status")
    if not isinstance(status, str):
        differences.append(f"{label} result.json status must be a string")
        return None
    if status in CASE_STATUSES:
        return status
    differences.append(f"{label} result.json unsupported status {status}")
    return None


def _case_name_from_result(
    label: str,
    result: dict[str, Any] | None,
    differences: list[str],
) -> str | None:
    if result is None:
        return None
    case_name = result.get("case_name")
    if isinstance(case_name, str):
        return case_name
    differences.append(f"{label} result.json case_name must be a string")
    return None


def _error_type_from_result(
    label: str,
    result: dict[str, Any] | None,
    status: str | None,
    differences: list[str],
) -> str | None:
    if result is None or status is None:
        return None
    error_type = result.get("error_type")
    if status == "passed":
        if error_type is not None:
            differences.append(f"{label} passed result.json must not define error_type")
        return None
    if error_type is None:
        differences.append(f"{label} {status} result.json requires error_type")
        return None
    if not isinstance(error_type, str):
        differences.append(f"{label} result.json error_type must be a string")
        return None
    if error_type not in ERROR_TYPES:
        differences.append(f"{label} result.json unsupported error_type {error_type}")
        return None
    return error_type


def _check_core_evidence_refs(
    label: str,
    result: dict[str, Any] | None,
    differences: list[str],
) -> None:
    if result is None:
        return
    evidence_refs = result.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not all(
        isinstance(item, str) for item in evidence_refs
    ):
        differences.append(f"{label} result.json evidence_refs must be a string list")
        return
    for filename in _CORE_FILES:
        if filename not in evidence_refs:
            differences.append(
                f"{label} result.json missing evidence ref {filename}"
            )


def _check_jsonl_non_empty(
    label: str,
    case_dir: Path,
    filename: str,
    differences: list[str],
) -> None:
    path = case_dir / filename
    if not path.is_file():
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        differences.append(f"{label} {filename} is empty")
        return
    for index, line in enumerate(lines, start=1):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            differences.append(f"{label} {filename}:{index} invalid JSON: {error}")
            continue
        if not isinstance(payload, dict):
            differences.append(f"{label} {filename}:{index} must be an object")
            continue
        if not isinstance(payload.get("name"), str):
            differences.append(f"{label} {filename}:{index} name must be a string")
        status = payload.get("status")
        if not isinstance(status, str):
            differences.append(f"{label} {filename}:{index} status must be a string")
        elif status not in _JSONL_STATUSES[filename]:
            differences.append(
                f"{label} {filename}:{index} unsupported status {status}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare core artifact structure between Python and YAML cases."
    )
    parser.add_argument("python_case_dir")
    parser.add_argument("yaml_case_dir")
    parser.add_argument(
        "--suggest-case-map",
        action="store_true",
        help="Print suggested python_case:yaml_case mappings for two run directories.",
    )
    parser.add_argument(
        "--yaml-case-suffix",
        default="_yaml",
        help="Suffix used when suggesting YAML case names from Python case names.",
    )
    parser.add_argument(
        "--case-map",
        action="append",
        default=[],
        help="Compare run directories by case name mapping, e.g. smoke_widget:smoke_widget_yaml",
    )
    args = parser.parse_args(argv)

    if args.suggest_case_map and args.case_map:
        print(
            "--suggest-case-map cannot be combined with --case-map",
            file=sys.stderr,
        )
        return 1

    if args.suggest_case_map:
        try:
            result = suggest_case_map(
                args.python_case_dir,
                args.yaml_case_dir,
                yaml_suffix=args.yaml_case_suffix,
            )
        except ValueError as error:
            print(f"Unable to suggest case_map: {error}", file=sys.stderr)
            return 1
        for python_case_name, yaml_case_name in result.items():
            print(f"{python_case_name}:{yaml_case_name}")
        return 0

    if args.case_map:
        result = compare_run_artifacts(
            args.python_case_dir,
            args.yaml_case_dir,
            _parse_case_map(args.case_map),
        )
    else:
        result = compare_case_artifacts(args.python_case_dir, args.yaml_case_dir)
    if result.ok:
        print(
            "Artifact comparison passed "
            f"(python_status={result.python_status}, yaml_status={result.yaml_status})"
        )
        return 0

    print("Artifact comparison failed", file=sys.stderr)
    for difference in result.differences:
        print(f"- {difference}", file=sys.stderr)
    return 1


def _parse_case_map(raw_items: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    yaml_cases: set[str] = set()
    for item in raw_items:
        if ":" not in item:
            raise SystemExit(f"Invalid --case-map value: {item}")
        python_case, yaml_case = item.split(":", 1)
        if not python_case or not yaml_case:
            raise SystemExit(f"Invalid --case-map value: {item}")
        if python_case in mapping:
            raise SystemExit(f"Duplicate --case-map python case: {python_case}")
        if yaml_case in yaml_cases:
            raise SystemExit(f"Duplicate --case-map yaml case: {yaml_case}")
        mapping[python_case] = yaml_case
        yaml_cases.add(yaml_case)
    return mapping


if __name__ == "__main__":
    raise SystemExit(main())
