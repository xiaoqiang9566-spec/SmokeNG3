from __future__ import annotations

import re

from watch_ui_automation.pages.base import BasePage

_FOCUSED_CLASS_RE = re.compile(r"(?<!ext-)classes:(0x[0-9a-fA-F]+)")


class SettingsPage(BasePage):
    def focused_item(self) -> str:
        payload = self.session.read_json(
            self.resources["settings_focus"],
            body={"select": ".list"},
        )
        raw_content = str(payload.get("Content", ""))
        signatures = _FOCUSED_CLASS_RE.findall(raw_content)
        if signatures:
            return "|".join(signatures[:3])
        return raw_content

    def traverse_focus(
        self,
        case_name: str,
        *,
        steps: int,
        action_name: str = "rotate_knob_down",
    ) -> list[str]:
        focused_items = [self.focused_item()]
        for index in range(steps):
            self.session.record_step(
                case_name,
                "settings_traverse_step",
                "running",
                index=index,
                action=action_name,
            )
            self.session.perform_action(action_name)
            focused_items.append(self.focused_item())
        return focused_items

    def open_root(self, case_name: str, view_name: str = "s-main") -> None:
        self.open_view(case_name, view_name=view_name)

    def open_view(self, case_name: str, view_name: str) -> None:
        self.session.record_step(
            case_name,
            "open_settings",
            "running",
            view_name=view_name,
        )
        self.session.open_view(view_name)

    def go_back(self, case_name: str) -> None:
        self.close_view(case_name, view_name="s-main")

    def close_view(self, case_name: str, view_name: str) -> None:
        self.session.record_step(
            case_name,
            "settings_back",
            "running",
            view_name=view_name,
        )
        self.session.close_view(view_name)
