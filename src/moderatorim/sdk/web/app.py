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


class App:
    """A collection of self-registering routes. Core owns one; each mounted app owns its own, and
    core's adapter collects each App's :attr:`routes` into the live application.

    PURE registration — holds route declarations, nothing runtime. Dispatch (build Ctx, enforce
    permission, render, wire cookies) is core's ``adapter.build_routes(app, …)``.
    """

    def __init__(self) -> None:
        self._routes: list[RouteDef] = []

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
    ) -> None:
        """Register a GENERATED model-driven List page at ``path``.

        Unlike :meth:`page`, this takes no handler — core expands the ``model`` + ``view``
        (a :class:`~moderatorim.sdk.ListView`) into the query→store→render flow, gated by
        ``{permission}.read`` (row actions gate on ``.create``/``.update``/``.delete``). The app
        declares intent; core owns the rendering (host-owns-the-shell seam)."""
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
                resource_permission=permission,
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
