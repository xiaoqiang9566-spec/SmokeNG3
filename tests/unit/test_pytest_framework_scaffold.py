from pathlib import Path

import yaml


def test_root_pytest_framework_scaffold_exists() -> None:
    expected_paths = [
        "config/config.yaml",
        "config/env.yaml",
        "config/settings.py",
        "common/logger.py",
        "common/yaml_util.py",
        "common/request_util.py",
        "common/assertion.py",
        "common/file_util.py",
        "common/retry.py",
        "pages/base_page.py",
        "pages/sport_page.py",
        "pages/widget_page.py",
        "pages/settings_page.py",
        "testcase/test_sport.py",
        "testcase/test_widget.py",
        "testcase/test_settings.py",
        "data/sport.yaml",
        "data/widget.yaml",
        "data/settings.yaml",
        "reports/allure-results/.gitkeep",
        "reports/allure-report/.gitkeep",
        "logs/.gitkeep",
        "conftest.py",
        "requirements.txt",
        "run.py",
    ]

    for expected_path in expected_paths:
        assert Path(expected_path).exists(), expected_path


def test_input_capability_catalog_defines_buttons_and_gestures() -> None:
    config = yaml.safe_load(Path("config/config.yaml").read_text(encoding="utf-8"))
    capabilities = config["input_capabilities"]

    buttons = capabilities["buttons"]
    assert buttons["press_top"]["button_id"] == 0
    assert buttons["press_middle"]["button_id"] == 1
    assert buttons["press_bottom"]["button_id"] == 2
    assert buttons["press_top_left"]["button_id"] == 3
    assert buttons["press_bottom_left"]["button_id"] == 4
    assert capabilities["durations"] == {"short_press": 0.1, "long_press": 2}

    gestures = capabilities["gestures"]
    assert {"tap_center", "swipe_up", "swipe_down", "swipe_left", "swipe_right"} <= set(gestures)
    assert gestures["swipe_up"]["direction"] == "up"
    assert gestures["swipe_left"]["direction"] == "left"


def test_module_data_files_are_placeholders_for_three_modules() -> None:
    expected_modules = {
        "sport": "sport",
        "widget": "widget",
        "settings": "settings",
    }

    for file_name, module_name in expected_modules.items():
        payload = yaml.safe_load(Path(f"data/{file_name}.yaml").read_text(encoding="utf-8"))
        assert payload["module"] == module_name
        assert payload["cases"] == []


def test_legacy_testcase_placeholders_are_marked_with_todo_notes() -> None:
    expected_todos = {
        "testcase/test_sport.py": "TODO: replace legacy sport placeholder",
        "testcase/test_widget.py": "TODO: replace legacy widget placeholder",
        "testcase/test_settings.py": "TODO: replace legacy settings placeholder",
    }

    for file_name, todo_marker in expected_todos.items():
        content = Path(file_name).read_text(encoding="utf-8")
        assert todo_marker in content
