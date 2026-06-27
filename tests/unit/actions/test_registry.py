import pytest

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.errors import ScenarioActionError


def test_registry_registers_and_calls_action() -> None:
    registry = ActionRegistry()

    def sample_action(ctx, *, value: int) -> int:
        return value + 1

    registry.register("sample.increment", sample_action)

    assert "sample.increment" in registry
    assert registry.call("sample.increment", object(), value=2) == 3


def test_registry_rejects_duplicate_action_names() -> None:
    registry = ActionRegistry()

    registry.register("sample.action", lambda ctx: None)

    with pytest.raises(ScenarioActionError, match="Duplicate action"):
        registry.register("sample.action", lambda ctx: None)


def test_registry_rejects_unknown_action_calls() -> None:
    registry = ActionRegistry()

    with pytest.raises(ScenarioActionError, match="Unknown action"):
        registry.call("missing.action", object())
