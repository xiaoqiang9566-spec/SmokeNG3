import pytest

from tests.conftest import read_content


@pytest.mark.device
@pytest.mark.smoke
def test_device_connection_and_watchface_baseline(device_dsl) -> None:
    case_name = "smoke_device_connection"
    with device_dsl.session.case(case_name, expected_page="main"):
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "watchface_visible_at_baseline",
            current_page in {"c-lowp", "main"},
            actual=current_page,
            expected="c-lowp or main",
        )
