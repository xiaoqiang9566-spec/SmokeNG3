from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequestRecord:
    method: str
    target: str
    payload: dict[str, Any]


class RequestClient:
    def __init__(self) -> None:
        self.records: list[RequestRecord] = []

    def send(self, method: str, target: str, payload: dict[str, Any] | None = None) -> RequestRecord:
        record = RequestRecord(method=method, target=target, payload=payload or {})
        self.records.append(record)
        return record
