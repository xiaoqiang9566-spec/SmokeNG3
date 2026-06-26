from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class BasePage:
    def __init__(
        self,
        session: Any,
        resources: Mapping[str, str],
        navigation: Mapping[str, Sequence[str]],
    ) -> None:
        self.session = session
        self.resources = resources
        self.navigation = navigation

    def _read_content(self, key: str) -> Any:
        return self.session.read_json(self.resources[key]).get("Content")
