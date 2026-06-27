from __future__ import annotations

from collections.abc import Callable
from typing import Any

from watch_ui_automation.scenarios.errors import ScenarioActionError

ActionCallable = Callable[..., object]


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionCallable] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    def register(self, name: str, action: ActionCallable) -> None:
        if name in self._actions:
            raise ScenarioActionError(f"Duplicate action '{name}'")
        self._actions[name] = action

    def get(self, name: str) -> ActionCallable:
        try:
            return self._actions[name]
        except KeyError as error:
            raise ScenarioActionError(f"Unknown action '{name}'") from error

    def call(self, name: str, ctx: Any, **params: object) -> object:
        return self.get(name)(ctx, **params)
