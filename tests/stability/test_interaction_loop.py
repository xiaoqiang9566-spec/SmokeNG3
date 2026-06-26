import pytest

from tests.conftest import read_content


@pytest.mark.device
@pytest.mark.stability
def test_watchface_widget_settings_loop(device_dsl) -> None:
    for index in range(5):
        widget_case = f"stability_widget_{index}"
        with device_dsl.session.case(widget_case, expected_page="main"):
            device_dsl.watchface.open_widget(widget_case)
            widget_name = device_dsl.widget.current_name()
            device_dsl.session.assert_condition(
                widget_case,
                "widget_name_is_non_empty",
                bool(widget_name.strip()),
                actual=widget_name,
                expected="non-empty widget name",
            )
            device_dsl.widget.go_back(widget_case)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                widget_case,
                "returned_to_watchface_after_widget",
                current_page == "main",
                actual=current_page,
                expected="main",
            )

        settings_case = f"stability_settings_{index}"
        with device_dsl.session.case(settings_case, expected_page="main"):
            device_dsl.settings.open_root(settings_case)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                settings_case,
                "entered_settings_root",
                current_page == "s-main",
                actual=current_page,
                expected="s-main",
            )
            focused_item = device_dsl.settings.focused_item()
            device_dsl.session.assert_condition(
                settings_case,
                "settings_focus_signature_is_non_empty",
                bool(focused_item.strip()) and "|" in focused_item,
                actual=focused_item,
                expected="non-empty focus signature",
            )
            device_dsl.settings.go_back(settings_case)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                settings_case,
                "returned_to_watchface_after_settings",
                current_page == "main",
                actual=current_page,
                expected="main",
            )
