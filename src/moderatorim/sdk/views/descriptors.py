"""Declarative view descriptors — the app-facing API for model-driven views (Stage 1).

An app declares a page as a :class:`PageView` (a model + a root view) and maps paths to PageViews in
its ``routes.py`` via :class:`ViewRoute` (path + PageView + role gate). These are PURE DATA — no
rendering, no store access. Core reads them to generate List/Form/Calendar screens, gate them via
RBAC, and compose search/filter/sort/paginate into one ``ctx.store`` query.

Stage 1 ships :class:`Field` + :class:`ListView`; Form/Calendar descriptors arrive in later stages.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    """

    name: str
    order: int = 100
    roles: tuple[str, ...] = ()
    span: int = 1
    display_field: str = ""
    help: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Field.name must be a non-empty column name")
        if self.span < 1:
            raise ValueError("Field.span must be >= 1")


@dataclass(frozen=True, slots=True)
class ListView:
    """A table generated from ``fields`` (ordered), with mandatory list affordances.

    * ``fields`` — the columns to show, ordered by each :class:`Field`'s ``order``.
    * ``search`` — column names the free-text search box matches (OR, case-insensitive). Empty = no
      search box.
    * ``filters`` — an OPTIONAL RESTRICTION on the runtime filter builder. The List view offers an
      "add filter" builder over the model's own columns; the operators for each come from the
      column's ``FieldType`` (core owns the type→operator mapping). Leave ``filters`` EMPTY to make
      every filterable column pickable (the default); provide a tuple to LIMIT the picker to those
      columns (e.g. hide sensitive columns from filtering). Non-filterable types (JSON/LIST/LISTREF)
      are auto-excluded regardless.
    * ``sort`` — the initial ``(column, "asc"|"desc")`` order, or None for the store default.
    """

    fields: tuple[Field, ...] = ()
    search: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        if self.sort is not None and (len(self.sort) != 2 or self.sort[1] not in ("asc", "desc")):
            raise ValueError("ListView.sort must be (column, 'asc'|'desc')")

    @property
    def ordered_fields(self) -> tuple[Field, ...]:
        """Fields sorted by their declared ``order`` (stable)."""
        return tuple(sorted(self.fields, key=lambda f: f.order))


@dataclass(frozen=True, slots=True)
class PageView:
    """One page = one model + one root view (a :class:`ListView`, later a FormView / CalendarView).

    Access ``roles`` live on the :class:`ViewRoute` binding, NOT here — the same PageView can be
    bound at several paths with different gates (list vs new vs edit)."""

    model: object  # a TableModel; typed as object so the SDK view layer needn't import models
    view: object  # a ListView (Stage 1); FormView / CalendarView later

    def __post_init__(self) -> None:
        if self.model is None:
            raise ValueError("PageView.model is required")
        if self.view is None:
            raise ValueError("PageView.view is required")


@dataclass(frozen=True, slots=True)
class ViewRoute:
    """A ``routes.py`` entry mapping a path to a :class:`PageView` + its RBAC gate.

    Named ``ViewRoute`` (not ``Route``) so it never collides with the web framework's route type in
    core. Core resolves new-vs-edit from the path shape (``/x`` list, ``/x/new`` create, ``/x/{id}``
    edit) — see the routing framework.
    """

    path: str
    view: PageView
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("ViewRoute.path must be non-empty")
