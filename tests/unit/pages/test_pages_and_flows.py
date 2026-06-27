from watch_ui_automation.dsl.watch import WatchDsl


class FakeSession:
    def __init__(self) -> None:
        self.calls = []
        self.values = {
            "page://current": {"Content": "Watchface"},
            "widget://current": {"Content": "Weather"},
            "workout://state": {"Content": "ready"},
        }
        self.settings_focus_sequence = [
            "{ id:1, classes:0x600 }{ id:2, classes:0x608 }{ id:3, classes:0x600 }",
            "{ id:1, classes:0x608 }{ id:2, classes:0x600 }{ id:3, classes:0x600 }",
            "{ id:1, classes:0x600 }{ id:2, classes:0x608 }{ id:3, classes:0x600 }",
            "{ id:1, classes:0x608 }{ id:2, classes:0x600 }{ id:3, classes:0x600 }",
        ]
        self.settings_focus_index = 0

    def read_json(self, uri: str, body=None):
        if uri == "settings://focus":
            return {"Content": self.settings_focus_sequence[self.settings_focus_index]}
        return self.values[uri]

    def perform_action(self, action_name: str) -> None:
        self.calls.append(("action", action_name))
        if action_name in {"rotate_knob_up", "rotate_knob_down"}:
            self.settings_focus_index = min(
                self.settings_focus_index + 1,
                len(self.settings_focus_sequence) - 1,
            )

    def perform_actions(self, actions: list[str]) -> None:
        self.calls.append(tuple(actions))

    def open_view(self, view_name: str) -> None:
        self.calls.append(("open_view", view_name))

    def close_view(self, view_name: str) -> None:
        self.calls.append(("close_view", view_name))

    def record_step(self, case_name: str, name: str, status: str, **extra) -> None:
        self.calls.append((case_name, name, status, extra))


def test_watch_dsl_exposes_pages_and_flows() -> None:
    session = FakeSession()
    resources = {
        "current_page": "page://current",
        "current_widget": "widget://current",
        "workout_state": "workout://state",
        "settings_focus": "settings://focus",
    }
    session.values["page://current"] = {"Content": "main"}
    navigation = {
        "open_settings": ["press_middle"],
        "open_widget": ["swipe_up"],
        "open_workout": ["press_top"],
        "go_back": ["press_bottom_left"],
        "workout_pause_resume": ["press_top"],
    }
    watch = WatchDsl(
        session=session,
        resources=resources,
        navigation=navigation,
    )

    assert watch.session is session
    assert watch.resources == resources
    assert watch.navigation == navigation
    assert watch.watchface.is_visible() is True
    assert watch.settings.focused_item() == "0x600|0x608|0x600"
    assert watch.widget.current_name() == "Weather"
    assert watch.workout.state() == "ready"

    watch.flows.open_settings_and_return("case_settings")
    watch.flows.open_widget_and_return("case_widget")
    watch.flows.start_pause_resume_stop_workout("case_workout")

    assert ("open_view", "s-main") in session.calls
    assert ("close_view", "s-main") in session.calls
    assert ("swipe_up",) in session.calls
    assert ("press_bottom_left",) in session.calls
    assert ("press_top",) in session.calls


def test_settings_traverse_focus_sequence_records_each_step() -> None:
    session = FakeSession()
    resources = {
        "current_page": "page://current",
        "current_widget": "widget://current",
        "workout_state": "workout://state",
        "settings_focus": "settings://focus",
    }
    session.values["page://current"] = {"Content": "main"}
    navigation = {
        "open_settings": ["press_middle"],
        "open_widget": ["swipe_up"],
        "open_workout": ["press_top"],
        "go_back": ["press_bottom_left"],
        "workout_pause_resume": ["press_top"],
    }
    watch = WatchDsl(
        session=session,
        resources=resources,
        navigation=navigation,
    )

    focus_sequence = watch.flows.traverse_settings("case_settings", steps=3)

    assert focus_sequence == [
        "0x600|0x608|0x600",
        "0x608|0x600|0x600",
        "0x600|0x608|0x600",
        "0x608|0x600|0x600",
    ]
    assert ("open_view", "s-main") in session.calls
    assert ("close_view", "s-main") in session.calls
    assert ("action", "rotate_knob_down") in session.calls
    assert (
        "case_settings",
        "settings_traverse_step",
        "running",
        {"index": 0, "action": "rotate_knob_down"},
    ) in session.calls


def test_settings_focus_signature_ignores_ext_classes_noise() -> None:
    session = FakeSession()
    resources = {
        "current_page": "page://current",
        "current_widget": "widget://current",
        "workout_state": "workout://state",
        "settings_focus": "settings://focus",
    }
    navigation = {
        "open_settings": ["press_middle"],
        "open_widget": ["swipe_up"],
        "open_workout": ["press_top"],
        "go_back": ["press_bottom_left"],
        "workout_pause_resume": ["press_top"],
    }
    session.settings_focus_sequence = [
        "{ id:3085301168, classes:0x600, ext-classes:0x0 }"
        "{ id:2250289567, classes:0x608, ext-classes:0x0 }"
        "{ id:3935339417, classes:0x600, ext-classes:0x0 }"
    ]
    watch = WatchDsl(
        session=session,
        resources=resources,
        navigation=navigation,
    )

    assert watch.settings.focused_item() == "0x600|0x608|0x600"


def test_open_settings_views_and_return_visits_each_named_view() -> None:
    session = FakeSession()
    resources = {
        "current_page": "page://current",
        "current_widget": "widget://current",
        "workout_state": "workout://state",
        "settings_focus": "settings://focus",
    }
    navigation = {
        "open_settings": ["press_middle"],
        "open_widget": ["swipe_up"],
        "open_workout": ["press_top"],
        "go_back": ["press_bottom_left"],
        "workout_pause_resume": ["press_top"],
    }
    watch = WatchDsl(
        session=session,
        resources=resources,
        navigation=navigation,
    )

    watch.flows.open_settings_views_and_return(
        "case_settings_views",
        view_names=["s-main", "s-ge", "s-cu"],
    )

    assert ("open_view", "s-main") in session.calls
    assert ("open_view", "s-ge") in session.calls
    assert ("open_view", "s-cu") in session.calls
    assert ("close_view", "s-main") in session.calls
    assert ("close_view", "s-ge") in session.calls
    assert ("close_view", "s-cu") in session.calls
