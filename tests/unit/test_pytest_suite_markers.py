from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _collect_suite(suite_dir: str, marker: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            suite_dir,
            "--collect-only",
            "-q",
            "-m",
            marker,
        ],
        check=False,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )


def _collected_test_names(result: subprocess.CompletedProcess[str]) -> set[str]:
    return {
        line.rsplit("::", 1)[-1]
        for line in result.stdout.splitlines()
        if "::" in line
    }


def test_python_smoke_suite_is_selectable_by_smoke_marker() -> None:
    result = _collect_suite("tests/smoke", "smoke")

    assert result.returncode == 0
    assert _collected_test_names(result) == {
        "test_device_connection_and_watchface_baseline",
        "test_open_settings_and_return",
        "test_open_known_settings_views_smoke",
        "test_open_widget_and_return",
        "test_workout_happy_path_smoke",
    }


def test_python_regression_suite_is_selectable_by_regression_marker() -> None:
    result = _collect_suite("tests/regression", "regression")

    assert result.returncode == 0
    assert _collected_test_names(result) == {
        "test_toggle_focused_setting_regression",
        "test_open_multiple_settings_views_regression",
        "test_switch_widget_and_return_watchface_regression",
        "test_start_pause_resume_stop_workout_regression",
    }


def test_python_stability_suite_is_selectable_by_stability_marker() -> None:
    result = _collect_suite("tests/stability", "stability")

    assert result.returncode == 0
    assert _collected_test_names(result) == {
        "test_watchface_widget_settings_loop",
    }
