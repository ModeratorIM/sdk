"""Routing + permission descriptors (Route, ViewRoute, PageRoute, Permission).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moderatorim.sdk.views.descriptors.view import PageView


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


# --- Dashboard visuals (dashboard-visuals spec) ------------------------------------------------
# Server-rendered SVG widgets. Each widget BINDS to a table the same way PageView.model does: via a
# MetricSource/SeriesSource whose `model` names the table and `filters` (reusing Filter/FilterOp)
# restrict it. The engine resolves the aggregate through ctx.store (table-ACL enforced); no app
# query in the common case. (See specs/moderatorim/dashboard-visuals.)
