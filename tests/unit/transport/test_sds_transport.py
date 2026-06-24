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

    def send(self, payload: str) -> None:
        self.sent_messages.append(payload)

    def recv(self) -> str:
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


def test_transport_connects_and_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()
    created: list[tuple[str, float]] = []

    def fake_create_connection(url: str, timeout: float) -> FakeSocket:
        created.append((url, timeout))
        return fake_socket

    monkeypatch.setattr(client_module, "create_connection", fake_create_connection)

    client = SdsTransportClient("ws://localhost:65534")
    client.connect()
    client.close()

    assert created == [("ws://localhost:65534", 10.0)]
    assert fake_socket.closed is True
    assert client._socket is None
