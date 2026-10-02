"""Typed model columns — the ``TableColumn`` declaration + the backend-neutral ``FieldType``
vocabulary.

A column carries enough type metadata for a relational backend to materialize storage and for a UI
layer to render an input. Types name intent (``REF``, ``LISTREF``, ``ENUM``), not a database's
column types — each backend maps them onto its own storage.

Naming (three things historically called ``Field``): this module owns the STORAGE column
(``TableColumn``). The VIEW-field reference (name/order/roles/…) lives in the views layer; the UI
label-wrapper primitive lives in ``moderatorim.ui.field``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldType(Enum):
    """The backend-neutral field-type vocabulary. An invalid member fails at import."""

    TEXT = "text"  # short, indexable string -> VARCHAR (bounded by max_length or backend default)
    TEXTAREA = "textarea"  # long / unbounded text -> TEXT
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    OBJECT = "object"  # arbitrary JSON blob -> JSONB
    ENUM = "enum"  # one of a fixed set of string choices (see TableColumn.choices)
    REF = "ref"  # reference to ONE record (see TableColumn.relation -> table name)
    LISTREF = "listref"  # list of references (many-to-many) -> auto join table


_STRING_TYPES = (FieldType.TEXT, FieldType.TEXTAREA)
_REF_TYPES = (FieldType.REF, FieldType.LISTREF)


@dataclass(frozen=True, slots=True)
class TableColumn:
    """A single typed column on a :class:`~moderatorim.sdk.models.TableModel`.

    Flat: type + constraints + presentation are all direct attributes (no nested type object).
    Frozen: a column declaration is immutable. All invariants are checked in ``__post_init__`` so a
    malformed declaration fails loudly at import/boot, not at schema-materialization time.
    """

    name: str
    type: FieldType
    label: str = ""
    required: bool = False
    unique: bool = False
    index: bool = False
    default: Any = None
    relation: str | None = None  # for REF/LISTREF: the target table name (app-namespaced)
    choices: tuple[str, ...] = ()  # for ENUM: the allowed string choices
    max_length: int | None = None  # for TEXT/TEXTAREA: VARCHAR(n), validated on save
    encrypt: bool = False  # at-rest encryption, store-honored
    active: bool = True  # shown in the UI (False = hidden from views/forms, NOT dropped)
    read_only: bool = False  # displayed but not editable
    display: bool = False  # THIS column is the record's display value (dropdowns / REF pickers)
    help: str = ""
    # Owning unit, FILLED BY CORE from the declaring model's manifest at boot (see
    # app-owned-columns design §1). Default None = "unattributed": authors never set it, and "no
    # source" does NOT mean core. Core stamps every column unconditionally with its manifest name
    # (core's models -> "core", an app's -> the app name), so a forgotten source can never
    # masquerade as core ownership. A None surviving to runtime means the column was materialized
    # outside any manifest (tests/ad-hoc).
    source: str | None = None

    def __post_init__(self) -> None:
        if self.type in _REF_TYPES and not self.relation:
            raise ValueError(f"{self.type.name} column {self.name!r} requires `relation`")
        if self.type not in _REF_TYPES and self.relation is not None:
            raise ValueError(f"`relation` is only valid on a REF/LISTREF column ({self.name!r})")

        if self.type is FieldType.ENUM and not self.choices:
            raise ValueError(f"ENUM column {self.name!r} requires non-empty `choices`")
        if self.type is not FieldType.ENUM and self.choices:
            raise ValueError(f"`choices` is only valid on an ENUM column ({self.name!r})")

        if self.max_length is not None and self.type not in _STRING_TYPES:
            raise ValueError(f"`max_length` is only valid on TEXT/TEXTAREA ({self.name!r})")
        if self.max_length is not None and self.max_length <= 0:
            raise ValueError(f"`max_length` must be positive ({self.name!r})")

        if self.active is False and self.required:
            raise ValueError(f"column {self.name!r} cannot be both required and active=False")

        _check_default_type(self)


def _check_default_type(col: TableColumn) -> None:
    """Validate `default` is consistent with the column's type (skip None — 'no default')."""
    d = col.default
    if d is None:
        return
    t = col.type
    if t is FieldType.BOOLEAN and not isinstance(d, bool):
        raise ValueError(f"BOOLEAN column {col.name!r} default must be a bool, got {d!r}")
    if t is FieldType.INTEGER and (isinstance(d, bool) or not isinstance(d, int)):
        raise ValueError(f"INTEGER column {col.name!r} default must be an int, got {d!r}")
    if t is FieldType.FLOAT and (isinstance(d, bool) or not isinstance(d, int | float)):
        raise ValueError(f"FLOAT column {col.name!r} default must be a number, got {d!r}")
    if t in _STRING_TYPES and not isinstance(d, str):
        raise ValueError(f"{t.name} column {col.name!r} default must be a str, got {d!r}")
    if t is FieldType.ENUM and d not in col.choices:
        raise ValueError(f"ENUM column {col.name!r} default {d!r} not in choices {col.choices}")


def text(name: str, *, required: bool = False, unique: bool = False, **kw: Any) -> TableColumn:
    """Convenience constructor for a short TEXT column."""
    return TableColumn(name=name, type=FieldType.TEXT, required=required, unique=unique, **kw)


def ref(
    name: str, table: str, *, required: bool = False, index: bool = True, **kw: Any
) -> TableColumn:
    """Convenience constructor for a REF column (relations are indexed by default)."""
    return TableColumn(
        name=name, type=FieldType.REF, relation=table, required=required, index=index, **kw
    )


def listref(name: str, table: str, **kw: Any) -> TableColumn:
    """Convenience constructor for a LISTREF column (many-to-many, join-backed, pill widget)."""
    return TableColumn(name=name, type=FieldType.LISTREF, relation=table, **kw)


def enum(
    name: str, *choices: str, required: bool = False, default: Any = None, **kw: Any
) -> TableColumn:
    """Convenience constructor for an ENUM column."""
    return TableColumn(
        name=name,
        type=FieldType.ENUM,
        choices=tuple(choices),
        required=required,
        default=default,
        **kw,
    )
