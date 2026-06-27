from __future__ import annotations

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.errors import (
    ScenarioStepAssertionError,
    ScenarioStepError,
)
from watch_ui_automation.scenarios.models import (
    PageState,
    ScenarioCase,
    WidgetState,
    WorkoutState,
)

_ALLOWED_RESULT_TYPES = (
    str,
    int,
    float,
    bool,
    PageState,
    WidgetState,
    WorkoutState,
)


def run_case(
    case: ScenarioCase,
    ctx: ScenarioContext,
    registry: ActionRegistry,
) -> None:
    with ctx.session.case(case.id, expected_page=case.baseline):
        for index, step in enumerate(case.steps, start=1):
            ctx.current_step = step
            try:
                resolved_params = ctx.resolve_params(step.params)
                ctx.session.record_step(
                    case.id,
                    "yaml_step_start",
                    "running",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                )
                result = registry.call(step.action, ctx, **resolved_params)
                if step.save_as:
                    validate_saved_result(result)
                    ctx.save_variable(step.save_as, result)
                ctx.session.record_step(
                    case.id,
                    "yaml_step_end",
                    "passed",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                )
            except Exception as exc:
                ctx.session.record_step(
                    case.id,
                    "yaml_step_end",
                    "failed",
                    step_index=index,
                    step_name=step.name,
                    action=step.action,
                    error=str(exc),
                )
                error_type = (
                    ScenarioStepAssertionError
                    if isinstance(exc, AssertionError)
                    else ScenarioStepError
                )
                raise error_type.from_exception(case, step, index, exc) from exc


def validate_saved_result(result: object) -> None:
    if result is None or isinstance(result, _ALLOWED_RESULT_TYPES):
        return
    if isinstance(result, list):
        for item in result:
            validate_saved_result(item)
        return
    if isinstance(result, dict):
        for key, value in result.items():
            if not isinstance(key, str):
                raise TypeError(
                    "Unsupported action result key type for save_as: "
                    f"{type(key).__name__}"
                )
            validate_saved_result(value)
        return
    raise TypeError(
        "Unsupported action result type for save_as: "
        f"{type(result).__name__}"
    )
