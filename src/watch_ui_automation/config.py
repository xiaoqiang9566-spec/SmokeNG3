from dataclasses import dataclass
from pathlib import Path
from typing import Union

import yaml


@dataclass(frozen=True)
class DeviceConfig:
    serial: str
    sds_url: str


@dataclass(frozen=True)
class TimeoutConfig:
    request_seconds: float
    settle_seconds: float
    poll_interval_seconds: float


@dataclass(frozen=True)
class ArtifactConfig:
    root_dir: str


@dataclass(frozen=True)
class ResourceConfig:
    current_page_uri: str
    current_widget_uri: str
    workout_state_uri: str
    settings_focus_uri: str


@dataclass(frozen=True)
class ProjectConfig:
    device: DeviceConfig
    timeouts: TimeoutConfig
    artifacts: ArtifactConfig
    resources: ResourceConfig


def load_project_config(path: Union[str, Path]) -> ProjectConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ProjectConfig(
        device=DeviceConfig(**raw["device"]),
        timeouts=TimeoutConfig(**raw["timeouts"]),
        artifacts=ArtifactConfig(**raw["artifacts"]),
        resources=ResourceConfig(**raw["resources"]),
    )
