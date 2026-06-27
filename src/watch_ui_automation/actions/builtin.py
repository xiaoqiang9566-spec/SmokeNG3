from __future__ import annotations

from watch_ui_automation.actions.assertion_actions import register_assertion_actions
from watch_ui_automation.actions.capture_actions import register_capture_actions
from watch_ui_automation.actions.navigation_actions import register_navigation_actions
from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.actions.workout_actions import register_workout_actions


def create_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    register_navigation_actions(registry)
    register_capture_actions(registry)
    register_assertion_actions(registry)
    register_workout_actions(registry)
    return registry
