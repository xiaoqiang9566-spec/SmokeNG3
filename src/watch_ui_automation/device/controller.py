from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from watch_ui_automation.config import InputConfig, NavigationConfig, ResourceConfig
from watch_ui_automation.transport import SdsRequest, SdsTransportClient

CONNECTED_DEVICES_URI = "suunto://SDS/ConnectedDevices"
DEVICE_TIME_URI_TEMPLATE = "suunto://{serial}/Dev/Time"
BUTTON_URI_TEMPLATE = "suunto://{serial}/Ui/Test/SimulatedButtonPress"
TOUCH_URI_TEMPLATE = "suunto://{serial}/Device/UserInteraction/Touch/Event"
KNOB_URI_TEMPLATE = "suunto://{serial}/Device/UserInteraction/Knob/Event"

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

    def assert_connected(self) -> None:
        response = self._send_checked(
            SdsRequest(method="GET", uri=CONNECTED_DEVICES_URI),
            "ConnectedDevices",
        )
        body = response.body if isinstance(response.body, Mapping) else {}
        devices = body.get("Devices", [])
        if self.serial not in devices:
            raise AssertionError(f"device not connected: {self.serial}")

    def read_json(self, uri: str) -> Any:
        response = self._send_checked(SdsRequest(method="GET", uri=uri), uri)
        return response.body

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
        drag_start_x = self.input_profile.swipe_left_start_x - (
            (self.input_profile.swipe_left_start_x - self.input_profile.swipe_left_end_x)
            // 2
        )
        pre_drag_x = self.input_profile.swipe_left_start_x - 8
        mid_x = max(self.input_profile.swipe_left_end_x, drag_start_x - 27)
        flick_velocity_x = float(self.input_profile.swipe_left_end_x - mid_x) * 12.0
        self._touch_sequence(
            [
                (self.input_profile.swipe_left_start_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, TOUCHDOWN),
                (pre_drag_x, self.input_profile.swipe_horizontal_y, -66.0, 0.0, TOUCHMOVE),
                (drag_start_x, self.input_profile.swipe_horizontal_y, 0.0, 0.0, DRAG_START),
                (mid_x, self.input_profile.swipe_horizontal_y, -1100.0, -6.0, TOUCHMOVE),
                (self.input_profile.swipe_left_end_x, self.input_profile.swipe_horizontal_y, flick_velocity_x, -7.0, LIFTOFF),
                (self.input_profile.swipe_left_end_x, self.input_profile.swipe_horizontal_y, flick_velocity_x, -7.0, FLICK),
                (0, 0, 0.0, 0.0, IDLE),
            ]
        )

    def swipe_up(self) -> None:
        pre_drag_y = self.input_profile.swipe_up_start_y - 16
        drag_start_y = self.input_profile.swipe_up_start_y - (
            (self.input_profile.swipe_up_start_y - self.input_profile.swipe_up_end_y)
            // 3
        )
        mid_y = max(self.input_profile.swipe_up_end_y, drag_start_y - 48)
        flick_velocity_y = float(self.input_profile.swipe_up_end_y - mid_y) * 18.0
        self._touch_sequence(
            [
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_start_y, 0.0, 0.0, TOUCHDOWN),
                (self.input_profile.swipe_up_x, pre_drag_y, 0.0, -96.0, TOUCHMOVE),
                (self.input_profile.swipe_up_x, drag_start_y, 0.0, 0.0, DRAG_START),
                (self.input_profile.swipe_up_x, mid_y, 0.0, -480.0, TOUCHMOVE),
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_end_y, 104.0, flick_velocity_y, LIFTOFF),
                (self.input_profile.swipe_up_x, self.input_profile.swipe_up_end_y, 104.0, flick_velocity_y, FLICK),
                (0, 0, 0.0, 0.0, IDLE),
            ]
        )

    def rotate_knob_up(self, angle: int = 15) -> None:
        timestamp = self._read_timestamp()
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=KNOB_URI_TEMPLATE.format(serial=self.serial),
                body={"event": {"angle": angle, "timestamp": timestamp}},
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
        self._send_checked(
            SdsRequest(
                method="PUT",
                uri=TOUCH_URI_TEMPLATE.format(serial=self.serial),
                body={
                    "x": x,
                    "y": y,
                    "data": {"x": velocity_x, "y": velocity_y},
                    "type": event_type,
                },
            ),
            "Touch/Event",
        )

    def _touch_sequence(
        self, events: Sequence[tuple[int, int, float, float, int]]
    ) -> None:
        for x, y, velocity_x, velocity_y, event_type in events:
            self._touch(x, y, event_type, velocity_x, velocity_y)

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


DeviceController = SdsDeviceController
