"""The ``App`` routing facade — pure registration. Core's adapter consumes ``App.routes``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class Kind(Enum):
    PAGE = auto()
    ACTION = auto()
    POST = auto()
    LIST = (
        auto()
    )  # a generated model-driven List page (core expands it into a query→render handler)
    FORM = auto()  # a generated model-driven Form route (core expands it into a handler)
    CALENDAR = auto()  # a generated model-driven Calendar month page (core expands it)


@dataclass
class RouteDef:
    """A recorded route declaration. Core's adapter turns each into a real HTTP route."""

    path: str
    methods: tuple[str, ...]
    handler: Callable[..., Any]
    kind: Kind
    title: str | None = None
    permission: str | None = None
    nav: str | None = None
    # For kind=LIST (generated model-driven pages): the model + view descriptor core renders. The
    # handler is None for LIST — core supplies the query→render handler at build time.
    model: Any = None
    view: Any = None
    # For kind=LIST: the bare resource permission prefix (e.g. "admin.users"); the route gate is
    # "{prefix}.read" (in `permission`), row actions gate on "{prefix}.create/.update/.delete".
    resource_permission: str | None = None
    # For kind=FORM: which form op this route serves — "new" (GET create form), "edit" (GET edit
    # form), "create" (POST), "update" (POST), "delete" (POST). Core supplies the matching handler.
    form_op: str | None = None
    # For kind=LIST: optional async (ctx, rows) -> None hook run AFTER the query, BEFORE render, to
    # attach computed fields (e.g. a role's grants from a link table) that a Field.custom cell then
    # renders. Mutates rows in place; core awaits it. Row-level escape hatch for cross-table data.
    enrich: Any = None
    # ALL-OF permission gate (declarative-routes, design §1): the FULL permission keys this route
    # REQUIRES; the caller's resolved permission set must contain EVERY one (empty = ungated). This
    # is the unified gate — it supersedes the legacy single `permission` (still populated by the
    # imperative decorators / the model-driven view expansion for the interim shim) and the removed
    # per-binding `roles` gate. Core's `_enforce` reads `permissions`, falling back to `permission`.
    permissions: tuple[str, ...] = ()
    # Per-binding ROLE gate — LEGACY (design §1b layer 2). Retained only so any not-yet-migrated
    # imperative caller that stamped roles= keeps constructing; core no longer gates on it. Removed
    # once apps migrate (Stage 3/4).
    roles: tuple[str, ...] = ()


class App:
    """A collection of self-registering routes. Core owns one; each mounted app owns its own, and
    core's adapter collects each App's :attr:`routes` into the live application.

    PURE registration — holds route declarations, nothing runtime. Dispatch (build Ctx, enforce
    permission, render, wire cookies) is core's ``adapter.build_routes(app, …)``.
    """

    def __init__(self) -> None:
        self._routes: list[RouteDef] = []
        self._extensions: list[Any] = []  # ViewExtension declarations (cross-app form injection)

    def page(
        self,
        path: str,
        *,
        title: str | None = None,
        permission: str | None = None,
        nav: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(
                RouteDef(path, ("GET",), fn, Kind.PAGE, title=title, permission=permission, nav=nav)
            )
            return fn

        return deco

    def list_view(
        self,
        path: str,
        *,
        model: Any,
        view: Any,
        permission: str,
        title: str | None = None,
        nav: str | None = None,
        enrich: Any = None,
    ) -> None:
        """Register a GENERATED model-driven List page at ``path``.

        Unlike :meth:`page`, this takes no handler — core expands the ``model`` + ``view``
        (a :class:`~moderatorim.sdk.ListView`) into the query→store→render flow, gated by
        ``{permission}.read`` (row actions gate on ``.create``/``.update``/``.delete``). The app
        declares intent; core owns the rendering (host-owns-the-shell seam).

        ``enrich`` is an optional ``async (ctx, rows) -> None`` hook run after the query and before
        render: attach computed fields to each row (e.g. a role's grants pulled from a link table)
        that a :class:`~moderatorim.sdk.Field` with ``custom=`` then renders. The escape hatch for
        per-row data the generic query cannot join."""
        self._routes.append(
            RouteDef(
                path,
                ("GET",),
                handler=_unset_list_handler,
                kind=Kind.LIST,
                title=title,
                permission=f"{permission}.read",
                nav=nav,
                model=model,
                view=view,
                enrich=enrich,
                resource_permission=permission,
                permissions=(f"{permission}.read",),
            )
        )

    def form_view(
        self,
        base_path: str,
        *,
        model: Any,
        view: Any,
        permission: str,
        title: str | None = None,
    ) -> None:
        """Register a GENERATED model-driven Form (new + edit + create/update/delete).

        Expands into the route set (design §1): GET ``{base}/new`` (create form), GET
        ``{base}/{id}`` (edit form), POST ``{base}/new`` (create), POST ``{base}/{id}`` (update),
        POST ``{base}/{id}/delete``. Each is gated by the matching CRUD permission
        (``{permission}.create/.read/.update/.delete``). No handler — core supplies each per
        ``form_op`` (host-owns-rendering seam)."""

        def _fd(path: str, methods: tuple[str, ...], op: str, perm: str) -> RouteDef:
            return RouteDef(
                path,
                methods,
                handler=_unset_form_handler,
                kind=Kind.FORM,
                title=title,
                permission=perm,
                model=model,
                view=view,
                resource_permission=permission,
                form_op=op,
                permissions=(perm,),
            )

        self._routes.extend(
            [
                _fd(f"{base_path}/new", ("GET",), "new", f"{permission}.create"),
                _fd(f"{base_path}/{{id}}", ("GET",), "edit", f"{permission}.read"),
                _fd(f"{base_path}/new", ("POST",), "create", f"{permission}.create"),
                _fd(f"{base_path}/{{id}}", ("POST",), "update", f"{permission}.update"),
                _fd(f"{base_path}/{{id}}/delete", ("POST",), "delete", f"{permission}.delete"),
            ]
        )
        # One ACTION route per declared FormAction, at {base}/{id}/action/{idx}, routed to the
        # action's OWN handler. The action's roles= gate the BUTTON at render (L3); the route is
        # permission-gated at the resource's .update floor (a form action mutates the record).
        for idx, act in enumerate(getattr(view, "ordered_actions", ())):
            self._routes.append(
                RouteDef(
                    f"{base_path}/{{id}}/action/{idx}",
                    ("POST",),
                    handler=act.handler,
                    kind=Kind.ACTION,
                    permission=f"{permission}.update",
                    permissions=(f"{permission}.update",),
                )
            )

    def extend_view(
        self,
        target: str,
        *,
        add_tabs: tuple[Any, ...] = (),
        add_actions: tuple[Any, ...] = (),
    ) -> None:
        """Inject tabs/actions into ANOTHER resource's Form (design §5b), keyed by the target form's
        base path (e.g. ``"/shop/orders"``). Core collects these across apps and merges them into
        the target FormView at render, gated by the injected tabs'/actions' own ``roles``. The
        injecting app must ALSO register a ``form_view`` action route for any injected FormAction —
        use ``form_view`` for a whole owned resource; ``extend_view`` only augments another's form.
        """
        from moderatorim.sdk.views import ViewExtension

        self._extensions.append(
            ViewExtension(target=target, add_tabs=add_tabs, add_actions=add_actions)
        )

    @property
    def extensions(self) -> list[Any]:
        """The recorded cross-app view extensions (core reads these at boot)."""
        return list(self._extensions)

    def calendar_view(self, path: str, *, model: Any, view: Any, permission: str) -> None:
        """Record a generated Calendar month page (design §6, ``Kind.CALENDAR``) at ``path``, gated
        at ``{permission}.read``. Core supplies the query→render handler at build time (fetches the
        month's records by date range and renders the grid). Pair with ``form_view`` on the same
        resource so event/day clicks open the edit/new forms."""
        self._routes.append(
            RouteDef(
                path,
                ("GET",),
                handler=self._unset_calendar_handler,
                kind=Kind.CALENDAR,
                model=model,
                view=view,
                permission=f"{permission}.read",
                resource_permission=permission,
                permissions=(f"{permission}.read",),
            )
        )

    @staticmethod
    async def _unset_calendar_handler(ctx: Any) -> Any:  # pragma: no cover - replaced at build
        raise RuntimeError("Kind.CALENDAR handler is supplied by core at build time")

    def expand_route(self, r: Any, *, default_permission: str | None = None) -> None:
        """Collect ONE declarative :class:`~moderatorim.sdk.Route` (declarative-routes design §2).

        The declarative twin of the ``@app.page`` / ``@app.action`` / ``@app.post`` decorators:
        ``r.method`` selects the binding — ``RouteMethod.GET`` → a ``Kind.PAGE`` route (``title`` /
        ``nav`` apply, GET only), ``RouteMethod.POST`` → a ``Kind.ACTION`` route. The gate is
        ``r.permissions`` (ALL-OF, full keys); ``default_permission`` is the bundle's resource
        prefix, carried for documentation/grouping only (it is NOT a gate — a route without
        ``permissions`` is public).
        """
        method = str(getattr(r, "method", "GET"))
        perms = tuple(getattr(r, "permissions", ()) or ())
        if method == "POST":
            self._routes.append(
                RouteDef(
                    r.path,
                    ("POST",),
                    handler=r.handler,
                    kind=Kind.ACTION,
                    permissions=perms,
                )
            )
        else:
            self._routes.append(
                RouteDef(
                    r.path,
                    ("GET",),
                    handler=r.handler,
                    kind=Kind.PAGE,
                    title=getattr(r, "title", None),
                    nav=getattr(r, "nav", None),
                    permissions=perms,
                )
            )

    def expand_view_route(
        self, vr: Any, *, permission: str | None = None, enrich: Any = None
    ) -> None:
        """Collect ONE declarative :class:`~moderatorim.sdk.ViewRoute` (declarative-routes §2).

        The declarative twin of :meth:`mount` for a single generated binding: core resolves the
        KIND from the PageView's ``view`` type (ListView → List, FormView → Form set, CalendarView →
        Calendar) and the path shape, gated by ``vr.permissions`` (ALL-OF). ``permission`` is the
        bundle's resource prefix used for the row-action / table-ACL layer (defaults from the path);
        ``enrich`` is applied to a List binding (per-row computed cells)."""
        self.mount(
            (vr,),
            permission=permission or self._path_to_permission(vr.path),
            enrich=enrich,
        )

    def collect_bundle(self, bundle: Any) -> None:
        """Collect one :class:`~moderatorim.sdk.PageRoute` BUNDLE (declarative-routes §2): expand
        each ``views`` entry via :meth:`expand_view_route` and each ``routes`` entry via
        :meth:`expand_route`, threading the bundle's ``permission`` prefix + ``enrich`` hook."""
        for vr in getattr(bundle, "views", ()):
            self.expand_view_route(vr, permission=bundle.permission, enrich=bundle.enrich)
        for r in getattr(bundle, "routes", ()):
            self.expand_route(r, default_permission=bundle.permission)

    def mount(
        self,
        routes: tuple[Any, ...],
        *,
        actions: tuple[Any, ...] = (),
        pages: tuple[Any, ...] = (),
        permission: str | None = None,
        enrich: Any = None,
    ) -> None:
        """Register a declarative ``routes.py`` table of :class:`ViewRoute` bindings (design §1).

        Each ``ViewRoute(path, view=PageView, roles=…)`` is expanded into the same generated routes
        as the imperative facades — core resolves the KIND from the PageView's ``view`` type and the
        path shape: a :class:`ListView` PageView at ``/x`` → a List; a :class:`FormView` PageView at
        ``/x/new`` + ``/x/{id}`` → one Form (deduped by base path); a :class:`CalendarView`
        PageView → a Calendar. The binding's ``roles=`` is the route ACCESS GATE (§1b layer 2):
        core enforces ``ctx.has_role(any)`` at the route, independent of the table-ACL data floor.

        ``permission`` is the resource permission PREFIX used only for the table-ACL / row-action
        layer (``.create/.update/.delete`` visibility); it defaults to the path turned into a prefix
        (``/admin/users`` → ``admin.users``). The route GATE is ``roles=``, not this prefix — the
        design's separation of route access (roles) from the data floor (table ACL).

        ``enrich`` is an optional ``async (ctx, rows) -> None`` hook applied to every LIST binding
        mounted here (see :meth:`list_view`), for per-row computed cells that join other tables.

        ``actions`` is a tuple of :class:`RouteAction` — standalone route-actions (the declarative
        form of ``@app.action``), each expanded into a ``Kind.ACTION`` route gated by its
        ``permissions`` (ALL-OF, full keys). Keep these in the app's ``actions.py``.

        ``pages`` is a tuple of :class:`Route` (GET) or the legacy :class:`LegacyPageRoute` — custom
        pages (the declarative form of ``@app.page``), each expanded into a ``Kind.PAGE`` route
        served by its ``handler``. A :class:`Route` gates on its ``permissions`` (ALL-OF); the
        legacy shape gates on its ``roles`` / ``permission``. This lets ``routes.py`` be uniformly
        tuples of declaration objects with no decorators — the escape-hatch page for a screen the
        view generator cannot express.
        """
        from moderatorim.sdk.views import CalendarView, FormView, ListView

        seen_form_base: set[str] = set()
        for r in routes:
            pv = r.view  # a PageView
            inner = pv.view
            perm = permission or self._path_to_permission(r.path)
            route_perms = tuple(getattr(r, "permissions", ()))
            if isinstance(inner, ListView):
                start = len(self._routes)
                self.list_view(r.path, model=pv.model, view=inner, permission=perm, enrich=enrich)
                self._stamp_permissions(start, route_perms)
            elif isinstance(inner, FormView):
                base = self._form_base_path(r.path)
                if base in seen_form_base:
                    continue  # the sibling binding (/new vs /{id}) already expanded the form set
                seen_form_base.add(base)
                start = len(self._routes)
                self.form_view(base, model=pv.model, view=inner, permission=perm)
                self._stamp_permissions(start, route_perms)
            elif isinstance(inner, CalendarView):
                start = len(self._routes)
                self.calendar_view(r.path, model=pv.model, view=inner, permission=perm)
                self._stamp_permissions(start, route_perms)
            else:  # pragma: no cover - guarded by PageView, but fail loud on a new view type
                raise TypeError(f"ViewRoute at {r.path!r} has an unsupported view {type(inner)!r}")

        # Standalone route-actions (design §1): each RouteAction -> a Kind.ACTION RouteDef, gated by
        # its permissions= (ALL-OF, full keys). The declarative form of @app.action.
        for a in actions:
            self._routes.append(
                RouteDef(
                    a.path,
                    a.methods,
                    handler=a.handler,
                    kind=Kind.ACTION,
                    permissions=tuple(getattr(a, "permissions", ())),
                )
            )

        # Custom pages (design §7.4): each Route/LegacyPageRoute -> a Kind.PAGE RouteDef served by
        # its handler. A Route gates on permissions= (ALL-OF); the legacy shape on roles=/permission
        for p in pages:
            self._routes.append(
                RouteDef(
                    p.path,
                    ("GET",),
                    handler=p.handler,
                    kind=Kind.PAGE,
                    title=p.title,
                    permission=getattr(p, "permission", None),
                    nav=p.nav,
                    permissions=tuple(getattr(p, "permissions", ())),
                    roles=tuple(getattr(p, "roles", ())),
                )
            )

    def _stamp_permissions(self, start_index: int, permissions: tuple[str, ...]) -> None:
        """Set the ALL-OF ``permissions`` gate on every RouteDef appended since ``start_index`` (the
        just-mounted view binding), from the ViewRoute's declared ``permissions``. When empty, the
        expansion's own per-op keys (list ``.read`` etc.) remain as the fallback gate."""
        if not permissions:
            return
        for rd in self._routes[start_index:]:
            rd.permissions = tuple(permissions)

    @staticmethod
    def _form_base_path(path: str) -> str:
        for suffix in ("/{id}/delete", "/{id}", "/new"):
            if path.endswith(suffix):
                return path[: -len(suffix)]
        return path

    @staticmethod
    def _path_to_permission(path: str) -> str:
        # "/admin/users" -> "admin.users"; the form base is used for /x/new and /x/{id}.
        base = App._form_base_path(path).strip("/")
        return base.replace("/", ".") if base else "app"

    def action(
        self, path: str, *, methods: tuple[str, ...] = ("POST",), permission: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(RouteDef(path, methods, fn, Kind.ACTION, permission=permission))
            return fn

        return deco

    def post(
        self, path: str, *, permission: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(RouteDef(path, ("POST",), fn, Kind.POST, permission=permission))
            return fn

        return deco

    @property
    def routes(self) -> list[RouteDef]:
        """All recorded route declarations (core's adapter consumes these)."""
        return list(self._routes)

    @property
    def nav_routes(self) -> list[RouteDef]:
        """Routes that declared ``nav=`` — shown only when their permission check passes."""
        return [rd for rd in self._routes if rd.nav is not None]


def as_bundle_tuple(bundles: Any) -> tuple[Any, ...]:
    """Normalize a domain/app ``register()`` return into a tuple of :class:`PageRoute` bundles
    (declarative-routes §2): accept a single ``PageRoute`` bundle, a tuple/list of them, or ``None``
    (a still-imperative ``register(app)`` that mutated the app and returned nothing → ``()``)."""
    if bundles is None:
        return ()
    if isinstance(bundles, list | tuple):
        return tuple(bundles)
    return (bundles,)


def _unset_list_handler(ctx: Any) -> Any:  # pragma: no cover - core replaces this at build time
    raise RuntimeError(
        "a Kind.LIST route's handler is generated by core at build time; it must not be called "
        "directly (App.list_view records intent, core.web.adapter supplies the handler)"
    )


def _unset_form_handler(ctx: Any) -> Any:  # pragma: no cover - core replaces this at build time
    raise RuntimeError(
        "a Kind.FORM route's handler is generated by core at build time; it must not be called "
        "directly (App.form_view records intent, core.web.adapter supplies the handler)"
    )
