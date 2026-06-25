from pathlib import Path

import pytest

from watch_ui_automation import __version__
from watch_ui_automation.config import load_project_config


def test_package_bootstrap_loads_yaml_config(tmp_path: Path) -> None:
    config_file = tmp_path / "device.yaml"
    config_file.write_text(
        "\n".join(
            [
                "device:",
                "  serial: TEST123",
                "  sds_url: ws://localhost:65534",
                "timeouts:",
                "  request_seconds: 8",
                "  settle_seconds: 1.5",
                "  poll_interval_seconds: 0.25",
                "artifacts:",
                "  root_dir: artifacts",
                "resources:",
                "  current_page_uri: suunto://{serial}/System/UI/CurrentPage",
                "  current_widget_uri: suunto://{serial}/System/UI/CurrentWidget",
                "  workout_state_uri: suunto://{serial}/Sport/Workout/State",
                "  settings_focus_uri: suunto://{serial}/System/UI/Settings/FocusedItem",
                "input:",
                "  tap_center_x: 233",
                "  tap_center_y: 233",
                "  swipe_left_start_x: 320",
                "  swipe_left_end_x: 120",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 320",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - press_top",
                "  go_back:",
                "    - press_bottom",
                "  workout_pause_resume:",
                "    - press_middle",
            ]
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_file)

    assert __version__ == "0.1.0"
    assert config.device.serial == "TEST123"
    assert config.timeouts.request_seconds == 8
    assert config.timeouts.poll_interval_seconds == 0.25
    assert config.resources.current_page_uri == "suunto://TEST123/System/UI/CurrentPage"
    assert config.resources.current_widget_uri == "suunto://TEST123/System/UI/CurrentWidget"


def test_package_bootstrap_loads_input_and_navigation_config(tmp_path: Path) -> None:
    config_file = tmp_path / "device.yaml"
    config_file.write_text(
        "\n".join(
            [
                "device:",
                "  serial: TEST123",
                "  sds_url: ws://localhost:65534",
                "timeouts:",
                "  request_seconds: 8",
                "  settle_seconds: 1.5",
                "  poll_interval_seconds: 0.25",
                "artifacts:",
                "  root_dir: artifacts",
                "resources:",
                "  current_page_uri: suunto://{serial}/System/UI/CurrentPage",
                "  current_widget_uri: suunto://{serial}/System/UI/CurrentWidget",
                "  workout_state_uri: suunto://{serial}/Sport/Workout/State",
                "  settings_focus_uri: suunto://{serial}/System/UI/Settings/FocusedItem",
                "input:",
                "  tap_center_x: 233",
                "  tap_center_y: 233",
                "  swipe_left_start_x: 320",
                "  swipe_left_end_x: 120",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 320",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - press_top",
                "  go_back:",
                "    - press_bottom",
                "  workout_pause_resume:",
                "    - press_middle",
            ]
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_file)

    assert config.input.tap_center_x == 233
    assert config.navigation.open_widget == ["swipe_left"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("", "config file is empty"),
        ("- item\n- item2\n", "top-level config must be a mapping"),
        (
            "\n".join(
                [
                    "device:",
                    "  serial: TEST123",
                    "  sds_url: ws://localhost:65534",
                    "timeouts:",
                    "  request_seconds: 8",
                    "  settle_seconds: 1.5",
                    "  poll_interval_seconds: 0.25",
                    "artifacts:",
                    "  root_dir: artifacts",
                ]
            ),
            "missing config section: resources",
        ),
    ],
)
def test_load_project_config_rejects_invalid_yaml(
    tmp_path: Path, payload: str, message: str
) -> None:
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_project_config(config_file)
