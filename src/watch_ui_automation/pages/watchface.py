from __future__ import annotations

from watch_ui_automation.pages.base import BasePage


class WatchfacePage(BasePage):
    def is_visible(self) -> bool:
        return str(self._read_content("current_page")) in {"c-lowp", "main"}

    def open_settings(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_settings", "running")
        self.session.perform_actions(self.navigation["open_settings"])

    def open_widget(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_widget", "running")
        self.session.perform_actions(self.navigation["open_widget"])

    def open_pinned_widget_shortcut(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_pinned_widget_shortcut", "running")
        self.session.perform_actions(self.navigation["open_pinned_widget_shortcut"])

    def open_workout(self, case_name: str) -> None:
        self.session.record_step(case_name, "open_workout", "running")
        self.session.perform_actions(self.navigation["open_workout"])
