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
CLICK = 6
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
        response = self.transport.send_and_wait(
            SdsRequest(method="GET", uri=CONNECTED_DEVICES_URI)
        )
        body = response.body if isinstance(response.body, Mapping) else {}
        devices = body.get("Devices", [])
        if self.serial not in devices:
            raise AssertionError(f"device not connected: {self.serial}")

    def read_json(self, uri: str) -> Any:
        response = self.transport.send_and_wait(SdsRequest(method="GET", uri=uri))
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
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, TOUCHDOWN),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, LIFTOFF),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, CLICK),
                (self.input_profile.tap_center_x, self.input_profile.tap_center_y, IDLE),
            ]
        )

    def swipe_left(self) -> None:
        self._touch_sequence(
            [
                (
                    self.input_profile.swipe_left_start_x,
                    self.input_profile.swipe_horizontal_y,
                    TOUCHDOWN,
                ),
                (
                    self.input_profile.swipe_left_end_x,
                    self.input_profile.swipe_horizontal_y,
                    TOUCHMOVE,
                ),
                (
                    self.input_profile.swipe_left_end_x,
                    self.input_profile.swipe_horizontal_y,
                    LIFTOFF,
                ),
                (
                    self.input_profile.swipe_left_end_x,
                    self.input_profile.swipe_horizontal_y,
                    IDLE,
                ),
            ]
        )

    def swipe_up(self) -> None:
        self._touch_sequence(
            [
                (
                    self.input_profile.swipe_up_x,
                    self.input_profile.swipe_up_start_y,
                    TOUCHDOWN,
                ),
                (
                    self.input_profile.swipe_up_x,
                    self.input_profile.swipe_up_end_y,
                    TOUCHMOVE,
                ),
                (
                    self.input_profile.swipe_up_x,
                    self.input_profile.swipe_up_end_y,
                    LIFTOFF,
                ),
                (
                    self.input_profile.swipe_up_x,
                    self.input_profile.swipe_up_end_y,
                    IDLE,
                ),
            ]
        )

    def rotate_knob_up(self, angle: int = 15) -> None:
        timestamp = self._read_timestamp()
        self.transport.send_and_wait(
            SdsRequest(
                method="PUT",
                uri=KNOB_URI_TEMPLATE.format(serial=self.serial),
                body={"event": {"angle": angle, "timestamp": timestamp}},
            )
        )

    def rotate_knob_down(self, angle: int = -15) -> None:
        self.rotate_knob_up(angle=angle)

    def perform_action(self, action_name: str) -> None:
        getattr(self, action_name)()

    def perform_actions(self, actions: Sequence[str]) -> None:
        for action_name in actions:
            self.perform_action(action_name)

    def _press_button(self, button_id: int, duration: float) -> None:
        self.transport.send_and_wait(
            SdsRequest(
                method="PUT",
                uri=BUTTON_URI_TEMPLATE.format(serial=self.serial),
                body={"value": {"id": button_id, "duration": duration}},
            )
        )

    def _touch(self, x: int, y: int, event_type: int) -> None:
        self.transport.send_and_wait(
            SdsRequest(
                method="PUT",
                uri=TOUCH_URI_TEMPLATE.format(serial=self.serial),
                body={
                    "x": x,
                    "y": y,
                    "data": {"x": 0.0, "y": 0.0},
                    "type": event_type,
                },
            )
        )

    def _touch_sequence(self, events: Sequence[tuple[int, int, int]]) -> None:
        for x, y, event_type in events:
            self._touch(x, y, event_type)

    def _read_timestamp(self) -> Any:
        payload = self.read_json(DEVICE_TIME_URI_TEMPLATE.format(serial=self.serial))
        if isinstance(payload, Mapping):
            if "Content" in payload:
                return payload["Content"]
            if "timestamp" in payload:
                return payload["timestamp"]
            if "Timestamp" in payload:
                return payload["Timestamp"]
        return payload


DeviceController = SdsDeviceController
