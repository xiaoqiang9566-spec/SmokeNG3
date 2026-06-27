from __future__ import annotations

from watch_ui_automation.scenarios.models import ScenarioCase, ScenarioStep


class ScenarioError(Exception):
    pass


class ScenarioSchemaError(ScenarioError):
    pass


class ScenarioVariableError(ScenarioError):
    pass


class ScenarioActionError(ScenarioError):
    pass


class ScenarioStepError(ScenarioError):
    @classmethod
    def from_exception(
        cls,
        case: ScenarioCase,
        step: ScenarioStep,
        index: int,
        exc: BaseException,
    ) -> "ScenarioStepError":
        message = "\n".join(
            [
                "ScenarioStepError:",
                f"  file: {case.source_file}",
                f"  case: {case.id}",
                f"  step: {index} - {step.name}",
                f"  action: {step.action}",
                f"  params: {step.params}",
                f"  cause: {type(exc).__name__}: {exc}",
            ]
        )
        return cls(message)


class ScenarioStepAssertionError(AssertionError, ScenarioStepError):
    pass
