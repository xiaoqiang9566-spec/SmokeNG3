from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

from watch_ui_automation import __version__
from watch_ui_automation.artifacts.writer import ArtifactWriter
from watch_ui_automation.config import ProjectConfig, load_project_config
from watch_ui_automation.device.controller import SdsDeviceController
from watch_ui_automation.dsl.watch import WatchDsl
from watch_ui_automation.models import RunManifest
from watch_ui_automation.session.runtime import WatchSession
from watch_ui_automation.transport.client import SdsTransportClient

RUN_LABEL_MARKERS = ("device", "yaml", "smoke", "regression", "stability")


def pytest_addoption(parser) -> None:
    parser.addoption("--device-config", action="store", default="configs/default.yaml")
    parser.addoption("--scenario-dir", action="store", default="tests/yaml_cases")
    parser.addoption("--scenario-suite", action="store", default="smoke")


def _require_real_device_config(project_config: ProjectConfig) -> None:
    if project_config.device.serial == "REPLACE_ME":
        raise pytest.UsageError(
            "Real-device tests require a concrete device serial in the selected config file"
        )


def _selected_test_labels_from_items(items) -> list[str]:
    selected = set()
    for item in items:
        for marker in item.iter_markers():
            if marker.name in RUN_LABEL_MARKERS:
                selected.add(marker.name)
    return [label for label in RUN_LABEL_MARKERS if label in selected]


@pytest.fixture(scope="session")
def project_config(pytestconfig) -> ProjectConfig:
    return load_project_config(pytestconfig.getoption("--device-config"))


@pytest.fixture(scope="session")
def device_dsl(request, project_config: ProjectConfig) -> Iterator[WatchDsl]:
    if os.getenv("WATCH_UI_RUN_DEVICE_TESTS") != "1":
        pytest.skip("Set WATCH_UI_RUN_DEVICE_TESTS=1 to run real-device tests")

    _require_real_device_config(project_config)

    writer = ArtifactWriter(project_config.artifacts.root_dir)
    writer.start_run(
        RunManifest(
            device_serial=project_config.device.serial,
            sds_url=project_config.device.sds_url,
            selected_tests=_selected_test_labels_from_items(request.session.items),
            framework_version=__version__,
        )
    )

    transport = SdsTransportClient(project_config.device.sds_url)
    device = SdsDeviceController(
        serial=project_config.device.serial,
        transport=transport,
        resources=project_config.resources,
        input_profile=project_config.input,
        navigation=project_config.navigation,
    )
    device.assert_connected()

    session = WatchSession(
        device=device,
        artifact_writer=writer,
        current_page_uri=project_config.resources.current_page_uri,
        baseline_actions=project_config.navigation.recover_baseline,
        settle_seconds=project_config.timeouts.settle_seconds,
        poll_interval_seconds=project_config.timeouts.poll_interval_seconds,
    )

    try:
        yield WatchDsl(
            session=session,
            resources={
                "current_page": project_config.resources.current_page_uri,
                "current_widget": project_config.resources.current_widget_uri,
                "workout_state": project_config.resources.workout_state_uri,
                "settings_focus": project_config.resources.settings_focus_uri,
            },
            navigation={
                "open_settings": project_config.navigation.open_settings,
                "open_widget": project_config.navigation.open_widget,
                "open_pinned_widget_shortcut": project_config.navigation.open_pinned_widget_shortcut,
                "open_workout": project_config.navigation.open_workout,
                "go_back": project_config.navigation.go_back,
                "recover_baseline": project_config.navigation.recover_baseline,
                "workout_pause_resume": project_config.navigation.workout_pause_resume,
            },
        )
    finally:
        session.release_device_bypasses()
        transport.close()


def read_content(device_dsl: WatchDsl, resource_key: str) -> Any:
    payload = device_dsl.session.read_json(device_dsl.resources[resource_key])
    return payload.get("Content")
