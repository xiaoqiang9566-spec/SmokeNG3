from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import yaml

SUPPORTED_NAVIGATION_ACTIONS = frozenset(
    {
        "press_top",
        "press_middle",
        "press_bottom",
        "press_top_left",
        "press_bottom_left",
        "tap_center",
        "swipe_left",
        "swipe_up",
        "rotate_knob_up",
        "rotate_knob_down",
    }
)


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
class InputConfig:
    tap_center_x: int
    tap_center_y: int
    swipe_left_start_x: int
    swipe_left_end_x: int
    swipe_horizontal_y: int
    swipe_up_x: int
    swipe_up_start_y: int
    swipe_up_end_y: int


@dataclass(frozen=True)
class NavigationConfig:
    open_settings: list[str]
    open_widget: list[str]
    open_workout: list[str]
    go_back: list[str]
    workout_pause_resume: list[str]


@dataclass(frozen=True)
class ProjectConfig:
    device: DeviceConfig
    timeouts: TimeoutConfig
    artifacts: ArtifactConfig
    resources: ResourceConfig
    input: InputConfig
    navigation: NavigationConfig


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _require_section(raw: Mapping[str, object], name: str) -> Mapping[str, object]:
    if name not in raw:
        raise ValueError(f"missing config section: {name}")
    return _require_mapping(raw[name], f"section '{name}'")


def _expand_resource_templates(
    resources: Mapping[str, object], serial: str
) -> dict[str, str]:
    expanded: dict[str, str] = {}
    for key, value in resources.items():
        if not isinstance(value, str):
            raise ValueError(f"resources.{key} must be a string")
        expanded[key] = value.replace("{serial}", serial)
    return expanded


def _build_section(config_cls: type, payload: Mapping[str, object], name: str):
    try:
        return config_cls(**payload)
    except TypeError as exc:
        raise ValueError(f"invalid section '{name}': {exc}") from exc


def _validate_navigation_config(navigation: NavigationConfig) -> NavigationConfig:
    for field_name, actions in navigation.__dict__.items():
        if not isinstance(actions, list):
            raise ValueError(f"navigation.{field_name} must be a list")
        for action_name in actions:
            if not isinstance(action_name, str):
                raise ValueError(f"navigation.{field_name} action must be a string")
            if action_name not in SUPPORTED_NAVIGATION_ACTIONS:
                raise ValueError(
                    f"invalid navigation action: {action_name} in navigation.{field_name}"
                )
    return navigation


def load_project_config(path: Union[str, Path]) -> ProjectConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError("config file is empty")

    project_raw = _require_mapping(raw, "top-level config")
    device_raw = _require_section(project_raw, "device")
    timeout_raw = _require_section(project_raw, "timeouts")
    artifact_raw = _require_section(project_raw, "artifacts")
    resource_raw = _require_section(project_raw, "resources")
    input_raw = _require_section(project_raw, "input")
    navigation_raw = _require_section(project_raw, "navigation")

    device = _build_section(DeviceConfig, device_raw, "device")
    resources = _expand_resource_templates(resource_raw, device.serial)

    return ProjectConfig(
        device=device,
        timeouts=_build_section(TimeoutConfig, timeout_raw, "timeouts"),
        artifacts=_build_section(ArtifactConfig, artifact_raw, "artifacts"),
        resources=_build_section(ResourceConfig, resources, "resources"),
        input=_build_section(InputConfig, input_raw, "input"),
        navigation=_validate_navigation_config(
            _build_section(NavigationConfig, navigation_raw, "navigation")
        ),
    )
