from __future__ import annotations

from watch_ui_automation.pages.base import BasePage


class WorkoutPage(BasePage):
    def state(self) -> str:
        return str(self._read_content("workout_state"))

    def pause_or_resume(self, case_name: str) -> None:
        self.session.record_step(case_name, "workout_pause_resume", "running")
        self.session.perform_actions(self.navigation["workout_pause_resume"])

    def stop(self, case_name: str) -> None:
        self.session.record_step(case_name, "workout_stop", "running")
        self.session.perform_actions(self.navigation["go_back"])
