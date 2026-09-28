"""``DataFilter`` — a reusable multi-field filter component (ui-view-components).

A ``filter_list`` icon button toggles an expandable region (rendered BELOW the search row) that
shows the currently-active conditions as **removable chips** plus an add-condition builder (each
row: field + operator + value). The query engine reads ``f_<field>_<op>=value`` params, so Apply
hx-GETs the list region with every condition's composed param; a removed chip drops its param.

Pure presentation (the ``Component`` contract: ``render() -> Raw``, composes via ``tag``, imports
only ``component`` + ``html``). The dynamic add/remove + per-field operators are driven by
``datatable-filter.js``. Active conditions are pre-rendered (chips + hidden params) so a region
swap re-applies them without JS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag

_DEFAULT_REGION = "mim-list-region"


@dataclass(frozen=True, kw_only=True)
class FilterField:
    """One filter-able field: its key, header label, and the operator tokens valid for its type."""

    key: str
    label: str
    ops: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class FilterState:
    """Multi-field filter state. ``fields`` are the pickable columns (each with its own operator
    set); ``active`` are the applied conditions as ``(field, op, value)`` triples."""

    fields: tuple[FilterField, ...] = ()
    active: tuple[tuple[str, str, str], ...] = ()


class DataFilter(Component):
    """The multi-field filter control: an icon trigger + a collapsible below-search region with
    removable active-condition chips and an add-condition builder."""

    def __init__(
        self, state: FilterState, *, base_path: str = "", region_id: str = _DEFAULT_REGION
    ) -> None:
        self.state = state
        self.base_path = base_path
        self.region_id = region_id

    def _ops_catalogue(self) -> str:
        return ";".join(f"{ff.key}:{','.join(ff.ops)}" for ff in self.state.fields)

    def _label_for(self, key: str) -> str:
        return next((ff.label for ff in self.state.fields if ff.key == key), key)

    def _chip(self, fld: str, op: str, val: str) -> Any:
        """A removable chip for one active condition. Carries a hidden input with the composed
        ``f_<field>_<op>`` name so the condition re-submits on Apply; the ✕ removes the chip."""
        return tag(
            "span",
            tag("span", f"{self._label_for(fld)} {op} {val}", **{"class": "mim-filter-chip-text"}),
            tag(
                "button",
                tag("i", "close"),
                **{"type": "button", "class": "mim-filter-chip-remove", "title": "Remove"},
            ),
            tag("input", **{"type": "hidden", "name": f"f_{fld}_{op}", "value": val}),
            **{"class": "chip small mim-filter-chip"},
        )

    def _condition_row(self, selected: tuple[str, str, str] | None = None) -> Any:
        """One field+op+value builder row. field/op are chosen client-side; the JS composes the
        value input's ``f_<field>_<op>`` name on change/submit."""
        f = self.state
        sel_field, sel_op, sel_val = selected or ("", "", "")
        field_opts = [
            tag(
                "option",
                ff.label,
                **(
                    {"value": ff.key, "selected": "selected"}
                    if ff.key == sel_field
                    else {"value": ff.key}
                ),
            )
            for ff in f.fields
        ]
        current = next(
            (ff for ff in f.fields if ff.key == sel_field), f.fields[0] if f.fields else None
        )
        op_opts = []
        if current:
            for op in current.ops:
                op_opts.append(
                    tag(
                        "option",
                        op,
                        **(
                            {"value": op, "selected": "selected"} if op == sel_op else {"value": op}
                        ),
                    )
                )
        return tag(
            "div",
            tag("select", *field_opts, **{"class": "mim-filter-field"}),
            tag("select", *op_opts, **{"class": "mim-filter-op"}),
            tag("input", **{"type": "text", "class": "mim-filter-value", "value": sel_val}),
            tag(
                "button",
                tag("i", "close"),
                **{"type": "button", "class": "button transparent circle small mim-filter-remove"},
            ),
            **{"class": "mim-filter-row"},
        )

    def render(self) -> Raw:
        f = self.state
        if not f.fields:
            return Raw("")

        # Active conditions as removable chips (each carries its hidden f_field_op param).
        chips = [self._chip(fld, op, val) for fld, op, val in f.active]
        chip_bar = tag("div", *chips, **{"class": "mim-filter-chips"})

        # The add-condition builder: an empty row + Add + Apply.
        builder = tag(
            "div",
            tag("div", self._condition_row(), **{"class": "mim-filter-rows"}),
            tag(
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
            ),
            **{
                "class": "mim-filter-builder",
                "data-region": self.region_id,
                "data-ops": self._ops_catalogue(),
            },
        )
        form = tag(
            "form",
            chip_bar,
            builder,
            tag("template", self._condition_row(), **{"class": "mim-filter-template"}),
            **{
                "hx-get": self.base_path,
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "class": "mim-filter-form",
            },
        )

        # The expandable region lives BELOW the search: a <details> whose <summary> is the icon
        # trigger; the panel (form) spans the full toolbar width beneath the search row.
        return tag(
            "details",
            tag(
                "summary",
                tag("i", "filter_list"),
                **{"class": "button transparent circle mim-filter-toggle", "title": "Filters"},
            ),
            tag("div", form, **{"class": "mim-filter-panel"}),
            **{"class": "mim-list-filters"},
        )
