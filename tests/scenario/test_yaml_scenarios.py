import pytest

from watch_ui_automation.actions import create_default_registry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.loader import load_scenarios
from watch_ui_automation.scenarios.runner import run_case

ACTION_REGISTRY = create_default_registry()


def pytest_generate_tests(metafunc) -> None:
    if "scenario_case" not in metafunc.fixturenames:
        return

    cases = load_scenarios(
        metafunc.config.getoption("--scenario-dir"),
        suite=metafunc.config.getoption("--scenario-suite"),
        registry=ACTION_REGISTRY,
    )
    params = [
        pytest.param(
            case,
            id=case.id,
            marks=[getattr(pytest.mark, marker) for marker in case.markers],
        )
        for case in cases
    ]
    metafunc.parametrize("scenario_case", params)


def test_yaml_scenario(device_dsl, scenario_case) -> None:
    ctx = ScenarioContext(
        dsl=device_dsl,
        session=device_dsl.session,
        case_id=scenario_case.id,
        baseline=scenario_case.baseline,
    )

    run_case(scenario_case, ctx, ACTION_REGISTRY)
