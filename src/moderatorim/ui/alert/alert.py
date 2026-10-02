"""Alert component (Beer CSS inline notice)."""

from __future__ import annotations

from typing import Literal

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag


class Alert(Component):
    """An inline notice. ``error`` renders a red container, ``success`` a green one, ``info`` a
    neutral surface."""

    def __init__(
        self, message: str, *, variant: Literal["info", "error", "success"] = "info"
    ) -> None:
        self.message = message
        self.variant = variant

    def render(self) -> Raw:
        fill = {"error": "error", "success": "green", "info": "surface-variant"}[self.variant]
        return tag(
            "div", tag("span", self.message), class_=f"mim-alert padding {fill}", role="alert"
        )
