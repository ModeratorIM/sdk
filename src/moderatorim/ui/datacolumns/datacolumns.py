"""``DataColumns`` — a reusable column-visibility control (ui-view-components).

A ``view_column`` icon button opens a **Beer CSS popup menu** (a ``<menu>``, like the account menu)
listing every declared column with a checkbox (checked = currently shown); Save posts the checked
names to ``{base_path}/columns`` and swaps the list region. The menu is toggled by a swap-safe
delegated handler in ``datatable-filter.js``.

Pure presentation (the ``Component`` contract). ``options`` is the ordered ``(key, label, shown)``
set — the caller resolves which columns exist + which are currently visible.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag

_DEFAULT_REGION = "mim-list-region"
_MENU_ID = "mim-columns-menu"


@dataclass(frozen=True, kw_only=True)
class ColumnOption:
    """One offerable column: its key, human label, and whether it is currently shown."""

    key: str
    label: str
    shown: bool = True


class DataColumns(Component):
    """A column-visibility control: a ``view_column`` icon trigger + a Beer CSS popup menu of
    column checkboxes with Save."""

    def __init__(
        self,
        options: Sequence[ColumnOption],
        *,
        base_path: str = "",
        region_id: str = _DEFAULT_REGION,
    ) -> None:
        self.options = tuple(options)
        self.base_path = base_path
        self.region_id = region_id

    def render(self) -> Raw:
        if not self.options:
            return Raw("")
        checks = [
            tag(
                "label",
                tag(
                    "input",
                    "",
                    **{
                        "type": "checkbox",
                        "name": "col",
                        "value": o.key,
                        **({"checked": "checked"} if o.shown else {}),
                    },
                ),
                tag("span", o.label),
                **{"class": "mim-cols-item"},
            )
            for o in self.options
        ]
        form = tag(
            "form",
            *checks,
            tag("button", "Save", **{"type": "submit", "class": "button small"}),
            **{
                "hx-post": f"{self.base_path}/columns",
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "class": "mim-cols-form",
            },
        )
        # Beer CSS popup: a trigger button + a sibling <menu> in a positioned wrapper. The menu's
        # `.active` is toggled by a swap-safe delegated handler (datatable-filter.js).
        trigger = tag(
            "button",
            tag("i", "view_column"),
            **{
                "type": "button",
                "class": "button transparent circle mim-cols-toggle",
                "title": "Columns",
                "data-mim-columns-toggle": "true",
            },
        )
        menu = tag("div", form, **{"id": _MENU_ID, "class": "mim-cols-menu"})
        return tag("div", trigger, menu, **{"class": "mim-cols-editor"})
