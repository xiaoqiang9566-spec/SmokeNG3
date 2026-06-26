import pytest

from tests.conftest import read_content


@pytest.mark.device
def test_switch_widget_and_return_watchface_regression(device_dsl) -> None:
    case_name = "regression_widget"
    with device_dsl.session.case(case_name, expected_page="main"):
        baseline_widget = device_dsl.widget.current_name()
        device_dsl.watchface.open_widget(case_name)
        first_widget = device_dsl.widget.current_name()
        device_dsl.session.assert_condition(
            case_name,
            "widget_path_changed_after_first_open",
            first_widget != baseline_widget,
            actual=first_widget,
            expected=f"!= {baseline_widget}",
        )
        device_dsl.widget.go_back(case_name)

        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "returned_to_watchface_after_first_widget_open",
            current_page == "main",
            actual=current_page,
            expected="main",
        )

        device_dsl.watchface.open_widget(case_name)
        second_widget = device_dsl.widget.current_name()
        device_dsl.session.assert_condition(
            case_name,
            "widget_name_is_stable_across_reentry",
            second_widget == first_widget,
            actual=second_widget,
            expected=first_widget,
        )
        device_dsl.widget.go_back(case_name)
