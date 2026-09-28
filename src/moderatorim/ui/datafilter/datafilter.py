"""``DataFilter`` — the multi-field filter shell (ui-view-components).

A ``filter_list`` icon toggles a below-search panel holding the active filter conditions (each an
editable ServiceNow-style row) + an add-condition control + Apply. The condition ROWS are
``DataFilterCondition`` components the CALLER composes and passes in (component isolation —
DataFilter never imports another component); DataFilter owns only the shell, toggle, and Apply form.

Pure presentation (the ``Component`` contract). Apply hx-GETs the list region with every row's
composed ``f_<field>_<op>=value`` param (``datatable-filter.js`` composes the value name); a removed
row drops its param. The ``template_row`` is a hidden prototype the JS clones on "Add condition".
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag

_DEFAULT_REGION = "mim-list-region"


class DataFilter(Component):
    """The filter shell: an icon trigger + a collapsible below-search panel of editable condition
    rows (pre-built ``DataFilterCondition`` components) + Add + Apply.

    ``rows`` are the active conditions (one pre-filled row each; empty tuple → one blank starter is
    the caller's job or the template is cloned). ``template_row`` is the blank prototype cloned by
    the JS when adding a condition. ``row_path`` is only used to hint the JS; the rows carry their
    own hx wiring.
    """

    def __init__(
        self,
        rows: Sequence[Component | Raw | str],
        *,
        template_row: Component | Raw | str = "",
        base_path: str = "",
        region_id: str = _DEFAULT_REGION,
        has_fields: bool = True,
    ) -> None:
        self.rows = tuple(rows)
        self.template_row = template_row
        self.base_path = base_path
        self.region_id = region_id
        self.has_fields = has_fields

    def render(self) -> Raw:
        if not self.has_fields:
            return Raw("")

        rows_box = tag("div", *self.rows, **{"class": "mim-filter-rows"})
        controls = tag(
            "div",
            tag(
                "button",
                tag("i", "add"),
                " Add condition",
                **{"type": "button", "class": "button border small mim-filter-add"},
            ),
            tag(
                "button",
                "Apply",
                **{"type": "submit", "class": "button small mim-filter-apply"},
            ),
            **{"class": "mim-filter-controls"},
        )
        builder = tag(
            "div",
            rows_box,
            controls,
            **{"class": "mim-filter-builder", "data-region": self.region_id},
        )
        form_children: list[Any] = [builder]
        if self.template_row:
            form_children.append(
                tag("template", self.template_row, **{"class": "mim-filter-template"})
            )
        form = tag(
            "form",
            *form_children,
            **{
                "hx-get": self.base_path,
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "class": "mim-filter-form",
            },
        )

        # A button trigger (stays inline in the toolbar) + a SEPARATE full-width panel that toggles
        # open below the toolbar controls (datatable-filter.js toggles `.active`).
        trigger = tag(
            "button",
            tag("i", "filter_list"),
            **{
                "type": "button",
                "class": "button transparent circle mim-filter-toggle",
                "title": "Filters",
                "data-mim-filter-toggle": "true",
            },
        )
        panel = tag("div", form, **{"class": "mim-filter-panel"})
        return tag("div", trigger, panel, **{"class": "mim-list-filters"})
