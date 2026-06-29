from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from watch_ui_automation.artifacts.writer import ArtifactWriter

_EVENT_TYPE_CODES = {
    "touchdown": 1,
    "touchmove": 2,
    "liftoff": 3,
    "drag_start": 5,
    "click": 6,
    "flick": 8,
    "idle": 99,
}


@dataclass(frozen=True)
class TouchEvent:
    x: int
    y: int
    event_type: str
    velocity_x: float = 0.0
    velocity_y: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "x": self.x,
            "y": self.y,
            "data": {"x": self.velocity_x, "y": self.velocity_y},
            "type": _EVENT_TYPE_CODES[self.event_type],
            "event_type": self.event_type,
        }


@dataclass(frozen=True)
class GestureDefinition:
    action_name: str
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    midpoints: list[tuple[int, int]]


@dataclass(frozen=True)
class ProbeStateSample:
    sample_index: int
    current_page: str
    current_widget_path: str
    workout_state: str


@dataclass(frozen=True)
class GestureProbeResult:
    probe_id: str
    action_name: str
    profile_name: str
    before_state: ProbeStateSample
    after_samples: list[ProbeStateSample]
    touch_events: list[TouchEvent]
    transport_entries: list[dict[str, object]]
    changed_page: bool
    changed_widget_path: bool
    changed_workout_state: bool
    changed_any: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "action_name": self.action_name,
            "profile_name": self.profile_name,
            "before_state": asdict(self.before_state),
            "after_samples": [asdict(sample) for sample in self.after_samples],
            "touch_events": [event.to_dict() for event in self.touch_events],
            "transport_entries": self.transport_entries,
            "changed_page": self.changed_page,
            "changed_widget_path": self.changed_widget_path,
            "changed_workout_state": self.changed_workout_state,
            "changed_any": self.changed_any,
        }


def default_gesture_definitions(config: Any) -> dict[str, GestureDefinition]:
    return {
        "swipe_up": GestureDefinition(
            action_name="swipe_up",
            start_x=config.input.swipe_up_x,
            start_y=config.input.swipe_up_start_y,
            end_x=config.input.swipe_up_x,
            end_y=config.input.swipe_up_end_y,
            midpoints=[
                (
                    config.input.swipe_up_x,
                    int((config.input.swipe_up_start_y + config.input.swipe_up_end_y) / 2),
                )
            ],
        ),
        "swipe_down": GestureDefinition(
            action_name="swipe_down",
            start_x=config.input.swipe_up_x,
            start_y=config.input.swipe_up_end_y,
            end_x=config.input.swipe_up_x,
            end_y=config.input.swipe_up_start_y,
            midpoints=[
                (
                    config.input.swipe_up_x,
                    int((config.input.swipe_up_start_y + config.input.swipe_up_end_y) / 2),
                )
            ],
        ),
        "swipe_left": GestureDefinition(
            action_name="swipe_left",
            start_x=config.input.swipe_left_start_x,
            start_y=config.input.swipe_horizontal_y,
            end_x=config.input.swipe_left_end_x,
            end_y=config.input.swipe_horizontal_y,
            midpoints=[
                (
                    int((config.input.swipe_left_start_x + config.input.swipe_left_end_x) / 2),
                    config.input.swipe_horizontal_y,
                )
            ],
        ),
        "swipe_right": GestureDefinition(
            action_name="swipe_right",
            start_x=config.input.swipe_left_end_x,
            start_y=config.input.swipe_horizontal_y,
            end_x=config.input.swipe_left_start_x,
            end_y=config.input.swipe_horizontal_y,
            midpoints=[
                (
                    int((config.input.swipe_left_start_x + config.input.swipe_left_end_x) / 2),
                    config.input.swipe_horizontal_y,
                )
            ],
        ),
    }


def build_variant_gestures(base_gesture: GestureDefinition) -> dict[str, GestureDefinition]:
    horizontal = base_gesture.start_y == base_gesture.end_y
    vertical = base_gesture.start_x == base_gesture.end_x

    long_gesture = base_gesture
    edge_gesture = base_gesture
    dense_midpoints = list(base_gesture.midpoints)

    if vertical:
        direction = 1 if base_gesture.start_y < base_gesture.end_y else -1
        long_gesture = GestureDefinition(
            action_name=base_gesture.action_name,
            start_x=base_gesture.start_x,
            start_y=base_gesture.start_y - (40 * direction),
            end_x=base_gesture.end_x,
            end_y=base_gesture.end_y + (40 * direction),
            midpoints=[
                (base_gesture.start_x, int((base_gesture.start_y + base_gesture.end_y) / 2))
            ],
        )
        edge_gesture = GestureDefinition(
            action_name=base_gesture.action_name,
            start_x=40 if base_gesture.start_x > 120 else 420,
            start_y=base_gesture.start_y,
            end_x=40 if base_gesture.end_x > 120 else 420,
            end_y=base_gesture.end_y,
            midpoints=list(base_gesture.midpoints),
        )
        dense_midpoints = [
            (base_gesture.start_x, int(base_gesture.start_y + ((base_gesture.end_y - base_gesture.start_y) * ratio)))
            for ratio in (0.25, 0.5, 0.75)
        ]
    elif horizontal:
        direction = 1 if base_gesture.start_x < base_gesture.end_x else -1
        long_gesture = GestureDefinition(
            action_name=base_gesture.action_name,
            start_x=base_gesture.start_x - (40 * direction),
            start_y=base_gesture.start_y,
            end_x=base_gesture.end_x + (40 * direction),
            end_y=base_gesture.end_y,
            midpoints=[
                (int((base_gesture.start_x + base_gesture.end_x) / 2), base_gesture.start_y)
            ],
        )
        edge_gesture = GestureDefinition(
            action_name=base_gesture.action_name,
            start_x=base_gesture.start_x,
            start_y=40 if base_gesture.start_y > 120 else 420,
            end_x=base_gesture.end_x,
            end_y=40 if base_gesture.end_y > 120 else 420,
            midpoints=list(base_gesture.midpoints),
        )
        dense_midpoints = [
            (int(base_gesture.start_x + ((base_gesture.end_x - base_gesture.start_x) * ratio)), base_gesture.start_y)
            for ratio in (0.25, 0.5, 0.75)
        ]

    return {
        "default": base_gesture,
        "long": long_gesture,
        "edge_start": edge_gesture,
        "dense_multi_move": GestureDefinition(
            action_name=base_gesture.action_name,
            start_x=base_gesture.start_x,
            start_y=base_gesture.start_y,
            end_x=base_gesture.end_x,
            end_y=base_gesture.end_y,
            midpoints=dense_midpoints,
        ),
    }


def build_touch_events(
    gesture: GestureDefinition,
    profile_name: str,
) -> list[TouchEvent]:
    if profile_name == "baseline":
        return [
            TouchEvent(gesture.start_x, gesture.start_y, "touchdown"),
            TouchEvent(gesture.end_x, gesture.end_y, "touchmove"),
            TouchEvent(gesture.end_x, gesture.end_y, "liftoff"),
            TouchEvent(gesture.end_x, gesture.end_y, "idle"),
        ]
    if profile_name == "drag_start":
        return [
            TouchEvent(gesture.start_x, gesture.start_y, "touchdown"),
            TouchEvent(gesture.start_x, gesture.start_y, "drag_start"),
            TouchEvent(gesture.end_x, gesture.end_y, "touchmove"),
            TouchEvent(gesture.end_x, gesture.end_y, "liftoff"),
            TouchEvent(gesture.end_x, gesture.end_y, "idle"),
        ]
    if profile_name == "multi_move":
        moves = [TouchEvent(x, y, "touchmove") for x, y in gesture.midpoints]
        return [
            TouchEvent(gesture.start_x, gesture.start_y, "touchdown"),
            *moves,
            TouchEvent(gesture.end_x, gesture.end_y, "touchmove"),
            TouchEvent(gesture.end_x, gesture.end_y, "liftoff"),
            TouchEvent(gesture.end_x, gesture.end_y, "idle"),
        ]
    if profile_name == "flick_like":
        return [
            TouchEvent(gesture.start_x, gesture.start_y, "touchdown"),
            TouchEvent(
                gesture.end_x,
                gesture.end_y,
                "touchmove",
                velocity_x=float(gesture.end_x - gesture.start_x),
                velocity_y=float(gesture.end_y - gesture.start_y),
            ),
            TouchEvent(
                gesture.end_x,
                gesture.end_y,
                "flick",
                velocity_x=float(gesture.end_x - gesture.start_x),
                velocity_y=float(gesture.end_y - gesture.start_y),
            ),
            TouchEvent(gesture.end_x, gesture.end_y, "liftoff"),
            TouchEvent(gesture.end_x, gesture.end_y, "idle"),
        ]
    raise ValueError(f"unsupported profile: {profile_name}")


def run_probe(
    *,
    device: Any,
    gesture: GestureDefinition,
    profile_name: str,
    current_page_uri: str,
    current_widget_uri: str,
    workout_state_uri: str,
    samples: int,
    baseline_actions: list[str] | None = None,
    expected_page: str = "main",
    delay_seconds: float = 0.0,
) -> GestureProbeResult:
    current_page = str(device.read_json(current_page_uri).get("Content"))
    if current_page != expected_page and baseline_actions:
        device.perform_actions(baseline_actions)
        for _ in range(10):
            current_page = str(device.read_json(current_page_uri).get("Content"))
            if current_page == expected_page:
                break
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    before_state = ProbeStateSample(
        sample_index=-1,
        current_page=str(device.read_json(current_page_uri).get("Content")),
        current_widget_path=str(device.read_json(current_widget_uri).get("Content")),
        workout_state=str(device.read_json(workout_state_uri).get("Content")),
    )
    touch_events = build_touch_events(gesture, profile_name)
    device.perform_touch_events(touch_events)

    after_samples: list[ProbeStateSample] = []
    for sample_index in range(samples):
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        after_samples.append(
            ProbeStateSample(
                sample_index=sample_index,
                current_page=str(device.read_json(current_page_uri).get("Content")),
                current_widget_path=str(device.read_json(current_widget_uri).get("Content")),
                workout_state=str(device.read_json(workout_state_uri).get("Content")),
            )
        )

    final_sample = after_samples[-1] if after_samples else before_state
    changed_page = final_sample.current_page != before_state.current_page
    changed_widget_path = (
        final_sample.current_widget_path != before_state.current_widget_path
    )
    changed_workout_state = final_sample.workout_state != before_state.workout_state
    return GestureProbeResult(
        probe_id=f"{gesture.action_name}-{profile_name}",
        action_name=gesture.action_name,
        profile_name=profile_name,
        before_state=before_state,
        after_samples=after_samples,
        touch_events=touch_events,
        transport_entries=list(getattr(device, "transport_entries", [])),
        changed_page=changed_page,
        changed_widget_path=changed_widget_path,
        changed_workout_state=changed_workout_state,
        changed_any=changed_page or changed_widget_path or changed_workout_state,
    )


def write_probe_result(writer: ArtifactWriter, result: GestureProbeResult) -> Path:
    if writer.run_dir is None:
        raise RuntimeError("writer.start_run() must be called before writing probe results")
    output_dir = writer.run_dir / "gesture-sweep" / "probes"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.probe_id}.json"
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
