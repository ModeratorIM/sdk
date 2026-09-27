"""Declarative view descriptors — the app-facing API for model-driven views (Stage 1).

An app declares a page as a :class:`PageView` (a model + a root view) and maps paths to PageViews in
its ``routes.py`` via :class:`ViewRoute` (path + PageView + role gate). These are PURE DATA — no
rendering, no store access. Core reads them to generate List/Form/Calendar screens, gate them via
RBAC, and compose search/filter/sort/paginate into one ``ctx.store`` query.

Stage 1 ships :class:`Field` + :class:`ListView`; Form/Calendar descriptors arrive in later stages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from moderatorim.sdk.models.field import TableColumn


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
    * ``row_actions`` — whether to render per-row Edit/Delete + the New button (default True). Set
      False for a READ-ONLY list that has no paired ``form_view`` (e.g. a catalog, or a list whose
      records are managed elsewhere) — otherwise a caller holding ``.update``/``.create`` would see
      action controls linking to form routes that do not exist. Independent of permission gating.
    """

    fields: tuple[Field, ...] = ()
    search: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None
    row_actions: bool = True

    def __post_init__(self) -> None:
        if self.sort is not None and (len(self.sort) != 2 or self.sort[1] not in ("asc", "desc")):
            raise ValueError("ListView.sort must be (column, 'asc'|'desc')")

    @property
    def ordered_fields(self) -> tuple[Field, ...]:
        """Fields sorted by their declared ``order`` (stable)."""
        return tuple(sorted(self.fields, key=lambda f: f.order))


# --- Form view (Stage 2) -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FormFields:
    """A form child view: renders the record's OWN fields in a ``columns``-wide grid.

    Widget per field comes from the model column's ``FieldType`` (core owns the mapping). Fields
    auto-flow across ``columns`` by their ``order``; ``Field(span=k)`` widens one. ``columns``
    (default 1) collapses to 1 on mobile — it lives HERE, not on the tab or the FormView.
    """

    fields: tuple[Field, ...] = ()
    columns: int = 1
    order: int = 100

    def __post_init__(self) -> None:
        if self.columns < 1:
            raise ValueError("FormFields.columns must be >= 1")


@dataclass(frozen=True, slots=True)
class FormOverview:
    """A form child view: the record header (display-name + status). Empty on the create form."""

    order: int = 100


@dataclass(frozen=True, slots=True)
class FormTab:
    """One tab of a :class:`FormView`. Holds an ordered list of child views (``views``).

    The lowest-``order`` tab (conventionally ``Detail``) is the default shown on load. ``roles``
    gates the tab's own visibility at render (layer 3, via ``ctx.has_role``) — a viewer lacking the
    role simply doesn't see the tab.
    """

    label: str
    views: tuple[object, ...] = ()  # FormFields / FormOverview (later: embedded ListView / custom)
    order: int = 100
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("FormTab.label is required")

    @property
    def ordered_views(self) -> tuple[object, ...]:
        return tuple(sorted(self.views, key=lambda v: getattr(v, "order", 100)))


@dataclass(frozen=True, slots=True)
class FormAction:
    """A declared button on a form, invoking ``handler`` (a ``@app.action``-style callable) — gated
    by ``roles`` at render (layer 3). E.g. the admin super-user toggle."""

    label: str
    handler: object  # a callable core binds to {path}/{id}/action/{name}
    roles: tuple[str, ...] = ()
    order: int = 100

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("FormAction.label is required")
        if self.handler is None:
            raise ValueError("FormAction.handler is required")


@dataclass(frozen=True, slots=True)
class FormView:
    """A single root form view composed of :class:`FormTab`s (ordered) + declared ``actions``.

    New and Edit share one FormView — edit pre-fills from the resolved record; create renders empty
    (``ctx.is_new``). The first tab (lowest order) is the default.
    """

    tabs: tuple[FormTab, ...] = ()
    actions: tuple[FormAction, ...] = ()

    def __post_init__(self) -> None:
        if not self.tabs:
            raise ValueError("FormView requires at least one FormTab")

    @property
    def ordered_tabs(self) -> tuple[FormTab, ...]:
        return tuple(sorted(self.tabs, key=lambda t: t.order))

    @property
    def ordered_actions(self) -> tuple[FormAction, ...]:
        return tuple(sorted(self.actions, key=lambda a: a.order))


@dataclass(frozen=True, slots=True)
class ViewExtension:
    """A cross-app injection into another resource's Form (design §5b), keyed by the target form's
    base path (e.g. ``/shop/orders``). The extending app OWNS the injected tabs/actions — they are
    gated by their own ``roles`` (a FormTab's / FormAction's ``roles``), resolved at boot, merged
    into the target FormView's tabs/actions (by ``order``), and disappear when the app is
    uninstalled. Injection does NOT change page access — the target's own route gate still applies.
    """

    target: str  # the target form's base path
    add_tabs: tuple[FormTab, ...] = ()
    add_actions: tuple[FormAction, ...] = ()

    def __post_init__(self) -> None:
        if not self.target:
            raise ValueError("ViewExtension.target (the target form's base path) is required")


@dataclass(frozen=True, slots=True)
class CalendarView:
    """A month calendar over a model (design §6). Renders records as events positioned by a
    DATE/DATETIME ``start_field``; ``title_field`` is the event label; optional ``end_field`` spans
    multi-day events. v1 = server-rendered month grid + prev/next navigation (``?month=YYYY-MM``);
    clicking an event opens the record's edit Form, an empty day opens the new Form with the date
    pre-filled. Fetches the month's records with a date-range filter under the hood.
    """

    start_field: str
    title_field: str
    end_field: str | None = None

    def __post_init__(self) -> None:
        if not self.start_field:
            raise ValueError("CalendarView.start_field (the DATE/DATETIME field) is required")
        if not self.title_field:
            raise ValueError("CalendarView.title_field (the event label field) is required")


@dataclass(frozen=True, slots=True)
class ViewModel:
    """A READ-ONLY reference to a table a view reads — NOT a model declaration.

    A view often lists a table another unit OWNS (e.g. the admin app lists ``core_user``). The app
    must not declare a :class:`~moderatorim.sdk.TableModel` for it: that would MINT the table into
    ``manifest.models`` and the boot ownership guard forbids a non-owning unit declaring a foreign
    (``{other}_``) table. A ``ViewModel`` is a REFERENCE instead — the same "declare vs reference"
    line the guard already draws for ``permission=`` strings — carrying just the column metadata the
    view engine needs (name, type, label, relation, choices, display). It is never provisioned and
    never validated for ownership; it only describes columns the view renders/filters.

    Exposes the same read surface the engine uses on a ``TableModel`` (``name`` / ``column_map`` /
    ``display_label``), so it is a drop-in for :class:`PageView`'s ``model``.
    """

    name: str  # the physical table it reads (may be another unit's, e.g. "core_user")
    columns: tuple[TableColumn, ...] = ()
    label: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ViewModel.name (the table it reads) is required")

    @property
    def column_map(self) -> dict[str, TableColumn]:
        return {c.name: c for c in self.columns}

    @property
    def display_label(self) -> str:
        if self.label:
            return self.label
        tail = self.name.split("_", 1)[-1] if "_" in self.name else self.name
        return tail.replace("_", " ").title()


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


@dataclass(frozen=True, slots=True)
class RouteAction:
    """A ``routes.py`` entry declaring a STANDALONE route-action (design §1) — a POST endpoint at
    ``path`` invoking ``handler``, NOT attached to a generated form's record (the ``@app.action``
    kind).

    Named ``RouteAction`` (not ``Action``) so it never collides with the bus/event ``Action``. It is
    the declarative form of ``@app.action``: put these in an app's ``actions.py`` as a tuple and
    hand them to ``App.mount(actions=…)`` alongside the ``ViewRoute`` table. Distinct from
    :class:`FormAction`, a button INSIDE a form (bound to a record at ``{base}/{id}/action``); a
    ``RouteAction`` is a page-level mutation at its own path (e.g. ``/admin/roles/define``).

    Gating: ``roles`` (route role gate, §1b L2) when set, else ``permission`` (the CRUD prefix).
    """

    path: str
    handler: object  # a callable (ctx) -> Redirect|Rendered, like an @app.action body
    permission: str | None = None
    roles: tuple[str, ...] = ()
    methods: tuple[str, ...] = ("POST",)

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("RouteAction.path must be non-empty")
        if self.handler is None:
            raise ValueError("RouteAction.handler is required")
