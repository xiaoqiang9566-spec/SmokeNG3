import pytest


TODO_PLACEHOLDER = (
    "TODO: replace legacy sport placeholder with real business cases "
    "once testcase coverage is defined"
)


pytestmark = pytest.mark.skip(reason=TODO_PLACEHOLDER)


def test_sport_module_placeholder(sport_page) -> None:
    """Legacy TODO placeholder kept until the old testcase scaffold is migrated."""
    assert sport_page.module_name == "sport"
