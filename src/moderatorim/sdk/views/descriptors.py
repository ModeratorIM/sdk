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
from enum import StrEnum
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
    * ``enable_actions`` — whether to render per-row Edit/Delete + the New button (default True).
      Set False for a READ-ONLY list that has no paired ``form_view`` (e.g. a catalog, or a list
      whose records are managed elsewhere) — otherwise a caller holding ``.update``/``.create``
      would see action controls linking to form routes that do not exist. A suppress-only VETO:
      permission (``ctx.can``) decides whether the CRUD buttons show; this only forces them off.
      Independent of permission gating.
    """

    fields: tuple[Field, ...] = ()
    search: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None
    enable_actions: bool = True

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
    """One GENERATED model-driven route: a path bound to a :class:`PageView` (model + view); NO
    handler — core expands it into the query→store→render flow. Each expanded sub-route (list GET,
    create ``POST`` on the collection, ``/{id}`` GET/PATCH/DELETE) gates on its OWN single full
    permission, supplied by the expansion from the resource prefix — no verb is inferred at
    enforcement.

    Named ``ViewRoute`` (not ``Route``) so it never collides with the web framework's route type in
    core. Core resolves new-vs-edit from the path shape (``/x`` list, ``/x/new`` create, ``/x/{id}``
    edit) — see the routing framework.

    GATE — ``permission``: the SINGLE capability the LIST route requires, a full key (e.g.
    ``"admin.users.read"``). Leave it ``None`` (the norm) and the generated expansion supplies each
    op its own single permission from the resource prefix — list/detail GET → ``.read``, create →
    ``.create``, update → ``.update``, delete → ``.delete`` — so a viewer holding only ``.read`` can
    view records but is denied create/update/delete. Set ``permission`` only to OVERRIDE the list
    op's gate. ROLES are never declared here — they are granted at RUNTIME in RBAC data.
    """

    path: str
    view: PageView
    permission: Permission | str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("ViewRoute.path must be non-empty")


class PermissionAction(StrEnum):
    """The CRUD capability a :class:`Permission` grants — the ``{action}`` segment of a permission
    key. A ``StrEnum`` (Python 3.11+): each member compares and serializes AS its lowercase verb
    (``PermissionAction.READ == "read"``), so a :class:`Permission` renders straight to the string
    key core enforces.

    DISTINCT from :class:`RouteMethod` (the HTTP transport): a permission's action is a capability
    fact, not the wire verb. The two are not 1:1 — a ``GET`` create-form route needs
    ``PermissionAction.CREATE``, and create/update/delete arrive over ``POST``/``PATCH``/``DELETE``
    — so reusing the HTTP-method enum here would re-introduce the method→verb coupling the gate
    model deliberately removed. Keep them separate: ``RouteMethod`` is transport,
    ``PermissionAction`` is capability.
    """

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class Permission:
    """A structured permission key — the typed, model-driven replacement for a hand-written dotted
    string like ``"admin.users.create"``. Renders to that exact string via :meth:`__str__`, so it is
    type-safe at the authoring layer and a plain key at the enforcement seam (the same pattern as
    :class:`RouteMethod` passing straight to the framework).

    The key is ``{source}.{resource}.{action}``:

    * ``source`` — the declaring UNIT's name (its ``Manifest.name``): an app, backend, or platform
      alike (e.g. ``"admin"``, ``"moderation"``). This is the ``{X}`` namespace segment; it is
      DECLARED explicitly, never derived from the folder — a silently-derived prefix a developer
      forgets is the same foot-gun as a hidden table prefix.
    * ``resource`` — the thing acted on (e.g. ``"users"``).
    * ``action`` — the CRUD :class:`PermissionAction` (``READ``/``CREATE``/``UPDATE``/``DELETE``).

    A unit's full permission catalog generates itself instead of being hand-typed::

        _PERMISSIONS = tuple(
            Permission(source="admin", resource=r, action=a)
            for r in ("users", "roles", "groups")
            for a in PermissionAction
        )

    A :class:`Route` / :class:`ViewRoute` ``permission`` accepts a ``Permission`` or a bare ``str``;
    core normalizes with ``str()`` and compares the rendered key, so enforcement is unchanged.
    """

    source: str
    resource: str
    action: PermissionAction

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("Permission.source must be non-empty (the declaring unit's name)")
        if not self.resource:
            raise ValueError("Permission.resource must be non-empty")

    def __str__(self) -> str:
        return f"{self.source}.{self.resource}.{self.action}"


class RouteMethod(StrEnum):
    """The HTTP method a :class:`Route` serves. A ``StrEnum`` (Python 3.11+): each member compares
    and serializes AS its string (``RouteMethod.GET == "GET"``), so it passes straight to the
    framework boundary (Starlette ``methods=[route.method]``) with no conversion — type safety at
    the authoring layer, a plain string at the framework seam.

    ``GET`` = a page (returns a Page); ``POST`` / ``PATCH`` / ``DELETE`` = a mutation / re-render
    (returns Redirect | Rendered). The verb carries the operation on a RESTful resource: ``POST``
    creates on the collection, ``PATCH`` updates the record at ``/{id}``, ``DELETE`` removes it —
    no ``/delete`` path suffix. The app is htmx-driven, so the edit/delete controls issue these via
    ``hx-patch`` / ``hx-delete`` (an HTML ``<form>`` alone could only GET/POST)."""

    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True, slots=True)
class Route:
    """One CUSTOM route: a ``path`` served by a hand-written ``handler``, keyed by ``method``.
    GET returns a :class:`~moderatorim.sdk.Page`; POST / PATCH / DELETE return a
    :class:`~moderatorim.sdk.Redirect` / :class:`~moderatorim.sdk.Rendered`. Replaces the
    ``@app.page`` / ``@app.action`` / ``@app.post`` decorators and the old standalone
    ``PageRoute`` and the old ``RouteAction`` — one item object, method-driven, so a domain's
    ``routes.py`` is a uniform tuple of declarations.

    * ``path`` — the URL path (must be non-empty).
    * ``handler`` — an ``async (ctx) -> Page | Redirect | Rendered`` callable (required).
    * ``method`` — :class:`RouteMethod`. GET renders a page; POST/PATCH/DELETE perform a mutation /
      in-place re-render. One Route = one method.
    * ``title`` — GET pages only: the document ``<title>``.
    * ``nav`` — GET pages only: contribute a gate-aware left-rail nav entry (shown when the gate
      passes).
    * ``permission`` — the GATE.

    GATE — ``permission``: the SINGLE app/system-level capability this route REQUIRES, a full key
    (e.g. ``"admin.users.create"``). The caller passes when their RESOLVED permission set (derived
    from the roles granted to them) contains it. ``None`` ⇒ ungated (public, e.g. ``/signin``). One
    route requires one permission — to ACCESS a record you need ``.read`` (the GET page), and each
    mutating route names the one capability its action needs (``.create`` / ``.update`` /
    ``.delete``). The permission is a fact about the ROUTE, declared at code-time; ROLES (user-level
    bundles of permissions) are NOT declared here — they are granted at RUNTIME in RBAC data
    (users→groups→roles→permissions). A viewer holding only ``.read`` is denied create/update/delete
    because they don't hold those permissions. There is no method→verb inference — the required
    capability is always the explicit full ``permission``.
    """

    path: str
    handler: object  # async (ctx) -> Page | Redirect | Rendered
    method: RouteMethod = RouteMethod.GET
    title: str | None = None
    nav: str | None = None
    permission: Permission | str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("Route.path must be non-empty")
        if self.handler is None:
            raise ValueError("Route.handler is required")


@dataclass(frozen=True, slots=True)
class PageRoute:
    """A domain's ROUTE BUNDLE — the declarative replacement for ``app.mount(...)``. Groups the
    generated ``views`` (:class:`ViewRoute`) + custom ``routes`` (:class:`Route`) + the default
    resource ``permission`` prefix (+ an optional ``enrich`` hook for the views' lists). A domain's
    ``register()`` RETURNS one; core collects it and expands every item. Pure declaration — no
    ``app`` handle, no imperative call.

    * ``views`` — generated model-driven routes (:class:`ViewRoute`).
    * ``routes`` — custom hand-written routes (:class:`Route`).
    * ``permission`` — the default resource permission PREFIX for this bundle (documentation /
      grouping; e.g. ``"admin.roles"``). Not a gate itself — each route declares its own single
      ``permission``.
    * ``enrich`` — optional ``async (ctx, rows) -> None`` hook applied to the bundle's list views
      (attach per-row computed data before render).

    NOTE: this REPURPOSES the name ``PageRoute`` (was: a single custom GET page). Every old
    ``PageRoute(path=, handler=)`` is now a :class:`Route` ``(path=, handler=)``; ``PageRoute``
    graduates to the bundle.
    """

    views: tuple[ViewRoute, ...] = ()
    routes: tuple[Route, ...] = ()
    permission: str | None = None  # default resource prefix (documentation/grouping)
    enrich: object | None = None  # optional async (ctx, rows) -> None for views' lists
