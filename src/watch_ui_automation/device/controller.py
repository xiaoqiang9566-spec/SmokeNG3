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


class DeviceController:
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
        self._press_button("Top", duration)

    def press_middle(self, duration: float = 0.8) -> None:
        self._press_button("Middle", duration)

    def press_bottom(self, duration: float = 0.8) -> None:
        self._press_button("Bottom", duration)

    def press_top_left(self, duration: float = 0.8) -> None:
        self._press_button("TopLeft", duration)

    def press_bottom_left(self, duration: float = 0.8) -> None:
        self._press_button("BottomLeft", duration)

    def tap_center(self) -> None:
        self._touch(
            self.input_profile.tap_center_x,
            self.input_profile.tap_center_y,
            "tap",
        )

    def swipe_left(self) -> None:
        self._touch(
            self.input_profile.swipe_left_start_x,
            self.input_profile.swipe_horizontal_y,
            "swipe_left",
        )

    def swipe_up(self) -> None:
        self._touch(
            self.input_profile.swipe_up_x,
            self.input_profile.swipe_up_start_y,
            "swipe_up",
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

    def _press_button(self, button_id: str, duration: float) -> None:
        self.transport.send_and_wait(
            SdsRequest(
                method="PUT",
                uri=BUTTON_URI_TEMPLATE.format(serial=self.serial),
                body={"value": {"id": button_id, "duration": duration}},
            )
        )

    def _touch(self, x: int, y: int, event_type: str) -> None:
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

    def _read_timestamp(self) -> Any:
        payload = self.read_json(DEVICE_TIME_URI_TEMPLATE.format(serial=self.serial))
        if isinstance(payload, Mapping):
            if "timestamp" in payload:
                return payload["timestamp"]
            if "Timestamp" in payload:
                return payload["Timestamp"]
        return payload
