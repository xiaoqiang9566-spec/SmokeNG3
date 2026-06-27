import pytest


TODO_PLACEHOLDER = (
    "TODO: replace legacy widget placeholder with real business cases "
    "once testcase coverage is defined"
)


pytestmark = pytest.mark.skip(reason=TODO_PLACEHOLDER)


def test_widget_module_placeholder(widget_page) -> None:
    """Legacy TODO placeholder kept until the old testcase scaffold is migrated."""
    assert widget_page.module_name == "widget"
