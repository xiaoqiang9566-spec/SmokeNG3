from __future__ import annotations

from typing import Any


class WatchFlows:
    def __init__(
        self,
        watchface: Any,
        settings: Any,
        widget: Any,
        workout: Any,
    ) -> None:
        self.watchface = watchface
        self.settings = settings
        self.widget = widget
        self.workout = workout

    def open_settings_and_return(self, case_name: str) -> None:
        self.settings.open_root(case_name)
        self.settings.go_back(case_name)

    def traverse_settings(self, case_name: str, *, steps: int) -> list[str]:
        self.settings.open_root(case_name)
        focus_sequence = self.settings.traverse_focus(case_name, steps=steps)
        self.settings.go_back(case_name)
        return focus_sequence

    def open_settings_views_and_return(
        self,
        case_name: str,
        *,
        view_names: list[str],
    ) -> None:
        for view_name in view_names:
            self.settings.open_view(case_name, view_name=view_name)
            self.settings.close_view(case_name, view_name=view_name)

    def open_widget_and_return(self, case_name: str) -> None:
        self.watchface.open_widget(case_name)
        self.widget.go_back(case_name)

    def start_pause_resume_stop_workout(self, case_name: str) -> None:
        self.watchface.open_workout(case_name)
        self.workout.pause_or_resume(case_name)
        self.workout.pause_or_resume(case_name)
        self.workout.stop(case_name)
