"""``DataFilterCondition`` — one ServiceNow-style filter condition row (ui-view-components).

A ``[field ▾] [operator ▾] [typed value]`` row. Changing the FIELD hx-GETs a per-row endpoint that
re-renders the whole row for the new field's type — the operator list AND the value control both
update, the value control via the SAME renderer the FormView uses
(:func:`moderatorim.ui.render.render_column`): a REF field → a select of candidates, BOOLEAN →
a true/false control, ENUM → its choices, date → a date input, etc. No type→widget logic is
duplicated in JS; the server owns it, exactly like ServiceNow's server round-trip.

Composed by ``DataFilter``. Pure presentation (the ``Component`` contract). The value control's
submit ``name`` is composed to ``f_<field>_<op>`` by ``datatable-filter.js`` (operator picked
client-side); a pre-rendered active row already carries the composed name so a region swap
re-applies it without JS.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from moderatorim.sdk import TableColumn
from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag
from moderatorim.ui.render import render_column


@dataclass(frozen=True, kw_only=True)
class ConditionField:
    """One pickable field for a condition row: its column (drives the typed value input via
    ``render_column``), the operator tokens valid for its type, and optional (id,label) options for
    a REF/ENUM value select (the caller resolves ACL-filtered candidates)."""

    column: TableColumn
    ops: tuple[str, ...]
    options: list[tuple[str, str]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.column.name

    @property
    def label(self) -> str:
        return self.column.label or self.column.name.replace("_", " ").title()


class DataFilterCondition(Component):
    """One ServiceNow-style condition row: field ▾ / operator ▾ / typed value / remove. Changing the
    field select hx-GETs ``row_path?field=<key>`` and swaps this row's outerHTML with the re-typed
    row. ``fields`` is the full pickable set (for the field select); ``selected`` is the active
    field; ``op`` / ``value`` prefill the operator + value on a re-render / active condition."""

    def __init__(
        self,
        fields: Sequence[ConditionField],
        *,
        selected: str = "",
        op: str = "",
        value: Any = None,
        row_path: str = "",
        region_id: str = "mim-list-region",
    ) -> None:
        self.fields = tuple(fields)
        self.selected = selected or (self.fields[0].key if self.fields else "")
        self._current = next(
            (f for f in self.fields if f.key == self.selected),
            self.fields[0] if self.fields else None,
        )
        self.op = op or (self._current.ops[0] if self._current and self._current.ops else "")
        self.value = value
        self.row_path = row_path
        self.region_id = region_id

    def _field_select(self) -> Raw:
        opts = [
            tag(
                "option",
                f.label,
                **(
                    {"value": f.key, "selected": "selected"}
                    if f.key == self.selected
                    else {"value": f.key}
                ),
            )
            for f in self.fields
        ]
        # Changing the field re-renders THIS row from the server (ServiceNow round-trip): the value
        # control + operator list come back typed for the new field. Targets the closest row.
        # Beer CSS styles a select via a `.field suffix border` WRAPPER (+ arrow), not classes on
        # the bare <select> — so wrap it (small round for the compact filter look).
        select = tag(
            "select",
            *opts,
            **{
                "class": "mim-filter-field",
                "name": "field",
                "hx-get": self.row_path,
                "hx-target": "closest .mim-filter-row",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
            },
        )
        return tag(
            "div", select, tag("i", "arrow_drop_down"), class_="field suffix border small round"
        )

    # Human labels for the query-param operator tokens (value stays the token for the engine).
    _OP_LABELS = {
        "eq": "is",
        "ne": "is not",
        "lt": "less than",
        "lte": "at most",
        "gt": "greater than",
        "gte": "at least",
        "contains": "contains",
    }

    def _operator_select(self) -> Raw:
        ops = self._current.ops if self._current else ()
        opts = [
            tag(
                "option",
                self._OP_LABELS.get(op, op),
                **({"value": op, "selected": "selected"} if op == self.op else {"value": op}),
            )
            for op in ops
        ]
        select = tag("select", *opts, **{"class": "mim-filter-op"})
        return tag(
            "div", select, tag("i", "arrow_drop_down"), class_="field suffix border small round"
        )

    def _value_input(self) -> Any:
        """The type-aware value control via the shared ``render_column`` (same as FormView).
        Wrapped in ``.mim-filter-value`` so ``datatable-filter.js`` can rewrite the inner control's
        name to the composed ``f_<field>_<op>`` submit name."""
        if self._current is None:
            return tag("div", **{"class": "mim-filter-value"})
        control = render_column(
            self._current.column,
            self.value,
            options=self._current.options or None,
            label="",  # the field is named by the field select; no redundant per-control label
        )
        return tag("div", control, **{"class": "mim-filter-value"})

    def render(self) -> Raw:
        return tag(
            "div",
            self._field_select(),
            self._operator_select(),
            self._value_input(),
            tag(
                "button",
                tag("i", "close"),
                **{"type": "button", "class": "button transparent circle small mim-filter-remove"},
            ),
            **{"class": "mim-filter-row", "data-field": self.selected},
        )
