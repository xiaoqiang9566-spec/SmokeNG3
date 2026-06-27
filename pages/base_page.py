from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapabilityAction:
    name: str
    category: str
    payload: dict[str, Any]


class BasePage:
    module_name = "base"

    def __init__(self, input_capabilities: dict[str, Any]) -> None:
        self.input_capabilities = input_capabilities

    @property
    def buttons(self) -> dict[str, Any]:
        return dict(self.input_capabilities["buttons"])

    @property
    def gestures(self) -> dict[str, Any]:
        return dict(self.input_capabilities["gestures"])

    def button(self, name: str, *, duration_name: str = "short_press") -> CapabilityAction:
        button = self.buttons[name]
        duration = self.input_capabilities["durations"][duration_name]
        return CapabilityAction(
            name=name,
            category="button",
            payload={
                "button_id": button["button_id"],
                "duration": duration,
                "position": button["position"],
            },
        )

    def gesture(self, name: str) -> CapabilityAction:
        gesture = self.gestures[name]
        return CapabilityAction(
            name=name,
            category="gesture",
            payload=dict(gesture),
        )

    def available_actions(self) -> dict[str, list[str]]:
        return {
            "buttons": sorted(self.buttons),
            "gestures": sorted(self.gestures),
        }
