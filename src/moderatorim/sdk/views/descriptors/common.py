"""Shared leaf view descriptors (Field + FormOverview).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Field:
    """A view's reference to one of the model's columns, plus view-only options.

    This is NOT a storage column (that is ``TableColumn``, which owns the ``FieldType``). A
    ``Field`` only NAMES a column and carries how the VIEW treats it:

    * ``name`` — the model column name it renders.
    * ``order`` — sort key for field placement (ascending; lower first).
    * ``roles`` — field-level visibility gate (L3): shown only to a caller holding one of these
      roles (empty = visible to all who can see the page). Enforced at render via ``ctx.has_role``.
    * ``span`` — how many form columns this field spans in a ``FormFields`` block (Stage 2).
    * ``display_field`` — for a REF column, the target column to show as its label; defaults to the
      target's ``display=True`` column (convention).
    * ``help`` — helper/placeholder text; falls back to the column's own label.
    * ``read_only`` — VIEW-level lock: render this field non-editable even in a form's edit mode
      (e.g. a profile's ``email``, which is the login identity and changes via a separate verified
      flow). Independent of the column's own ``read_only``; composes by OR.
    * ``custom`` — ESCAPE HATCH (design §7.3): a ``(record) -> cell content`` callback that renders
      a computed / non-field List cell (a status badge, a derived value, an action button like
      admin's super-user toggle). RETURN A UI PRIMITIVE (``tag(...)`` / ``Raw(...)``) — a plain
      string is escaped as safe text (XSS-safe default), so HTML must be a ``Raw``/tag. When set,
      ``name`` is a synthetic COLUMN KEY + header label, no backing model column is required, and
      the cell is neither sortable nor filterable. List-only.
    """

    name: str
    order: int = 100
    roles: tuple[str, ...] = ()
    span: int = 1
    display_field: str = ""
    help: str = ""
    read_only: bool = False
    custom: Callable[[dict[str, Any]], Any] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Field.name must be a non-empty column name")
        if self.span < 1:
            raise ValueError("Field.span must be >= 1")

    @property
    def is_custom(self) -> bool:
        """True when this field renders via a ``custom`` callback (no backing model column)."""
        return self.custom is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class FormOverview:
    """A form child view: the record header (display-name + status). Empty on the create form."""

    order: int = 100
