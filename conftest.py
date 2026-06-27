from __future__ import annotations

import pytest

from config.settings import load_settings
from pages.settings_page import SettingsPage
from pages.sport_page import SportPage
from pages.widget_page import WidgetPage


@pytest.fixture(scope="session")
def framework_settings():
    return load_settings()


@pytest.fixture(scope="session")
def input_capabilities(framework_settings):
    return framework_settings.input_capabilities


@pytest.fixture
def sport_page(input_capabilities):
    return SportPage(input_capabilities)


@pytest.fixture
def widget_page(input_capabilities):
    return WidgetPage(input_capabilities)


@pytest.fixture
def settings_page(input_capabilities):
    return SettingsPage(input_capabilities)
