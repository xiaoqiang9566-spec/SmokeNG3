from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScenarioStep:
    name: str
    action: str
    params: dict[str, object] = field(default_factory=dict)
    save_as: str | None = None


@dataclass(frozen=True)
class ScenarioCase:
    id: str
    title: str
    markers: list[str]
    baseline: str
    steps: list[ScenarioStep]
    source_file: str | None = None


@dataclass(frozen=True)
class PageState:
    name: str
    raw: dict[str, object] | None = None


@dataclass(frozen=True)
class WidgetState:
    name: str | None
    path: str | None
    raw: dict[str, object] | None = None


@dataclass(frozen=True)
class WorkoutState:
    status: str | None
    raw: dict[str, object] | None = None
