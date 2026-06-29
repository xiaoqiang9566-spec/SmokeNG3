from __future__ import annotations

import argparse
import json
from typing import Any

from watch_ui_automation import __version__
from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.config import load_project_config
from watch_ui_automation.device.controller import SdsDeviceController
from watch_ui_automation.diagnostics.gesture_sweep import (
    GestureDefinition,
    build_variant_gestures,
    default_gesture_definitions,
    run_probe,
    write_probe_result,
)
from watch_ui_automation.models import RunManifest
from watch_ui_automation.transport.client import SdsTransportClient


class SweepDeviceAdapter:
    def __init__(self, device: SdsDeviceController, transport_records: list[dict[str, object]]) -> None:
        self.device = device
        self.transport_records = transport_records
        self.transport_entries: list[dict[str, object]] = []

    def read_json(self, uri: str, body: Any | None = None) -> Any:
        return self.device.read_json(uri, body=body)

    def perform_touch_events(self, events) -> None:
        start = len(self.transport_records)
        for event in events:
            self.device._touch(  # noqa: SLF001
                event.x,
                event.y,
                {
                    "touchdown": 1,
                    "touchmove": 2,
                    "liftoff": 3,
                    "drag_start": 5,
                    "click": 6,
                    "flick": 8,
                    "idle": 99,
                }[event.event_type],
                velocity_x=event.velocity_x,
                velocity_y=event.velocity_y,
            )
        self.transport_entries = list(self.transport_records[start:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gesture sweep probes against a real watch.")
    parser.add_argument("--device-config", default="configs/default.yaml")
    parser.add_argument(
        "--actions",
        nargs="+",
        default=["swipe_up", "swipe_down", "swipe_left", "swipe_right"],
    )
    parser.add_argument("--profiles", nargs="+", default=["baseline", "drag_start", "multi_move", "flick_like"])
    parser.add_argument("--variants", nargs="+", default=["default", "long", "edge_start", "dense_multi_move"])
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_project_config(args.device_config)
    writer = ArtifactWriter(config.artifacts.root_dir)
    writer.start_run(
        RunManifest(
            device_serial=config.device.serial,
            sds_url=config.device.sds_url,
            selected_tests=["gesture-sweep"],
            framework_version=__version__,
        )
    )

    transport_records: list[dict[str, object]] = []
    transport = SdsTransportClient(config.device.sds_url, recorder=transport_records.append)
    device = SdsDeviceController(
        serial=config.device.serial,
        transport=transport,
        resources=config.resources,
        input_profile=config.input,
        navigation=config.navigation,
    )
    adapter = SweepDeviceAdapter(device, transport_records)
    definitions = default_gesture_definitions(config)
    summary: list[dict[str, object]] = []

    try:
        device.assert_connected()
        for action_name in args.actions:
            base_gesture = definitions[action_name]
            variants = build_variant_gestures(base_gesture)
            for variant_name in args.variants:
                gesture = variants[variant_name]
                for profile_name in args.profiles:
                    result = run_probe(
                        device=adapter,
                        gesture=GestureDefinition(
                            action_name=f"{gesture.action_name}-{variant_name}",
                            start_x=gesture.start_x,
                            start_y=gesture.start_y,
                            end_x=gesture.end_x,
                            end_y=gesture.end_y,
                            midpoints=gesture.midpoints,
                        ),
                        profile_name=profile_name,
                        current_page_uri=config.resources.current_page_uri,
                        current_widget_uri=config.resources.current_widget_uri,
                        workout_state_uri=config.resources.workout_state_uri,
                        samples=args.samples,
                        baseline_actions=list(config.navigation.recover_baseline),
                        expected_page="main",
                        delay_seconds=args.delay,
                    )
                    path = write_probe_result(writer, result)
                    summary.append(
                        {
                            "probe_id": result.probe_id,
                            "changed_any": result.changed_any,
                            "result_file": str(path),
                        }
                    )
                    print(
                        json.dumps(
                            {
                                "probe_id": result.probe_id,
                                "changed_page": result.changed_page,
                                "changed_widget_path": result.changed_widget_path,
                                "changed_workout_state": result.changed_workout_state,
                                "changed_any": result.changed_any,
                            },
                            ensure_ascii=False,
                        )
                    )
    finally:
        device.release_bypasses()
        transport.close()

    if writer.run_dir is not None:
        summary_path = writer.run_dir / "gesture-sweep" / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
