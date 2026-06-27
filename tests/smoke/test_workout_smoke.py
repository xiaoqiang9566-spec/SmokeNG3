import pytest

from tests.conftest import read_content


@pytest.mark.device
@pytest.mark.smoke
def test_workout_happy_path_smoke(device_dsl) -> None:
    case_name = "smoke_workout"
    with device_dsl.session.case(case_name, expected_page="main"):
        baseline_page = read_content(device_dsl, "current_page")
        device_dsl.watchface.open_workout(case_name)
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "page_changed_after_workout_open",
            current_page != baseline_page,
            actual=current_page,
            expected=f"!= {baseline_page}",
        )
        workout_state = device_dsl.workout.state()
        device_dsl.session.assert_condition(
            case_name,
            "workout_state_is_non_empty",
            bool(workout_state.strip()),
            actual=workout_state,
            expected="non-empty workout state",
        )
        device_dsl.workout.pause_or_resume(case_name)
        device_dsl.workout.pause_or_resume(case_name)
        device_dsl.workout.stop(case_name)
        current_page = read_content(device_dsl, "current_page")
        device_dsl.session.assert_condition(
            case_name,
            "returned_to_watchface_after_workout",
            current_page == "main",
            actual=current_page,
            expected="main",
        )
