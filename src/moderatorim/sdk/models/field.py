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


@dataclass(frozen=True, slots=True)
class FieldChoice:
    """One option of a :data:`FieldType.CHOICE` column — a structured static pick-list entry.

    Unlike a bare string, a choice separates what is STORED from what is SHOWN:

    * ``value`` — the stable identity written to the column (``core_user.type == "user"``). Never
      changes once rows reference it; this is what a ``CHOICE`` column stores (as text).
    * ``label`` — the human text shown in the dropdown. Renameable freely without touching stored
      rows, because rows hold ``value``, not ``label``.
    * ``name`` — an optional stable machine key for code comparisons (defaults to ``value``).
    * ``active`` — ``True`` by default. ``False`` RETIRES the option: it is hidden from new
      selections but a row already holding it stays valid (that is the whole point over an ENUM —
      you can drop an option without a data migration).
    * ``order`` — dropdown ordering, independent of ``value``/``label``.
    """

    value: str
    label: str
    name: str = ""
    active: bool = True
    order: int = 0

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("FieldChoice.value must be non-empty")
        if not self.label:
            raise ValueError(f"FieldChoice {self.value!r} requires a non-empty label")
        if not self.name:
            object.__setattr__(self, "name", self.value)  # default the machine key to value

    @property
    def key(self) -> str:
        """The stable machine key (``name``, falling back to ``value``)."""
        return self.name or self.value


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
    CHOICE = "choice"  # structured static pick-list (see TableColumn.choices -> FieldChoice tuple)
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
    choices: tuple[FieldChoice, ...] = ()  # for CHOICE: the allowed options (value/label/active/…)
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

        if self.type is FieldType.CHOICE:
            if not self.choices:
                raise ValueError(f"CHOICE column {self.name!r} requires non-empty `choices`")
            values = [c.value for c in self.choices]
            if len(values) != len(set(values)):
                raise ValueError(f"CHOICE column {self.name!r} has duplicate choice values")
        elif self.choices:
            raise ValueError(f"`choices` is only valid on a CHOICE column ({self.name!r})")

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
    if t is FieldType.CHOICE and d not in {c.value for c in col.choices}:
        raise ValueError(
            f"CHOICE column {col.name!r} default {d!r} not in choice values "
            f"{tuple(c.value for c in col.choices)}"
        )


# View-column-resolution R4: which TableColumn facets a VIEW may override on a column it does not
# own, vs which are storage truth owned by the declaring unit. A view re-SKINS (presentation); it
# never redefines storage shape — so two apps overriding the same column cannot conflict and a view
# cannot desync a column's type/choices from what is stored.
#
# OVERRIDABLE: presentation facets a view legitimately sets for its own render.
OVERRIDABLE_FACETS = frozenset({"label", "help", "display", "read_only", "active"})
# INHERIT-ONLY: owner storage truth. A view that needs a different one of these must ADD its own
# column, not override a foreign one. (`type` is positional on TableColumn so a delta always carries
# one; the resolver takes the BASE type and ignores a delta's — it is not listed here because it
# cannot be "unset" to detect, and overriding it is simply never honored.)
INHERIT_ONLY_FACETS = frozenset(
    {"relation", "choices", "required", "unique", "max_length", "encrypt", "default", "source"}
)


def assert_valid_override(delta: TableColumn) -> None:
    """Validate ``delta`` used as a VIEW OVERRIDE of an existing (owner-owned) base column.

    An override may carry only :data:`OVERRIDABLE_FACETS`; every :data:`INHERIT_ONLY_FACETS` facet
    must be left at its ``TableColumn`` default (unset). A non-default inherit-only facet means the
    author is trying to redefine storage truth from a view — rejected loudly (R4/R5), because that
    is exactly the drift/conflict this design forbids. (Only meaningful for an OVERRIDE — a column
    whose name matches a base column. A brand-new view-only ADDED column is a full declaration and
    is not checked here.)
    """
    _defaults = {
        "relation": None,
        "choices": (),
        "required": False,
        "unique": False,
        "max_length": None,
        "encrypt": False,
        "default": None,
        "source": None,
    }
    offenders = [f for f in INHERIT_ONLY_FACETS if getattr(delta, f) != _defaults[f]]
    if offenders:
        raise ValueError(
            f"view override of column {delta.name!r} may not set storage facet(s) "
            f"{sorted(offenders)} — those are owned by the table's declaring unit; override only "
            f"{sorted(OVERRIDABLE_FACETS)}, or ADD a new column instead"
        )


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


def choice(
    name: str,
    *choices: FieldChoice,
    required: bool = False,
    default: Any = None,
    **kw: Any,
) -> TableColumn:
    """Convenience constructor for a CHOICE column (structured static pick-list)."""
    return TableColumn(
        name=name,
        type=FieldType.CHOICE,
        choices=tuple(choices),
        required=required,
        default=default,
        **kw,
    )
