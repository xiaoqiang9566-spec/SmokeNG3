import pytest

from tests.conftest import read_content


@pytest.mark.device
@pytest.mark.smoke
def test_open_settings_and_return(device_dsl) -> None:
    case_name = "smoke_settings"
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
        focused_item = device_dsl.settings.focused_item()
        device_dsl.session.assert_condition(
            case_name,
            "settings_focus_signature_is_non_empty",
            bool(focused_item.strip()) and "|" in focused_item,
            actual=focused_item,
            expected="non-empty focus signature",
        )
        device_dsl.settings.go_back(case_name)
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "returned_to_watchface_after_settings",
            current_page == "main",
            actual=current_page,
            expected="main",
        )
