"""The ``Manifest`` contract — how a unit declares itself to the core.

Every installable unit exposes a module-level ``manifest`` of this type. The core reads it for the
unit's name, type, dependencies, models, inheritance, routes, permissions/roles, and store metadata
— without importing the unit's implementation until boot. The ``register(core)`` hook wires
services / subscribes to events; the optional ``routes(app)`` hook adds pages. Both touch only the
SDK surface, never core.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from moderatorim.sdk.models import Extends, TableModel

if TYPE_CHECKING:  # pragma: no cover - typing only (avoid a runtime import cycle)
    from moderatorim.sdk.views import PageRoute, Permission


def _no_register(_core: Any) -> None:
    """Default ``Manifest.register`` — a no-op, so apps that only DECLARE (models, subscriptions,
    routes) need not supply a hollow register hook. Override only for custom boot logic."""
    return None


class UnitType(Enum):
    """The three kinds of installable unit, ordered by layer (lower value = lower layer)."""

    BACKEND = 0  # persistence/auth/storage adapter
    PLATFORM = 1  # messaging-channel adapter
    APP = 2  # feature package (may depend on other apps)


@dataclass(frozen=True, slots=True)
class NavEntry:
    """A left-rail navigation entry an app contributes for the authenticated shell.

    ``icon`` is a Material Symbol name (``<i>``) or a path to the app's own icon asset (``<img>`` —
    a value with ``/`` or an image extension). ``permission`` gates visibility (None = always) and
    accepts a :class:`~moderatorim.sdk.Permission` or a bare key string — core normalizes it with
    ``str()`` (same as a route gate). ``order`` sorts entries (lower first); ties break on
    ``label``.
    """

    label: str
    path: str
    icon: str = ""
    permission: Permission | str | None = None
    order: int = 100
    badge: str | int | None = None
    # Placement: when True this entry is the app's ENTRY POINT in the account popup menu (gated by
    # ``permission``) instead of a tile in the global launcher rail. The app's other nav entries
    # still form its in-app (app-scoped) rail. Use for a management app reached via the account
    # menu rather than launched from the rail (e.g. admin). Default False = a launcher tile.
    is_popup_menu: bool = False

    @property
    def icon_is_asset(self) -> bool:
        """True when ``icon`` is an image asset path (``<img>``) rather than a Material Symbol."""
        return "/" in self.icon or self.icon.endswith((".svg", ".png", ".webp"))


@dataclass(frozen=True, slots=True)
class AuthMethod:
    """A sign-in method an app contributes to the public sign-in page (auth-methods spec).

    The sign-in page renders a button per method (sorted by ``order``; core's ``core.password`` is
    order 0 = first/default). Clicking a button reveals that method's ``form`` (rendered inline,
    hidden until clicked) OR navigates to its ``redirect_url`` (an OAuth-start redirect). Exactly
    one of ``form`` / ``redirect_url`` is set.

    ``form`` is a RENDERABLE (a zero-arg callable returning markup), not a URL — core builds it into
    the page at render time. A ``form`` method also registers its own POST handler via the unit's
    ``routes`` hook; it authenticates a principal then asks the core session service to establish
    the session (it never mints one itself).
    """

    id: str  # stable, app-namespaced id ("core.password", "sso.okta")
    label: str  # button text ("Email / Password", "Sign in with Okta")
    icon: str = ""  # leading icon (Material Symbol name)
    order: int = 100  # sort among methods (core.password = 0)
    form: Callable[[], Any] | None = None  # renders the method's inline form
    redirect_url: str = ""  # OR an OAuth-start redirect (no inline form)

    def __post_init__(self) -> None:
        has_form = self.form is not None
        has_redirect = bool(self.redirect_url)
        if has_form == has_redirect:
            raise ValueError(
                f"AuthMethod {self.id!r} must set exactly one of `form` or `redirect_url`"
            )


@dataclass(frozen=True, slots=True)
class Manifest:
    """A unit's self-declaration.

    ``register`` is the one-time boot hook. ``dependency`` names OTHER units this requires (by
    manifest name). ``models`` are the unit's own model classes; ``extends`` the inheritance links.
    ``routes`` is the optional ``register_routes(app)`` hook adding the unit's pages to the router.
    """

    name: str
    type: UnitType
    # The one-time boot hook. Historically ``register(core) -> None`` (imperative: wires services /
    # mounts routes on the passed handle). The declarative-routes migration widens this so a unit's
    # ``register()`` may instead RETURN its route bundle(s) — a ``PageRoute`` (the domain bundle) or
    # a tuple of them — which core COLLECTS and expands (design §2). Both call shapes coexist behind
    # the boot compatibility shim during the migration, so the annotation admits either.
    register: Callable[..., PageRoute | tuple[PageRoute, ...] | None] = _no_register
    version: str = "0.0.0"
    display_name: str = ""
    dependency: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    models: tuple[TableModel, ...] = ()
    extends: tuple[Extends, ...] = ()
    # Declarative event subscriptions (design §1): each Subscription(kind, factory) is wired at
    # boot — core calls factory(core) and subscribes the returned handler to kind. Replaces the
    # imperative register(core) + bus.subscribe(...) boilerplate (register is now optional).
    subscriptions: tuple[Any, ...] = ()
    store_metadata: dict[str, Any] = field(default_factory=dict)
    nav: tuple[NavEntry, ...] = ()
    # Sign-in methods this unit contributes to the public sign-in page (auth-methods spec). Core's
    # own core.password method is added by core, not declared here. Collected across units at boot.
    auth_methods: tuple[AuthMethod, ...] = ()
    # Stylesheet filenames the app ships in its static dir, injected into the <head> by core when
    # one of the app's pages is served (served from /static/apps/{name}/<file>). App-owned theming:
    # the app declares + ships the CSS; core serves it and links it. e.g. ("admin.css",).
    styles: tuple[str, ...] = ()
    # JavaScript filenames the app ships in its static dir, injected as <script type="module"> by
    # core when one of the app's pages is served (served from /static/apps/{name}/<file>), mirroring
    # ``styles``. App-GATED: injected ONLY while the app's pages are showing (not globally), so one
    # app's JS cannot run against another app. Because the shell is swapped by htmx on navigation,
    # the script re-executes on each in-app swap — so app JS MUST be swap-safe: bind DELEGATED
    # handlers on ``document`` and (re)apply stateful DOM on ``htmx:afterSettle``, never assume a
    # one-shot DOMContentLoaded. The app declares + ships the JS; core serves + links it.
    # e.g. ("admin.js",).
    scripts: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    # Roles this unit declares (seeded into the core RBAC catalog at boot): {role_name: (grants,)}.
    # Renamed from `default_roles` — the seeding-default semantics live in the docs, not the field.
    roles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Roles this unit's OWN service principal ("app:<name>") holds, for table-ACL (table-acl P3).
    # A unit's userless work (event handlers, cron, boot hooks) runs as the "app:<name>" principal;
    # these are the roles that principal is granted at boot (into core_role_granted), so it can
    # reach its own role-gated tables out of the box. Each MUST be a declared role (its own or a
    # dependency's); core validates + seeds them (apps declare, core decides).
    service_roles: tuple[str, ...] = ()
    # System users this unit ships: each maps a system-user NAME ("{app}.{user_name}",
    # e.g. "cron.user") to the group names it belongs to. Boot/install seeds each as a
    # type="system", un-loginable core_user and places it in those groups, so the unit's userless
    # work (event-bus subscribers, cron, webhooks, boot hooks) runs AS a real, least-privilege RBAC
    # principal. Core validates the "{app}" ownership prefix and seeds them (apps declare, core
    # decides) — the SDK only carries the declaration.
    system_users: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # When True, this unit is PRIVATE: ANY unauthorized access to one of its routes — whether the
    # caller is UNAUTHENTICATED or authenticated-WITHOUT the required permission, and whether a GET
    # page or a mutation — returns 404 (Not Found), so the unit's existence is fully CONCEALED.
    # Neither an anonymous scanner nor a logged-in low-privilege user can tell the route exists (the
    # GitHub/GitLab private-resource convention). There is NO /signin redirect from a private unit's
    # URL — login happens at `/` (root), not at a unit's own page, so redirecting would only leak
    # the endpoint. Default False = the ordinary gate (unauthenticated GET -> /signin, otherwise
    # 403). Set True for a control-center or sensitive app (e.g. admin, private messaging).
    private: bool = False
    # The optional route-recording hook. Historically imperative: ``routes(app) -> None`` mutates
    # the passed SDK App (``app.mount(...)`` / the ``@app.page``/``@app.action``/``@app.post``
    # decorators). The declarative-routes migration (design §2c, Option A) widens it so a unit's
    # ``routes`` may instead be a zero-arg ``routes() -> PageRoute | tuple[PageRoute, ...]`` that
    # RETURNS the domain's route bundle(s); core detects the form by arity and collects a returned
    # bundle onto the core App via ``collect_bundle``. Both call shapes coexist during the
    # migration (apps stay imperative until Stage 3), so the annotation admits either.
    routes: Callable[..., PageRoute | tuple[PageRoute, ...] | None] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Manifest.name is required")
        if not self.name.islower() or " " in self.name:
            raise ValueError(f"Manifest.name must be lowercase, no spaces: {self.name!r}")
        if not callable(self.register):
            raise TypeError("Manifest.register must be callable (the boot hook)")
        if self.routes is not None and not callable(self.routes):
            raise TypeError("Manifest.routes must be callable (register_routes(app)) or None")
        if self.name in self.dependency:
            raise ValueError(f"unit {self.name!r} cannot depend on itself")
        if len(set(self.dependency)) != len(self.dependency):
            raise ValueError(f"unit {self.name!r} has duplicate dependencies")

    @property
    def title(self) -> str:
        """Human-facing name: the explicit ``display_name`` if set, else a capitalized ``name``."""
        return self.display_name or self.name.capitalize()
