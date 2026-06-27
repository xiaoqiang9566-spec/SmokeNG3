import pytest


TODO_PLACEHOLDER = (
    "TODO: replace legacy settings placeholder with real business cases "
    "once testcase coverage is defined"
)


pytestmark = pytest.mark.skip(reason=TODO_PLACEHOLDER)


def test_settings_module_placeholder(settings_page) -> None:
    """Legacy TODO placeholder kept until the old testcase scaffold is migrated."""
    assert settings_page.module_name == "settings"
