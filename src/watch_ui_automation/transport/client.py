from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from websocket import create_connection

from watch_ui_automation.transport.models import SdsRequest, SdsResponse


class SdsTransportClient:
    def __init__(
        self,
        sds_url: str,
        recorder: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.sds_url = sds_url
        self.recorder = recorder
        self._socket: Any | None = None
        self._request_id = 0
        self._pending_messages: list[dict[str, Any]] = []

    def connect(self) -> None:
        if self._socket is None:
            self._socket = create_connection(self.sds_url, timeout=10.0)

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def send_and_wait(self, request: SdsRequest) -> SdsResponse:
        self.connect()
        request_id = self._next_request_id()
        payload = request.to_payload(request_id)
        self._record({"direction": "request", "payload": payload})

        try:
            encoded_payload = json.dumps(payload)
            self._socket.send(encoded_payload)
        except Exception as exc:
            self._discard_socket()
            raise RuntimeError("send failed") from exc

        buffered_response = self._pop_buffered_message(request_id)
        if buffered_response is not None:
            self._record({"direction": "response", "payload": buffered_response})
            try:
                return SdsResponse.from_payload(buffered_response)
            except Exception:
                self._discard_socket()
                raise

        while True:
            try:
                raw_message = self._socket.recv()
            except Exception as exc:
                self._discard_socket()
                raise RuntimeError("receive failed") from exc

            try:
                raw_payload = json.loads(raw_message)
            except Exception as exc:
                self._discard_socket()
                raise ValueError("invalid JSON response") from exc

            if not isinstance(raw_payload, dict):
                self._discard_socket()
                raise ValueError("SDS response payload must be an object")

            if not self._matches_request_id(raw_payload, request_id):
                self._pending_messages.append(raw_payload)
                continue

            self._record({"direction": "response", "payload": raw_payload})
            try:
                return SdsResponse.from_payload(raw_payload)
            except Exception:
                self._discard_socket()
                raise

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _record(self, entry: dict[str, object]) -> None:
        if self.recorder is not None:
            self.recorder(entry)

    def _pop_buffered_message(self, request_id: int) -> dict[str, Any] | None:
        for index, message in enumerate(self._pending_messages):
            if self._matches_request_id(message, request_id):
                return self._pending_messages.pop(index)
        return None

    def _matches_request_id(self, raw_message: dict[str, Any], request_id: int) -> bool:
        try:
            return int(raw_message.get("RequestId", -1)) == request_id
        except (TypeError, ValueError):
            return False

    def _discard_socket(self) -> None:
        self.close()
