import pytest

from tests.conftest import read_content


@pytest.mark.device
def test_open_widget_and_return(device_dsl) -> None:
    case_name = "smoke_widget"
    with device_dsl.session.case(case_name, expected_page="main"):
        baseline_widget = device_dsl.widget.current_name()
        device_dsl.watchface.open_widget(case_name)
        widget_name = device_dsl.widget.current_name()
        device_dsl.session.assert_condition(
            case_name,
            "widget_path_changed_after_open",
            widget_name != baseline_widget,
            actual=widget_name,
            expected=f"!= {baseline_widget}",
        )
        device_dsl.widget.go_back(case_name)
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "returned_to_watchface_after_widget",
            current_page == "main",
            actual=current_page,
            expected="main",
        )
