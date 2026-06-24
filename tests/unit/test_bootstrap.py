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
