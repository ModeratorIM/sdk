"""Routing primitives an app returns/receives — ``Page``/``redirect``/``Fragment``/``Rendered`` and
the per-request ``Ctx`` handle. App authors never name Starlette; the core adapter renders these."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from moderatorim.sdk.datastore import DataStore

Content = list[Any]


@dataclass
class Page:
    """A full page a ``@app.page`` handler returns. Normal GET → wrapped in the shell (full doc);
    ``HX-Request`` → body fragment + central ``HX-Push-Url``."""

    title: str
    content: Content
    permission: str | None = None


@dataclass
class Redirect:
    """A mutate-then-navigate result. ``HX-Redirect`` for htmx, ``303`` for plain. ``replace=True``
    also sets ``X-Mim-Replace`` (history replace — crossing the auth boundary)."""

    url: str
    replace: bool = False


def redirect(url: str, *, replace: bool = False) -> Redirect:
    """Return a navigation result (``HX-Redirect`` for htmx, ``303`` for plain)."""
    return Redirect(url, replace=replace)


@dataclass
class Fragment:
    """A swap-in-place result a ``@app.post`` handler returns (no navigation)."""

    html: Any


@dataclass
class Rendered:
    """Swap-in-place content with an explicit HTTP status (e.g. a 404 body). Bare Fragment = 200."""

    html: Any
    status: int = 200


@dataclass
class Ctx:
    """Per-request context the framework populates and hands to a handler.

    - ``config`` / ``user`` / ``store`` / ``request`` — runtime handles core injects.
    - ``can``   — a ``can(permission)->bool`` read gate for the current user.
    - ``has_role`` — a ``has_role(name)->bool`` gate for the current user (declared-role names);
                  a super_user holds every role. Used to gate role-gated views/fields.
    - ``authz`` — the RBAC management handle (for apps that MANAGE permissions, e.g. admin), so apps
                  never import AuthzService.
    - session/cookie mutations are recorded and applied by the adapter.
    """

    config: Any
    request: Any
    user: Any | None = None
    store: DataStore | None = None
    can: Callable[[str], bool] = field(default=lambda _p: False)
    has_role: Callable[[str], bool] = field(default=lambda _r: False)
    authz: Any | None = None
    _set_session: str | None = field(default=None, repr=False)
    _clear_session: bool = field(default=False, repr=False)
    _extra_cookies: list[tuple[str, str, str, int | None]] = field(default_factory=list, repr=False)

    def set_session(self, token: str) -> None:
        """Set the session cookie on the outgoing response."""
        self._set_session = token
        self._clear_session = False

    def clear_session(self) -> None:
        """Clear the session cookie on the outgoing response (logout)."""
        self._clear_session = True
        self._set_session = None

    def set_cookie(
        self, name: str, value: str, *, path: str = "/", max_age: int | None = None
    ) -> None:
        """Record a non-session cookie to set on the outgoing response (httponly, samesite=lax,
        secure from the request scheme). Used e.g. for the setup installation-lock cookie."""
        self._extra_cookies.append((name, value, path, max_age))

    async def form(self) -> dict[str, str]:
        """Parse the urlencoded request body into a flat {field: value} dict (last value wins)."""
        from urllib.parse import parse_qs

        raw = (await self.request.body()).decode()
        return {k: v[0] for k, v in parse_qs(raw).items()}

    async def form_multi(self) -> dict[str, list[str]]:
        """Parse the urlencoded body into {field: [all values]} — the multi-value form read.
        Use this when a field repeats (a checkbox group / multi-select set-editor); ``form()``
        keeps only the last value and would collapse the set."""
        from urllib.parse import parse_qs

        raw = (await self.request.body()).decode()
        return {k: list(v) for k, v in parse_qs(raw).items()}

    def query(self, key: str, default: str = "") -> str:
        """Read a query-string parameter."""
        value: str = self.request.query_params.get(key, default)
        return value
