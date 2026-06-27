from __future__ import annotations

import tests.conftest as conftest_module

from tests.conftest import _selected_test_labels_from_items


class FakeMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeItem:
    def __init__(self, *marker_names: str) -> None:
        self._markers = [FakeMarker(name) for name in marker_names]

    def iter_markers(self):
        return iter(self._markers)


def test_selected_test_labels_from_items_returns_stable_allowed_union() -> None:
    items = [
        FakeItem("smoke", "device"),
        FakeItem("yaml", "device"),
        FakeItem("device", "smoke"),
    ]

    assert _selected_test_labels_from_items(items) == ["device", "yaml", "smoke"]


def test_selected_test_labels_from_items_ignores_untracked_markers() -> None:
    items = [
        FakeItem("device", "slow", "regression"),
        FakeItem("flaky", "regression"),
    ]

    assert _selected_test_labels_from_items(items) == ["device", "regression"]


def test_selected_test_labels_from_items_keeps_device_only_when_no_suite_marker() -> None:
    items = [
        FakeItem("device"),
        FakeItem("device", "unknown_marker"),
    ]

    assert _selected_test_labels_from_items(items) == ["device"]


def test_device_dsl_uses_session_item_labels_for_run_manifest(monkeypatch) -> None:
    captured_manifest = None
    transport_closed = False

    class FakeWriter:
        def __init__(self, root_dir) -> None:
            self.root_dir = root_dir

        def start_run(self, manifest) -> None:
            nonlocal captured_manifest
            captured_manifest = manifest

    class FakeTransport:
        def __init__(self, sds_url: str) -> None:
            self.sds_url = sds_url

        def close(self) -> None:
            nonlocal transport_closed
            transport_closed = True

    class FakeDevice:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def assert_connected(self) -> None:
            pass

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeDsl:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeProjectConfig:
        class Artifacts:
            root_dir = "artifacts"

        class Device:
            serial = "TEST123"
            sds_url = "ws://localhost:65534"

        class Resources:
            current_page_uri = "suunto://watch/current-page"
            current_widget_uri = "suunto://watch/current-widget"
            workout_state_uri = "suunto://watch/workout-state"
            settings_focus_uri = "suunto://watch/settings-focus"

        class Input:
            pass

        class Navigation:
            open_settings = ["open_settings"]
            open_widget = ["open_widget"]
            open_workout = ["open_workout"]
            go_back = ["go_back"]
            workout_pause_resume = ["workout_pause_resume"]

        class Timeouts:
            settle_seconds = 1.5
            poll_interval_seconds = 0.25

        artifacts = Artifacts()
        device = Device()
        resources = Resources()
        input = Input()
        navigation = Navigation()
        timeouts = Timeouts()

    class FakeSessionState:
        items = [
            FakeItem("device", "smoke"),
            FakeItem("device", "yaml", "smoke"),
        ]

    class FakeRequest:
        session = FakeSessionState()

    monkeypatch.setenv("WATCH_UI_RUN_DEVICE_TESTS", "1")
    monkeypatch.setattr(conftest_module, "ArtifactWriter", FakeWriter)
    monkeypatch.setattr(conftest_module, "SdsTransportClient", FakeTransport)
    monkeypatch.setattr(conftest_module, "SdsDeviceController", FakeDevice)
    monkeypatch.setattr(conftest_module, "WatchSession", FakeSession)
    monkeypatch.setattr(conftest_module, "WatchDsl", FakeDsl)

    fixture = conftest_module.device_dsl.__wrapped__(FakeRequest(), FakeProjectConfig())
    next(fixture)
    fixture.close()

    assert captured_manifest.selected_tests == ["device", "yaml", "smoke"]
    assert transport_closed is True
