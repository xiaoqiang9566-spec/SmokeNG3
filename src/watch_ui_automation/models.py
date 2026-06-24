from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

CASE_STATUSES = {"passed", "failed", "error"}
ERROR_TYPES = {
    "assertion_failure",
    "device_error",
    "transport_error",
    "timeout",
}
CaseStatus = Literal["passed", "failed", "error"]
CaseErrorType = Literal[
    "assertion_failure",
    "device_error",
    "transport_error",
    "timeout",
]


@dataclass(frozen=True)
class RunManifest:
    device_serial: str
    sds_url: str
    selected_tests: list[str]
    framework_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CaseResult:
    case_name: str
    status: CaseStatus
    error_type: CaseErrorType | None
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in CASE_STATUSES:
            raise ValueError(f"unsupported case status: {self.status}")
        if self.error_type is not None and self.error_type not in ERROR_TYPES:
            raise ValueError(f"unsupported error_type: {self.error_type}")
        if self.status == "passed" and self.error_type is not None:
            raise ValueError("passed cases must not define error_type")
        if self.status in {"failed", "error"} and self.error_type is None:
            raise ValueError(f"{self.status} cases requires error_type")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
