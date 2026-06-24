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
        self._socket.send(json.dumps(payload))

        while True:
            raw_payload = json.loads(self._socket.recv())
            if raw_payload.get("RequestId") != request_id:
                continue

            self._record({"direction": "response", "payload": raw_payload})
            return SdsResponse.from_payload(raw_payload)

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _record(self, entry: dict[str, object]) -> None:
        if self.recorder is not None:
            self.recorder(entry)
