from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SdsRequest:
    method: str
    uri: str
    body: dict[str, object] = field(default_factory=dict)
    type: str = "Request"

    def to_payload(self, request_id: int) -> dict[str, object]:
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
    body: dict[str, object]
    raw: dict[str, object]

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "SdsResponse":
        body = payload.get("Body", {})
        if not isinstance(body, dict):
            raise ValueError("SDS response body must be a mapping")

        return cls(
            request_id=int(payload["RequestId"]),
            status=int(payload["Status"]),
            uri=str(payload["Uri"]),
            body=body,
            raw=payload,
        )
