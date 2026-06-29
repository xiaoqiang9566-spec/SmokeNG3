from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any

from watch_ui_automation.config import InputConfig, NavigationConfig, ResourceConfig
from watch_ui_automation.transport import SdsRequest, SdsTransportClient

CONNECTED_DEVICES_URI = "suunto://SDS/ConnectedDevices"
BYPASS_ROUTER_URI = "suunto://SDS/BypassRouter"
DEVICE_TIME_URI_TEMPLATE = "suunto://{serial}/Dev/Time"
BUTTON_URI_TEMPLATE = "suunto://{serial}/Ui/Test/SimulatedButtonPress"
OPEN_VIEW_URI_TEMPLATE = "suunto://{serial}/Ui/Control/Open"
CLOSE_VIEW_URI_TEMPLATE = "suunto://{serial}/Ui/Control/Close"
TOUCH_URI_TEMPLATE = "suunto://{serial}/Device/UserInteraction/Touch/Event"
KNOB_URI_TEMPLATE = "suunto://{serial}/Device/UserInteraction/Knob/Event"
TOUCH_BYPASS_PATH = "/Device/UserInteraction/Touch/Event"
KNOB_BYPASS_PATH = "/Device/UserInteraction/Knob/Event"

BUTTON_TOP = 0
BUTTON_MIDDLE = 1
BUTTON_BOTTOM = 2
BUTTON_TOP_LEFT = 3
BUTTON_BOTTOM_LEFT = 4

TOUCHDOWN = 1
TOUCHMOVE = 2
LIFTOFF = 3
DRAG_START = 5
CLICK = 6
FLICK = 8
IDLE = 99
VERIFIED_TOUCH_EVENT_DELAY_SECONDS = 0.05


class SdsDeviceController:
    def __init__(
        self,
        serial: str,
        transport: SdsTransportClient,
        resources: ResourceConfig,
        input_profile: InputConfig,
        navigation: NavigationConfig,
    ) -> None:
        self.serial = serial
        self.transport = transport
        self.resources = resources
        self.input_profile = input_profile
        self.navigation = navigation
        self._active_bypasses: set[str] = set()

    def assert_connected(self) -> None:
        response = self._send_checked(
            SdsRequest(method="GET", uri=CONNECTED_DEVICES_URI),
            "ConnectedDevices",
        )
        devices = self._extract_connected_devices(response.body)
        if self.serial not in devices:
            raise AssertionError(f"device not connected: {self.serial}")

    def read_json(self, uri: str, body: Any | None = None) -> Any:
        response = self._send_checked(
            SdsRequest(method="GET", uri=uri, body={} if body is None else body),
            uri,
        )
        return response.body

    def open_view(self, view_name: str) -> None:
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=OPEN_VIEW_URI_TEMPLATE.format(serial=self.serial),
                body={"name": view_name},
            ),
            "Ui/Control/Open",
        )

    def close_view(self, view_name: str) -> None:
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=CLOSE_VIEW_URI_TEMPLATE.format(serial=self.serial),
                body={"name": view_name},
            ),
            "Ui/Control/Close",
        )

    def press_top(self, duration: float = 0.8) -> None:
        self._press_button(BUTTON_TOP, duration)

    def press_middle(self, duration: float = 0.8) -> None:
        self._press_button(BUTTON_MIDDLE, duration)

    def press_bottom(self, duration: float = 0.8) -> None:
        self._press_button(BUTTON_BOTTOM, duration)

    def press_top_left(self, duration: float = 0.8) -> None:
        self._press_button(BUTTON_TOP_LEFT, duration)

    def press_bottom_left(self, duration: float = 0.8) -> None:
        self._press_button(BUTTON_BOTTOM_LEFT, duration)

    def tap_center(self) -> None:
        self._touch_sequence(
            [
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, 0.0, 0.0, TOUCHDOWN),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, 0.0, 0.0, LIFTOFF),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, 0.0, 0.0, CLICK),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, 0.0, 0.0, IDLE),
            ]
        )

    def swipe_left(self) -> None:
        self._touch_sequence(
            [
                (350, 149, 0.0, 0.0, TOUCHDOWN),
                (350, 149, -66.66666412353516, 0.0, TOUCHMOVE),
                (214, 148, 0.0, 0.0, DRAG_START),
                (187, 148, -1089.8284912109375, -5.714285850524902, TOUCHMOVE),
                (3, 147, -1882.64111328125, -6.948571681976318, LIFTOFF),
                (3, 147, -1882.64111328125, -6.948571681976318, FLICK),
                (0, 0, 0.0, 0.0, IDLE),
            ],
            inter_event_delay_seconds=VERIFIED_TOUCH_EVENT_DELAY_SECONDS,
        )

    def swipe_right(self) -> None:
        self._touch_sequence(
            [
                (self.input_profile.swipe_left_end_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, TOUCHDOWN),
                (self.input_profile.swipe_left_start_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, TOUCHMOVE),
                (self.input_profile.swipe_left_start_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, LIFTOFF),
                (self.input_profile.swipe_left_start_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, IDLE),
            ]
        )

    def swipe_up(self) -> None:
        self._touch_sequence(
            [
                (101, 350, 0.0, 0.0, TOUCHDOWN),
                (101, 350, 34.782604217529297, -139.13041687011719, TOUCHMOVE),
                (138, 350, 0.0, 0.0, DRAG_START),
                (143, 350, 102.95651245117188, -352.0, TOUCHMOVE),
                (148, 116, 69.60235595703125, -349.12554931640625, TOUCHMOVE),
                (154, 116, 53.57699203491211, -214.89886474609375, TOUCHMOVE),
                (154, 116, 6.943579196929932, -357.33355712890625, TOUCHMOVE),
                (154, 116, 0.8998879790306091, -371.17999267578125, TOUCHMOVE),
                (154, 116, 0.11662549525499344, -314.7567443847656, TOUCHMOVE),
                (154, 116, 0.015114667825400829, -402.7499084472656, TOUCHMOVE),
                (154, 116, 0.0019588612485677004, -364.00244140625, TOUCHMOVE),
                (154, 116, 0.0019588612485677004, -364.00244140625, LIFTOFF),
                (154, 116, 0.0019588612485677004, -364.00244140625, FLICK),
                (0, 0, 0.0, 0.0, IDLE),
            ],
            inter_event_delay_seconds=VERIFIED_TOUCH_EVENT_DELAY_SECONDS,
        )

    def swipe_down(self) -> None:
        self._touch_sequence(
            [
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_end_y, 0.0, 0.0, TOUCHDOWN),
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_start_y, 0.0, 0.0, TOUCHMOVE),
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_start_y, 0.0, 0.0, LIFTOFF),
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_start_y, 0.0, 0.0, IDLE),
            ]
        )

    def rotate_knob_up(self, angle: int = 15) -> None:
        self._ensure_bypass(KNOB_BYPASS_PATH)
        timestamp = self._read_timestamp()
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=KNOB_URI_TEMPLATE.format(serial=self.serial),
                body={"": {"angle": angle, "timestamp": timestamp}},
            ),
            "Knob/Event",
        )

    def rotate_knob_down(self, angle: int = -15) -> None:
        self.rotate_knob_up(angle=angle)

    def perform_action(self, action_name: str) -> None:
        getattr(self, action_name)()

    def perform_actions(self, actions: Sequence[str]) -> None:
        for action_name in actions:
            self.perform_action(action_name)

    def release_bypasses(self) -> None:
        response = self.transport.send_and_wait(
            SdsRequest(
                method="DEL",
                uri=f"{BYPASS_ROUTER_URI}/{self.serial}",
                body={},
            )
        )
        if response.status not in {200, 204, 404}:
            raise RuntimeError(f"BypassRouter request failed with status {response.status}")
        self._active_bypasses.clear()

    def _press_button(self, button_id: int, duration: float) -> None:
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=BUTTON_URI_TEMPLATE.format(serial=self.serial),
                body={"value": {"id": button_id, "duration": duration}},
            ),
            "SimulatedButtonPress",
        )

    def _touch(
        self,
        x: int,
        y: int,
        event_type: int,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
    ) -> None:
        self._ensure_bypass(TOUCH_BYPASS_PATH)
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=TOUCH_URI_TEMPLATE.format(serial=self.serial),
                body={
                    "": {
                        "x": x,
                        "y": y,
                        "data": {"x": velocity_x, "y": velocity_y},
                        "type": event_type,
                    }
                },
            ),
            "Touch/Event",
        )

    def _ensure_bypass(self, resource_path: str) -> None:
        if resource_path in self._active_bypasses:
            return
        self._send_checked(
            SdsRequest(
                method="POST",
                uri=BYPASS_ROUTER_URI,
                body={
                    "serial": self.serial,
                    "pathToBypass": resource_path,
                },
            ),
            "BypassRouter",
        )
        self._active_bypasses.add(resource_path)

    def _touch_sequence(
        self,
        events: Sequence[tuple[int, int, float, float, int]],
        inter_event_delay_seconds: float = 0.0,
    ) -> None:
        for x, y, velocity_x, velocity_y, event_type in events:
            self._touch(x, y, event_type, velocity_x, velocity_y)
            if inter_event_delay_seconds > 0:
                time.sleep(inter_event_delay_seconds)

    def _read_timestamp(self) -> int:
        payload = self.read_json(DEVICE_TIME_URI_TEMPLATE.format(serial=self.serial))
        if isinstance(payload, Mapping):
            if "Content" in payload:
                return int(payload["Content"])
            if "timestamp" in payload:
                return int(payload["timestamp"])
            if "Timestamp" in payload:
                return int(payload["Timestamp"])
        raise ValueError(f"unexpected Dev/Time payload: {payload!r}")

    def _send_checked(self, request: SdsRequest, label: str):
        response = self.transport.send_and_wait(request)
        if response.status >= 400:
            raise RuntimeError(f"{label} request failed with status {response.status}")
        return response

    def _extract_connected_devices(self, payload: Any) -> list[str]:
        if not isinstance(payload, Mapping):
            raise ValueError("ConnectedDevices payload must be a mapping")
        devices = payload.get("Devices", [])
        if isinstance(devices, (str, bytes)) or not isinstance(devices, Sequence):
            raise ValueError("ConnectedDevices Devices must be a sequence of strings")
        normalized_devices: list[str] = []
        for device in devices:
            if not isinstance(device, str):
                raise ValueError("ConnectedDevices Devices must be a sequence of strings")
            normalized_devices.append(device)
        return normalized_devices


DeviceController = SdsDeviceController
