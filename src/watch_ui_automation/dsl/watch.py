from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from watch_ui_automation.flows.core import WatchFlows
from watch_ui_automation.pages.settings import SettingsPage
from watch_ui_automation.pages.watchface import WatchfacePage
from watch_ui_automation.pages.widget import WidgetPage
from watch_ui_automation.pages.workout import WorkoutPage


class WatchDsl:
    def __init__(
        self,
        session: Any,
        resources: Mapping[str, str],
        navigation: Mapping[str, Sequence[str]],
    ) -> None:
        self.session = session
        self.resources = dict(resources)
        self.navigation = {key: list(value) for key, value in navigation.items()}
        self.watchface = WatchfacePage(session, resources, navigation)
        self.settings = SettingsPage(session, resources, navigation)
        self.widget = WidgetPage(session, resources, navigation)
        self.workout = WorkoutPage(session, resources, navigation)
        self.flows = WatchFlows(
            self.watchface,
            self.settings,
            self.widget,
            self.workout,
        )
