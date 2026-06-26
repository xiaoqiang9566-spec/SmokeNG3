import pytest

from tests.conftest import read_content


@pytest.mark.device
def test_toggle_focused_setting_regression(device_dsl) -> None:
    case_name = "regression_settings"
    with device_dsl.session.case(case_name, expected_page="main"):
        device_dsl.settings.open_root(case_name)
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "entered_settings_root",
            current_page == "s-main",
            actual=current_page,
            expected="s-main",
        )
        first_focus = device_dsl.settings.focused_item()
        device_dsl.session.assert_condition(
            case_name,
            "initial_settings_focus_signature_is_non_empty",
            bool(first_focus.strip()) and "|" in first_focus,
            actual=first_focus,
            expected="non-empty focus signature",
        )
        device_dsl.settings.go_back(case_name)


@pytest.mark.device
def test_open_multiple_settings_views_regression(device_dsl) -> None:
    case_name = "regression_settings_views"
    view_names = ["s-main", "s-ge", "s-cu"]
    with device_dsl.session.case(case_name, expected_page="main"):
        for view_name in view_names:
            device_dsl.settings.open_view(case_name, view_name=view_name)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                case_name,
                f"entered_{view_name}",
                current_page == view_name,
                actual=current_page,
                expected=view_name,
            )
            device_dsl.settings.close_view(case_name, view_name=view_name)
            current_page = read_content(device_dsl, "current_page")
            device_dsl.session.assert_condition(
                case_name,
                f"returned_to_watchface_after_{view_name}",
                current_page == "main",
                actual=current_page,
                expected="main",
            )
