from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.yaml_util import load_yaml


@dataclass(frozen=True)
class FrameworkSettings:
    config: dict[str, Any]
    env: dict[str, Any]
    env_name: str

    @property
    def input_capabilities(self) -> dict[str, Any]:
        return dict(self.config["input_capabilities"])


def load_settings(
    config_path: str | Path = "config/config.yaml",
    env_path: str | Path = "config/env.yaml",
    env_name: str | None = None,
) -> FrameworkSettings:
    config = load_yaml(config_path)
    envs = load_yaml(env_path)
    selected_env = env_name or str(config["project"]["default_env"])
    if selected_env not in envs:
        raise KeyError(f"unknown environment: {selected_env}")
    return FrameworkSettings(
        config=config,
        env=dict(envs[selected_env]),
        env_name=selected_env,
    )
