from __future__ import annotations

import json
from pathlib import Path

from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.diagnostics.gesture_sweep import (
    GestureDefinition,
    GestureProbeResult,
    ProbeStateSample,
    TouchEvent,
    build_touch_events,
    build_variant_gestures,
    default_gesture_definitions,
    run_probe,
    write_probe_result,
)
from watch_ui_automation.models import RunManifest
from watch_ui_automation.config import InputConfig


class FakeDevice:
    def __init__(self) -> None:
        self.actions: list[list[TouchEvent]] = []
        self.current_page = "main"
        self.current_widget = "/watch-face/main"
        self.workout_state = "0"
        self.transport_entries: list[dict[str, object]] = []
        self.recover_calls: list[str] = []
        self.pending_recovery_reads = 0

    def read_json(self, uri: str, body=None):
        if uri == "page://current":
            if self.pending_recovery_reads > 0:
                self.pending_recovery_reads -= 1
                if self.pending_recovery_reads == 0:
                    self.current_page = "main"
            return {"Content": self.current_page}
        if uri == "widget://current":
            return {"Content": self.current_widget}
        if uri == "workout://state":
            return {"Content": self.workout_state}
        raise KeyError(uri)

    def perform_touch_events(self, events: list[TouchEvent]) -> None:
        self.actions.append(events)
        self.transport_entries = [
            {
                "direction": "request",
                "payload": {
                    "Uri": "suunto://TEST/Device/UserInteraction/Touch/Event",
                    "Body": event.to_dict(),
                },
            }
            for event in events
        ]
        self.current_page = "widget-list"
        self.current_widget = "/widget/list"
        self.workout_state = "ready"

    def perform_actions(self, actions: list[str]) -> None:
        self.recover_calls.extend(actions)
        self.current_widget = "/watch-face/main"
        self.workout_state = "0"
        self.pending_recovery_reads = 2


class FakeCleanupDevice:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def release_bypasses(self) -> None:
        self.calls.append("release_bypasses")


def test_build_touch_events_for_multi_move_profile() -> None:
    gesture = GestureDefinition(
        action_name="swipe_up",
        start_x=233,
        start_y=360,
        end_x=233,
        end_y=120,
        midpoints=[(233, 280), (233, 200)],
    )

    events = build_touch_events(gesture, "multi_move")

    assert [event.event_type for event in events] == [
        "touchdown",
        "touchmove",
        "touchmove",
        "touchmove",
        "liftoff",
        "idle",
    ]
    assert [(event.x, event.y) for event in events] == [
        (233, 360),
        (233, 280),
        (233, 200),
        (233, 120),
        (233, 120),
        (233, 120),
    ]


def test_build_variant_gestures_adds_long_edge_and_dense_variants() -> None:
    base_gesture = GestureDefinition(
        action_name="swipe_up",
        start_x=233,
        start_y=360,
        end_x=233,
        end_y=120,
        midpoints=[(233, 240)],
    )

    variants = build_variant_gestures(base_gesture)

    assert set(variants) >= {
        "default",
        "long",
        "edge_start",
        "dense_multi_move",
    }
    assert variants["default"].start_x == 233
    assert variants["long"].start_y > base_gesture.start_y
    assert variants["long"].end_y < base_gesture.end_y
    assert variants["edge_start"].start_x != base_gesture.start_x
    assert len(variants["dense_multi_move"].midpoints) > len(base_gesture.midpoints)


def test_default_gesture_definitions_include_swipe_right() -> None:
    class FakeConfig:
        input = InputConfig(
            tap_center_x=233,
            tap_center_y=233,
            swipe_left_start_x=420,
            swipe_left_end_x=46,
            swipe_horizontal_y=233,
            swipe_up_x=233,
            swipe_up_start_y=360,
            swipe_up_end_y=120,
        )

    definitions = default_gesture_definitions(FakeConfig())

    assert definitions["swipe_right"] == GestureDefinition(
        action_name="swipe_right",
        start_x=46,
        start_y=233,
        end_x=420,
        end_y=233,
        midpoints=[(233, 233)],
    )


def test_run_probe_records_before_after_and_transport_entries() -> None:
    device = FakeDevice()
    gesture = GestureDefinition(
        action_name="swipe_up",
        start_x=233,
        start_y=360,
        end_x=233,
        end_y=120,
        midpoints=[(233, 240)],
    )

    result = run_probe(
        device=device,
        gesture=gesture,
        profile_name="baseline",
        current_page_uri="page://current",
        current_widget_uri="widget://current",
        workout_state_uri="workout://state",
        samples=2,
    )

    assert result.action_name == "swipe_up"
    assert result.profile_name == "baseline"
    assert result.before_state.current_page == "main"
    assert result.before_state.current_widget_path == "/watch-face/main"
    assert result.before_state.workout_state == "0"
    assert [sample.current_page for sample in result.after_samples] == [
        "widget-list",
        "widget-list",
    ]
    assert [sample.workout_state for sample in result.after_samples] == [
        "ready",
        "ready",
    ]
    assert result.changed_page is True
    assert result.changed_widget_path is True
    assert result.changed_workout_state is True
    assert result.changed_any is True
    assert len(result.transport_entries) == len(result.touch_events)
    assert device.recover_calls == []


def test_run_probe_recovers_expected_page_before_sampling() -> None:
    device = FakeDevice()
    device.current_page = "widg-ctrlp"
    device.current_widget = "/watch-face/main/widg-ctrlp"
    gesture = GestureDefinition(
        action_name="swipe_down",
        start_x=233,
        start_y=120,
        end_x=233,
        end_y=360,
        midpoints=[(233, 240)],
    )

    result = run_probe(
        device=device,
        gesture=gesture,
        profile_name="baseline",
        current_page_uri="page://current",
        current_widget_uri="widget://current",
        workout_state_uri="workout://state",
        baseline_actions=["press_bottom", "press_bottom"],
        expected_page="main",
        samples=1,
    )

    assert device.recover_calls == ["press_bottom", "press_bottom"]
    assert result.before_state.current_page == "main"
    assert result.before_state.current_widget_path == "/watch-face/main"


def test_run_probe_waits_for_recovered_page_before_before_state_snapshot() -> None:
    device = FakeDevice()
    device.current_page = "c-lowp"
    gesture = GestureDefinition(
        action_name="swipe_down",
        start_x=233,
        start_y=120,
        end_x=233,
        end_y=360,
        midpoints=[(233, 240)],
    )

    result = run_probe(
        device=device,
        gesture=gesture,
        profile_name="baseline",
        current_page_uri="page://current",
        current_widget_uri="widget://current",
        workout_state_uri="workout://state",
        baseline_actions=["press_bottom"],
        expected_page="main",
        samples=1,
    )

    assert result.before_state.current_page == "main"
    assert device.pending_recovery_reads == 0


def test_write_probe_result_creates_probe_json_under_gesture_sweep(tmp_path: Path) -> None:
    writer = ArtifactWriter(tmp_path)
    writer.start_run(
        RunManifest(
            device_serial="TEST123",
            sds_url="ws://localhost:65534",
            selected_tests=["gesture-sweep"],
            framework_version="0.1.0",
        )
    )
    result = GestureProbeResult(
        probe_id="swipe_up-baseline",
        action_name="swipe_up",
        profile_name="baseline",
        before_state=ProbeStateSample(
            sample_index=-1,
            current_page="main",
            current_widget_path="/watch-face/main",
            workout_state="0",
        ),
        after_samples=[
            ProbeStateSample(
                sample_index=0,
                current_page="widget-list",
                current_widget_path="/widget/list",
                workout_state="ready",
            )
        ],
        touch_events=[
            TouchEvent(x=233, y=360, event_type="touchdown"),
            TouchEvent(x=233, y=120, event_type="liftoff"),
        ],
        transport_entries=[],
        changed_page=True,
        changed_widget_path=True,
        changed_workout_state=True,
        changed_any=True,
    )

    path = write_probe_result(writer, result)

    assert "gesture-sweep" in str(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["probe_id"] == "swipe_up-baseline"
    assert payload["before_state"]["workout_state"] == "0"
    assert payload["changed_workout_state"] is True
    assert payload["changed_any"] is True


def test_gesture_sweep_cleanup_releases_bypasses_before_transport_close() -> None:
    device = FakeCleanupDevice()
    calls: list[str] = []

    device.release_bypasses()
    calls.append("transport_close")

    assert device.calls == ["release_bypasses"]
    assert calls == ["transport_close"]
