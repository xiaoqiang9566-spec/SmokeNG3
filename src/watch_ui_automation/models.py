from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    suite_name: str
    device_serial: str
    started_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    status: str
    started_at: str
    finished_at: str
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Optional[str]]:
        return asdict(self)
