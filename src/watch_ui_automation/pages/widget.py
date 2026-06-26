from __future__ import annotations

from watch_ui_automation.pages.base import BasePage


class WidgetPage(BasePage):
    def current_name(self) -> str:
        return str(self._read_content("current_widget"))

    def go_back(self, case_name: str) -> None:
        self.session.record_step(case_name, "widget_back", "running")
        self.session.perform_actions(self.navigation["go_back"])
