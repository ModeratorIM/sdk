"""Type -> widget rendering + validator generation for a model ``TableColumn``.

The bridge from a STORAGE column (``moderatorim.sdk.models.TableColumn``) to a UI control: given a
column and an optional current value, emit the right BeerCSS primitive. Also generates the
server-side validators implied by the column (required / max_length / choices / …) so the same
declaration drives rendering AND enforcement.

Layer note: this consumes ``moderatorim.ui`` primitives and the SDK model contract — it does NOT
live in the SDK models domain (which must stay UI-free).
"""

from __future__ import annotations

from typing import Any

from moderatorim.sdk import FieldType, TableColumn
from moderatorim.sdk.validation.rules import MaxLength, OneOf, Required, Validator
from moderatorim.ui.component import Component
from moderatorim.ui.input import Input
from moderatorim.ui.pills import Pills
from moderatorim.ui.select import Select
from moderatorim.ui.switch import Switch
from moderatorim.ui.textarea import Textarea

# FieldType -> the HTML <input type=...> for the types that map onto a plain input.
_INPUT_TYPES: dict[FieldType, str] = {
    FieldType.TEXT: "text",
    FieldType.INTEGER: "number",
    FieldType.FLOAT: "number",
    FieldType.DATE: "date",
    FieldType.DATETIME: "datetime-local",
}


def column_validators(column: TableColumn) -> list[Validator]:
    """Server-side validators implied by the column declaration."""
    out: list[Validator] = []
    if column.required:
        out.append(Required())
    if column.max_length is not None:
        out.append(MaxLength(column.max_length))
    if column.type is FieldType.ENUM and column.choices:
        out.append(OneOf(tuple(column.choices)))
    return out


def render_column(
    column: TableColumn,
    value: Any = None,
    *,
    options: list[tuple[str, str]] | None = None,
    selected: list[tuple[str, str]] | None = None,
    label: str | None = None,
) -> Component:
    """Render one column as its default widget.

    ``options`` supplies (id, label) candidates for ENUM/REF/LISTREF pickers; ``selected`` supplies
    the currently-chosen (id, label) pairs for a LISTREF. The referenced-table ACL filtering that
    produces ``options`` is the caller's responsibility (it needs a store + the request principal).
    ``label`` overrides the field label: ``None`` (default) uses the column's own label/name; pass
    ``""`` to render the control WITHOUT a label (e.g. a filter value where the field is named
    elsewhere).
    """
    label = (column.label or column.name) if label is None else label
    t = column.type

    if t is FieldType.BOOLEAN:
        return Switch(column.name, label=label, checked=bool(value), disabled=column.read_only)

    if t is FieldType.TEXTAREA:
        return Textarea(
            column.name,
            label=label,
            value="" if value is None else str(value),
            required=column.required,
            disabled=column.read_only,
        )

    if t is FieldType.ENUM:
        opts = options or [(c, c) for c in column.choices]
        return Select(column.name, opts, label=label, value="" if value is None else str(value))

    if t is FieldType.REF:
        # A single relation picker == a select of candidate records (id, display).
        return Select(
            column.name, options or [], label=label, value="" if value is None else str(value)
        )

    if t is FieldType.LISTREF:
        picker = Select(f"{column.name}__add", options or [], label="") if options else ""
        return Pills(
            column.name, selected or [], label=label, picker=picker, disabled=column.read_only
        )

    # TEXT / INTEGER / FLOAT / DATE / DATETIME / OBJECT -> a plain input of the mapped html type.
    extra: dict[str, Any] = {"readonly": True} if column.read_only else {}
    return Input(
        column.name,
        label=label,
        value="" if value is None else str(value),
        type=_INPUT_TYPES.get(t, "text"),
        required=column.required,
        validators=column_validators(column),
        **extra,
    )
