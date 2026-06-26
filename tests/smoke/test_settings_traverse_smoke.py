import pytest

from tests.conftest import read_content


@pytest.mark.device
def test_open_known_settings_views_smoke(device_dsl) -> None:
    case_name = "smoke_settings_views"
    view_names = ["s-main", "s-ge"]
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
