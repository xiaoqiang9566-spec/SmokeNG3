from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SdsRequest:
    method: str
    uri: str
    body: Any = field(default_factory=dict)
    type: str = "Request"

    def to_payload(self, request_id: int) -> dict[str, Any]:
        return {
            "Type": self.type,
            "Method": self.method,
            "Uri": self.uri,
            "Body": self.body,
            "RequestId": request_id,
        }


@dataclass(frozen=True)
class SdsResponse:
    request_id: int
    status: int
    uri: str
    body: Any
    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SdsResponse":
        if not isinstance(payload, dict):
            raise ValueError("SDS response payload must be an object")

        response_type = _require_field(payload, "Type")
        if response_type != "Response":
            raise ValueError(f"invalid response type: {response_type}")

        return cls(
            request_id=int(_require_field(payload, "RequestId")),
            status=int(_require_field(payload, "Status")),
            uri=str(_require_field(payload, "Uri")),
            body=payload.get("Body"),
            raw=payload,
        )


def _require_field(payload: dict[str, Any], field_name: str) -> Any:
    if field_name not in payload:
        raise ValueError(f"missing required field: {field_name}")
    return payload[field_name]
