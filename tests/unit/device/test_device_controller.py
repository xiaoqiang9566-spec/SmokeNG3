from __future__ import annotations

import pytest

from watch_ui_automation.config import InputConfig, NavigationConfig, ResourceConfig
from watch_ui_automation.device import DeviceController, SdsDeviceController
from watch_ui_automation.transport import SdsRequest, SdsResponse


class FakeTransport:
    def __init__(
        self,
        responses: dict[str, object | list[object]] | None = None,
        statuses: dict[str, int | list[int]] | None = None,
    ) -> None:
        self.requests: list[SdsRequest] = []
        self.responses = responses or {}
        self.statuses = statuses or {}

    def send_and_wait(self, request: SdsRequest) -> SdsResponse:
        self.requests.append(request)
        body = self._consume(self.responses, request.uri, {})
        status = self._consume(self.statuses, request.uri, 200)
        return SdsResponse(
            request_id=len(self.requests),
            status=status,
            uri=request.uri,
            body=body,
            raw={
                "Type": "Response",
                "RequestId": len(self.requests),
                "Status": status,
                "Uri": request.uri,
                "Body": body,
            },
        )

    def _consume(
        self,
        source: dict[str, object | list[object] | int | list[int]],
        uri: str,
        default: object,
    ) -> object:
        value = source.get(uri, default)
        if isinstance(value, list):
            if not value:
                return default
            return value.pop(0)
        return value


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
        swipe_left_start_x=420,
        swipe_left_end_x=46,
        swipe_horizontal_y=233,
        swipe_up_x=233,
        swipe_up_start_y=360,
        swipe_up_end_y=120,
    )


@pytest.fixture
def navigation() -> NavigationConfig:
    return NavigationConfig(
        open_settings=["press_middle"],
        open_widget=["swipe_left"],
        open_workout=["press_top_left"],
        go_back=["press_bottom_left"],
        workout_pause_resume=["press_top"],
    )


def build_controller(
    transport: FakeTransport,
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> DeviceController:
    return SdsDeviceController(
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


def test_assert_connected_raises_on_transport_error_status(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://SDS/ConnectedDevices": {"Devices": ["TEST123"]}},
        statuses={"suunto://SDS/ConnectedDevices": 503},
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(RuntimeError, match="ConnectedDevices"):
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
        "value": {"id": 1, "duration": 0.8}
    }


def test_press_middle_raises_on_transport_error_status(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        statuses={"suunto://TEST123/Ui/Test/SimulatedButtonPress": 500}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(RuntimeError, match="SimulatedButtonPress"):
        controller.press_middle(duration=0.8)


def test_device_module_exports_backward_compatible_alias() -> None:
    assert DeviceController is SdsDeviceController


def test_tap_center_sends_numeric_touch_sequence(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.tap_center()

    assert [request.method for request in transport.requests] == ["PUT", "PUT", "PUT", "PUT"]
    assert [request.uri for request in transport.requests] == [
        "suunto://TEST123/Device/UserInteraction/Touch/Event",
        "suunto://TEST123/Device/UserInteraction/Touch/Event",
        "suunto://TEST123/Device/UserInteraction/Touch/Event",
        "suunto://TEST123/Device/UserInteraction/Touch/Event",
    ]
    assert [request.body["type"] for request in transport.requests] == [1, 3, 6, 99]
    assert transport.requests[0].body == {
        "x": 233,
        "y": 233,
        "data": {"x": 0.0, "y": 0.0},
        "type": 1,
    }


def test_swipe_left_sends_numeric_touch_sequence(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.swipe_left()

    assert [request.body["type"] for request in transport.requests] == [1, 2, 5, 2, 3, 8, 99]
    assert transport.requests[0].body["x"] == 420
    assert transport.requests[0].body["y"] == 233
    assert transport.requests[2].body["type"] == 5
    assert transport.requests[5].body["type"] == 8
    assert transport.requests[6].body == {
        "x": 0,
        "y": 0,
        "data": {"x": 0.0, "y": 0.0},
        "type": 99,
    }


def test_swipe_up_sends_numeric_touch_sequence(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.swipe_up()

    assert [request.body["type"] for request in transport.requests] == [1, 2, 5, 2, 3, 8, 99]
    assert transport.requests[0].body["x"] == 233
    assert transport.requests[0].body["y"] == 360
    assert transport.requests[2].body["type"] == 5
    assert transport.requests[5].body["type"] == 8
    assert transport.requests[6].body == {
        "x": 0,
        "y": 0,
        "data": {"x": 0.0, "y": 0.0},
        "type": 99,
    }


def test_tap_center_raises_on_touch_transport_error_status(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        statuses={"suunto://TEST123/Device/UserInteraction/Touch/Event": [500]}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(RuntimeError, match="Touch/Event"):
        controller.tap_center()


def test_rotate_knob_up_reads_time_before_sending_knob_event(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://TEST123/Dev/Time": {"Content": 123456}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    controller.rotate_knob_up()

    assert [request.uri for request in transport.requests] == [
        "suunto://TEST123/Dev/Time",
        "suunto://TEST123/Device/UserInteraction/Knob/Event",
    ]
    assert transport.requests[0].method == "GET"
    assert transport.requests[1].method == "PUT"
    assert transport.requests[1].body == {"event": {"angle": 15, "timestamp": 123456}}


def test_rotate_knob_up_raises_when_time_payload_is_invalid(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://TEST123/Dev/Time": {"unexpected": "value"}}
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(ValueError, match="Dev/Time"):
        controller.rotate_knob_up()


def test_rotate_knob_up_raises_on_knob_write_transport_error_status(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport(
        responses={"suunto://TEST123/Dev/Time": {"Content": 123456}},
        statuses={"suunto://TEST123/Device/UserInteraction/Knob/Event": 500},
    )
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(RuntimeError, match="Knob/Event"):
        controller.rotate_knob_up()


def test_perform_action_raises_on_unknown_action(
    resources: ResourceConfig,
    input_profile: InputConfig,
    navigation: NavigationConfig,
) -> None:
    transport = FakeTransport()
    controller = build_controller(transport, resources, input_profile, navigation)

    with pytest.raises(AttributeError, match="unknown_action"):
        controller.perform_action("unknown_action")
