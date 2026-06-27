from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scenario_collect_defaults_to_smoke_suite() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/scenario",
            "--collect-only",
            "-q",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "test_yaml_scenario[smoke_widget_yaml]" in result.stdout
    assert "test_yaml_scenario[smoke_workout_yaml]" in result.stdout
    assert "NOTSET" not in result.stdout


def test_scenario_collect_rejects_unknown_suite() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/scenario",
            "--scenario-suite",
            "missing",
            "--collect-only",
            "-q",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "No scenario YAML files found" in output
    assert "NOTSET" not in output


def test_scenario_runtime_skips_device_cases_without_real_device_opt_in() -> None:
    env = os.environ.copy()
    env.pop("WATCH_UI_RUN_DEVICE_TESTS", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/scenario",
            "-v",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[3]),
        env=env,
    )

    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "test_yaml_scenario[smoke_widget_yaml]" in output
    assert "test_yaml_scenario[smoke_workout_yaml]" in output
    assert "SKIPPED" in output
    assert "Set WATCH_UI_RUN_DEVICE_TESTS=1 to run real-device tests" in output
    assert "2 skipped" in output or "SKIPPED [2]" in output


def test_python_compare_scope_collects_only_widget_and_workout_smoke_cases() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/smoke/test_widget_smoke.py",
            "tests/smoke/test_workout_smoke.py",
            "--collect-only",
            "-q",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "test_open_widget_and_return" in output
    assert "test_workout_happy_path_smoke" in output
    assert "test_device_connection_and_watchface_baseline" not in output
    assert "test_open_settings_and_return" not in output
    assert "test_open_known_settings_views_smoke" not in output
    assert "2 tests collected" in output
