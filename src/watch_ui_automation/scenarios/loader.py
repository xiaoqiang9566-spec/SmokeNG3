from __future__ import annotations

from pathlib import Path
import argparse
import sys

import yaml

from watch_ui_automation.actions import create_default_registry
from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.errors import ScenarioSchemaError
from watch_ui_automation.scenarios.models import ScenarioCase
from watch_ui_automation.scenarios.schema import parse_cases


def load_scenarios(
    scenario_dir: str | Path,
    *,
    registry: ActionRegistry,
    suite: str | None = None,
) -> list[ScenarioCase]:
    root = Path(scenario_dir)
    search_root = root / suite if suite else root
    scenario_files = sorted(search_root.glob("*.yaml"))
    if not scenario_files:
        raise ScenarioSchemaError(f"No scenario YAML files found in {search_root}")

    cases: list[ScenarioCase] = []
    seen_ids: set[str] = set()
    for scenario_file in scenario_files:
        try:
            payload = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ScenarioSchemaError(
                f"Invalid YAML in {scenario_file}: {error}"
            ) from error
        file_cases = parse_cases(
            payload,
            source_file=str(scenario_file),
            registry=registry,
        )
        for case in file_cases:
            if case.id in seen_ids:
                raise ScenarioSchemaError(f"Duplicate case id '{case.id}'")
            seen_ids.add(case.id)
            cases.append(case)
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate YAML scenario cases without connecting to a device."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("scenario_dir")
    validate_parser.add_argument("--suite", default=None)

    args = parser.parse_args(argv)
    if args.command == "validate":
        try:
            cases = load_scenarios(
                args.scenario_dir,
                suite=args.suite,
                registry=create_default_registry(),
            )
        except ScenarioSchemaError as error:
            print(str(error), file=sys.stderr)
            return 1

        suffix = "case" if len(cases) == 1 else "cases"
        print(f"Validated {len(cases)} scenario {suffix}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
