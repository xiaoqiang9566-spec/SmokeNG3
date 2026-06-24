from __future__ import annotations

import json

import pytest

import watch_ui_automation.transport.client as client_module
from watch_ui_automation.transport.client import SdsTransportClient
from watch_ui_automation.transport.models import SdsRequest, SdsResponse


class FakeSocket:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.sent_messages: list[str] = []
        self.responses = responses or []
        self.closed = False
        self.recv_calls = 0
        self.send_error: Exception | None = None
        self.recv_error: Exception | None = None

    def send(self, payload: str) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent_messages.append(payload)

    def recv(self) -> str:
        self.recv_calls += 1
        if self.recv_error is not None:
            raise self.recv_error
        if not self.responses:
            raise AssertionError("recv() called without queued responses")
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


def test_transport_matches_request_id_and_records_request_response() -> None:
    records: list[dict[str, object]] = []
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 999,
                    "Status": 200,
                    "Uri": "suunto://ignored",
                    "Body": {"ignored": True},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 1,
                    "Status": 200,
                    "Uri": "suunto://SDS/ConnectedDevices",
                    "Body": {"devices": ["TEST123"]},
                }
            ),
        ]
    )
    client = SdsTransportClient("ws://localhost:65534", recorder=records.append)
    client._socket = fake_socket

    response = client.send_and_wait(
        SdsRequest(
            method="GET",
            uri="suunto://SDS/ConnectedDevices",
        )
    )

    assert isinstance(response, SdsResponse)
    assert json.loads(fake_socket.sent_messages[0]) == {
        "Type": "Request",
        "Method": "GET",
        "Uri": "suunto://SDS/ConnectedDevices",
        "Body": {},
        "RequestId": 1,
    }
    assert response.request_id == 1
    assert response.status == 200
    assert response.body["devices"] == ["TEST123"]
    assert records == [
        {
            "direction": "request",
            "payload": {
                "Type": "Request",
                "Method": "GET",
                "Uri": "suunto://SDS/ConnectedDevices",
                "Body": {},
                "RequestId": 1,
            },
        },
        {
            "direction": "response",
            "payload": {
                "Type": "Response",
                "RequestId": 1,
                "Status": 200,
                "Uri": "suunto://SDS/ConnectedDevices",
                "Body": {"devices": ["TEST123"]},
            },
        },
    ]


def test_transport_matches_string_request_id() -> None:
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": "1",
                    "Status": 200,
                    "Uri": "suunto://SDS/ConnectedDevices",
                    "Body": {"devices": ["TEST123"]},
                }
            )
        ]
    )
    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/ConnectedDevices"))

    assert response.request_id == 1
    assert response.body == {"devices": ["TEST123"]}


def test_transport_buffers_crossed_responses_for_later_request() -> None:
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 2,
                    "Status": 202,
                    "Uri": "suunto://SDS/Second",
                    "Body": {"second": True},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 1,
                    "Status": 200,
                    "Uri": "suunto://SDS/First",
                    "Body": {"first": True},
                }
            ),
        ]
    )
    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    first_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/First"))
    recv_calls_after_first = fake_socket.recv_calls
    second_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/Second"))

    assert first_response.request_id == 1
    assert first_response.body == {"first": True}
    assert second_response.request_id == 2
    assert second_response.body == {"second": True}
    assert fake_socket.recv_calls == recv_calls_after_first


def test_transport_does_not_buffer_out_of_order_event_messages() -> None:
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Event",
                    "RequestId": 2,
                    "Uri": "suunto://SDS/Event",
                    "Body": {"event": True},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 1,
                    "Status": 200,
                    "Uri": "suunto://SDS/First",
                    "Body": {"first": True},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 2,
                    "Status": 202,
                    "Uri": "suunto://SDS/Second",
                    "Body": {"second": True},
                }
            ),
        ]
    )
    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    first_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/First"))
    recv_calls_after_first = fake_socket.recv_calls

    assert first_response.request_id == 1
    assert client._pending_messages == []

    second_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/Second"))

    assert second_response.request_id == 2
    assert second_response.body == {"second": True}
    assert fake_socket.recv_calls == recv_calls_after_first + 1


def test_transport_does_not_buffer_messages_without_request_id() -> None:
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Notification",
                    "Uri": "suunto://SDS/Notification",
                    "Body": {"message": "ignored"},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 1,
                    "Status": 200,
                    "Uri": "suunto://SDS/First",
                    "Body": {"first": True},
                }
            ),
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 2,
                    "Status": 202,
                    "Uri": "suunto://SDS/Second",
                    "Body": {"second": True},
                }
            ),
        ]
    )
    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    first_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/First"))
    recv_calls_after_first = fake_socket.recv_calls

    assert first_response.request_id == 1
    assert client._pending_messages == []

    second_response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/Second"))

    assert second_response.request_id == 2
    assert second_response.body == {"second": True}
    assert fake_socket.recv_calls == recv_calls_after_first + 1


def test_transport_allows_non_dict_body_values() -> None:
    fake_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 1,
                    "Status": 200,
                    "Uri": "suunto://SDS/Scalar",
                    "Body": ["item", 2, False],
                }
            )
        ]
    )
    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    response = client.send_and_wait(
        SdsRequest(method="POST", uri="suunto://SDS/Scalar", body=["item", 2, False])
    )

    assert json.loads(fake_socket.sent_messages[0])["Body"] == ["item", 2, False]
    assert response.body == ["item", 2, False]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing required field: Type"),
        (
            {"Type": "Event", "RequestId": 1, "Status": 200, "Uri": "suunto://SDS/Test", "Body": {}},
            "invalid response type: Event",
        ),
        (
            {"Type": "Response", "Status": 200, "Uri": "suunto://SDS/Test", "Body": {}},
            "missing required field: RequestId",
        ),
        (
            {"Type": "Response", "RequestId": 1, "Uri": "suunto://SDS/Test", "Body": {}},
            "missing required field: Status",
        ),
        (
            {"Type": "Response", "RequestId": 1, "Status": 200, "Body": {}},
            "missing required field: Uri",
        ),
    ],
)
def test_transport_rejects_invalid_response_envelope(payload: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        SdsResponse.from_payload(payload)


@pytest.mark.parametrize(
    ("socket_setup", "expected_exception", "expected_message"),
    [
        ("send_error", RuntimeError, "send failed"),
        ("recv_error", RuntimeError, "receive failed"),
        ("bad_json", ValueError, "invalid JSON response"),
        ("bad_payload", ValueError, "missing required field: Status"),
    ],
)
def test_transport_discards_socket_after_transport_failures(
    socket_setup: str, expected_exception: type[Exception], expected_message: str
) -> None:
    fake_socket = FakeSocket()
    if socket_setup == "send_error":
        fake_socket.send_error = RuntimeError("boom")
    elif socket_setup == "recv_error":
        fake_socket.recv_error = RuntimeError("boom")
    elif socket_setup == "bad_json":
        fake_socket.responses = ["not-json"]
    elif socket_setup == "bad_payload":
        fake_socket.responses = [json.dumps({"Type": "Response", "RequestId": 1, "Uri": "suunto://SDS/Test"})]

    client = SdsTransportClient("ws://localhost:65534")
    client._socket = fake_socket

    with pytest.raises(expected_exception, match=expected_message):
        client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/Test"))

    assert fake_socket.closed is True
    assert client._socket is None
    assert client._pending_messages == []


def test_transport_discards_buffered_messages_after_disconnect_before_reconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 2,
                    "Status": 202,
                    "Uri": "suunto://SDS/Second",
                    "Body": {"source": "stale"},
                }
            )
        ]
    )
    stale_recv = stale_socket.recv
    stale_recv_calls = 0

    def recv_then_fail() -> str:
        nonlocal stale_recv_calls
        stale_recv_calls += 1
        if stale_recv_calls == 1:
            return stale_recv()
        raise RuntimeError("boom")

    stale_socket.recv = recv_then_fail  # type: ignore[method-assign]
    fresh_socket = FakeSocket(
        responses=[
            json.dumps(
                {
                    "Type": "Response",
                    "RequestId": 2,
                    "Status": 200,
                    "Uri": "suunto://SDS/Second",
                    "Body": {"source": "fresh"},
                }
            )
        ]
    )
    sockets = [stale_socket, fresh_socket]

    def fake_create_connection(url: str, timeout: float) -> FakeSocket:
        assert url == "ws://localhost:65534"
        assert timeout == 10.0
        if not sockets:
            raise AssertionError("no sockets left to create")
        return sockets.pop(0)

    monkeypatch.setattr(client_module, "create_connection", fake_create_connection)

    client = SdsTransportClient("ws://localhost:65534")

    with pytest.raises(RuntimeError, match="receive failed"):
        client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/First"))

    assert stale_socket.closed is True
    assert client._pending_messages == []

    response = client.send_and_wait(SdsRequest(method="GET", uri="suunto://SDS/Second"))

    assert response.request_id == 2
    assert response.body == {"source": "fresh"}
    assert fresh_socket.recv_calls == 1


def test_transport_connects_and_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()
    created: list[tuple[str, float]] = []

    def fake_create_connection(url: str, timeout: float) -> FakeSocket:
        created.append((url, timeout))
        return fake_socket

    monkeypatch.setattr(client_module, "create_connection", fake_create_connection)

    client = SdsTransportClient("ws://localhost:65534")
    client._pending_messages.append({"RequestId": 99})
    client.connect()
    client.close()

    assert created == [("ws://localhost:65534", 10.0)]
    assert fake_socket.closed is True
    assert client._socket is None
    assert client._pending_messages == []
