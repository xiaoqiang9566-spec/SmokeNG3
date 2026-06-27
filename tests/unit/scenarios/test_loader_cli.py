from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import os


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_ROOT) if not existing else f"{SRC_ROOT}{os.pathsep}{existing}"
    )
    return env


def write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loader_cli_validate_accepts_valid_scenario_dir(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "valid.yaml",
        """
cases:
  - id: smoke_widget
    title: Smoke widget
    markers: [yaml, smoke]
    baseline: main
    steps:
      - name: capture page
        action: capture.current_page
        save_as: page
      - name: assert page
        action: assert.equals
        params:
          actual: ${page.name}
          expected: main
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.scenarios.loader",
            "validate",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 0
    assert "Validated 1 scenario case" in result.stdout


def test_loader_cli_validate_reports_schema_errors(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: smoke_widget
    title: Smoke widget
    markers: [yaml]
    baseline: main
    steps:
      - name: bad action
        action: missing.action
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.scenarios.loader",
            "validate",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 1
    assert "Unknown action 'missing.action'" in result.stderr


def test_loader_cli_validate_reports_invalid_yaml_syntax(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: broken
    title: Broken
    markers: [yaml
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "watch_ui_automation.scenarios.loader",
            "validate",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        env=cli_env(),
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid YAML" in result.stderr
    assert str(scenario_file) in result.stderr
