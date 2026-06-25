from __future__ import annotations

import pytest

from watch_ui_automation.config import InputConfig, NavigationConfig, ResourceConfig
from watch_ui_automation.device import DeviceController
from watch_ui_automation.transport import SdsRequest, SdsResponse


class FakeTransport:
    def __init__(self, responses: dict[str, object] | None = None) -> None:
        self.requests: list[SdsRequest] = []
        self.responses = responses or {}

    def send_and_wait(self, request: SdsRequest) -> SdsResponse:
        self.requests.append(request)
        body = self.responses.get(request.uri, {})
        return SdsResponse(
            request_id=len(self.requests),
            status=200,
            uri=request.uri,
            body=body,
            raw={
                "Type": "Response",
                "RequestId": len(self.requests),
                "Status": 200,
                "Uri": request.uri,
                "Body": body,
            },
        )


@pytest.fixture
def resources() -> ResourceConfig:
    return ResourceConfig(
        current_page_uri="suunto://TEST123/System/UI/CurrentPage",
        current_widget_uri="suunto://TEST123/System/UI/CurrentWidget",
        workout_state_uri="suunto://TEST123/Sport/Workout/State",
        settings_focus_uri="suunto://TEST123/System/UI/Settings/FocusedItem",
    )


@pytest.fixture
def input_profile() -> InputConfig:
    return InputConfig(
        tap_center_x=233,
        tap_center_y=233,
        swipe_left_start_x=320,
        swipe_left_end_x=120,
        swipe_horizontal_y=233,
        swipe_up_x=233,
        swipe_up_start_y=320,
        swipe_up_end_y=120,
    )


@pytest.fixture
def navigation() -> NavigationConfig:
    return NavigationConfig(
        open_settings=["press_middle"],
        open_widget=["swipe_left"],
        open_workout=["press_top"],
        go_back=["press_bottom"],
        workout_pause_resume=["press_middle"],
    )


def build_controller(
    transport: FakeTransport,
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> DeviceController:
    return DeviceController(
        serial="TEST123",
        transport=transport,
        resources=resources,
        input_profile=input_profile,
        navigation=navigation,
    )


def test_assert_connected_reads_connected_devices_resource(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://SDS/ConnectedDevices": {"Devices": ["TEST123", "OTHER999"]}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.assert_connected()

    assert transport.requests[0].method == "GET"
    assert transport.requests[0].uri == "suunto://SDS/ConnectedDevices"


def test_assert_connected_raises_when_serial_is_missing(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://SDS/ConnectedDevices": {"Devices": ["OTHER999"]}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(AssertionError, match="TEST123"):
        controller.assert_connected()


def test_read_json_reads_resource_body(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={resources.current_page_uri: {"page": "WidgetCarousel"}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    payload = controller.read_json(resources.current_page_uri)

    assert payload == {"page": "WidgetCarousel"}
    assert transport.requests[0].method == "GET"
    assert transport.requests[0].uri == resources.current_page_uri


def test_press_middle_sends_button_press_request(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.press_middle(duration=0.8)

    assert transport.requests[0].method == "PUT"
    assert transport.requests[0].uri == "suunto://TEST123/Ui/Test/SimulatedButtonPress"
    assert transport.requests[0].body == {
        "value": {"id": "Middle", "duration": 0.8}
    }


def test_tap_center_sends_touch_event(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.tap_center()

    assert transport.requests[0].method == "PUT"
    assert transport.requests[0].uri == "suunto://TEST123/Device/UserInteraction/Touch/Event"
    assert transport.requests[0].body == {
        "x": 233,
        "y": 233,
        "data": {"x": 0.0, "y": 0.0},
        "type": "tap",
    }


def test_rotate_knob_up_reads_time_before_sending_knob_event(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://TEST123/Dev/Time": {"timestamp": 1234567890}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.rotate_knob_up()

    assert [request.uri for request in transport.requests] == [
        "suunto://TEST123/Dev/Time",
        "suunto://TEST123/Device/UserInteraction/Knob/Event",
    ]
    assert transport.requests[0].method == "GET"
    assert transport.requests[1].method == "PUT"
    assert transport.requests[1].body == {
        "event": {"angle": 15, "timestamp": 1234567890}
    }
