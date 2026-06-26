from pathlib import Path

import pytest

from watch_ui_automation import __version__
from watch_ui_automation.config import SUPPORTED_NAVIGATION_ACTIONS, load_project_config


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
                "  swipe_left_start_x: 420",
                "  swipe_left_end_x: 46",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 360",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - swipe_up",
                "  go_back:",
                "    - press_bottom_left",
                "  workout_pause_resume:",
                "    - press_top",
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
                "  swipe_left_start_x: 420",
                "  swipe_left_end_x: 46",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 360",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - swipe_up",
                "  go_back:",
                "    - press_bottom_left",
                "  workout_pause_resume:",
                "    - press_top",
            ]
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_file)

    assert config.input.tap_center_x == 233
    assert config.navigation.open_widget == ["swipe_left"]


def test_default_config_matches_task4_defaults() -> None:
    config = load_project_config(Path("configs/default.yaml"))

    assert config.input.tap_center_x == 233
    assert config.input.tap_center_y == 233
    assert config.input.swipe_left_start_x == 420
    assert config.input.swipe_left_end_x == 46
    assert config.input.swipe_horizontal_y == 233
    assert config.input.swipe_up_x == 233
    assert config.input.swipe_up_start_y == 360
    assert config.input.swipe_up_end_y == 120
    assert config.navigation.open_settings == ["press_middle"]
    assert config.navigation.open_widget == ["swipe_left"]
    assert config.navigation.open_workout == ["swipe_up"]
    assert config.navigation.go_back == ["press_bottom_left"]
    assert config.navigation.workout_pause_resume == ["press_top"]


def test_load_project_config_rejects_invalid_navigation_action(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "invalid-navigation.yaml"
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
                "  swipe_left_start_x: 420",
                "  swipe_left_end_x: 46",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 360",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - invalid_action",
                "  go_back:",
                "    - press_bottom_left",
                "  workout_pause_resume:",
                "    - press_top",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid navigation action"):
        load_project_config(config_file)


def test_load_project_config_rejects_invalid_input_coordinate_type(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "invalid-input.yaml"
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
                "  tap_center_x: bad",
                "  tap_center_y: 233",
                "  swipe_left_start_x: 420",
                "  swipe_left_end_x: 46",
                "  swipe_horizontal_y: 233",
                "  swipe_up_x: 233",
                "  swipe_up_start_y: 360",
                "  swipe_up_end_y: 120",
                "navigation:",
                "  open_settings:",
                "    - press_middle",
                "  open_widget:",
                "    - swipe_left",
                "  open_workout:",
                "    - swipe_up",
                "  go_back:",
                "    - press_bottom_left",
                "  workout_pause_resume:",
                "    - press_top",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="input.tap_center_x"):
        load_project_config(config_file)


def test_supported_navigation_actions_include_task4_defaults() -> None:
    assert "press_middle" in SUPPORTED_NAVIGATION_ACTIONS
    assert "swipe_left" in SUPPORTED_NAVIGATION_ACTIONS
    assert "press_top_left" in SUPPORTED_NAVIGATION_ACTIONS
    assert "press_bottom_left" in SUPPORTED_NAVIGATION_ACTIONS
    assert "press_top" in SUPPORTED_NAVIGATION_ACTIONS


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
