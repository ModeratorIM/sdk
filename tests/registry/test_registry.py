"""Contract tests for the registry domain (Manifest, UnitType, NavEntry)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import Manifest, NavEntry, UnitType


def test_manifest_basics_and_routes_hook() -> None:
    m = Manifest(
        name="widget",
        type=UnitType.APP,
        register=lambda core: None,
        nav=(NavEntry("Widget", "/widget", "star"),),
        routes=lambda app: None,
    )
    assert m.title == "Widget" and m.routes is not None
    with pytest.raises(TypeError, match="routes must be callable"):
        Manifest(name="bad", type=UnitType.APP, register=lambda c: None, routes=1)  # type: ignore[arg-type]


def test_manifest_name_validation() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        Manifest(name="Widget", type=UnitType.APP, register=lambda c: None)


def test_nav_entry_icon_is_asset() -> None:
    assert NavEntry("A", "/a", "star").icon_is_asset is False
    assert NavEntry("A", "/a", "/static/a.svg").icon_is_asset is True


def test_nav_entry_permission_accepts_permission_object() -> None:
    # NavEntry.permission accepts a Permission object or a bare key; core normalizes with str().
    from moderatorim.sdk import Permission, PermissionAction

    e = NavEntry(
        "Users", "/admin/users", permission=Permission("admin", "users", PermissionAction.READ)
    )
    assert str(e.permission) == "admin.users.read"
    # a bare string still works
    assert NavEntry("Roles", "/admin/roles", permission="admin.roles.read").permission == (
        "admin.roles.read"
    )


def test_manifest_service_roles_default_empty_and_carries_declaration() -> None:
    # default: no service roles
    m = Manifest(name="widget", type=UnitType.APP, register=lambda c: None)
    assert m.service_roles == ()
    # carries the declared tuple verbatim (SDK records; core validates + seeds it)
    m2 = Manifest(
        name="moderation",
        type=UnitType.APP,
        register=lambda c: None,
        service_roles=("moderation.reviewer",),
    )
    assert m2.service_roles == ("moderation.reviewer",)


def test_manifest_api_version_default_empty_and_distinct_from_version() -> None:
    # default: no provider API version (apps / unversioned providers)
    m = Manifest(name="widget", type=UnitType.APP, register=lambda c: None)
    assert m.api_version == ""
    # carries the declared provider API version, independent of the package `version`
    m2 = Manifest(
        name="telegram",
        type=UnitType.PLATFORM,
        register=lambda c: None,
        version="0.1.0",
        api_version="7.0",
    )
    assert m2.api_version == "7.0"
    assert m2.version == "0.1.0"


def test_platform_capabilities_default_and_declared() -> None:
    from moderatorim.sdk import PlatformCapabilities

    # non-platform / undeclared: platform is None (zero impact on existing manifests)
    plain = Manifest(name="widget", type=UnitType.APP, register=lambda c: None)
    assert plain.platform is None

    # a platform adapter declares its capability catalog as DATA on the manifest
    caps = PlatformCapabilities(
        auth_type="token",
        ingest_mode="webhook",
        description="Telegram Bot API adapter",
        events=(("message", "Message"),),
        signals=(("text", "Text", "text"),),
        actions=(("delete", "Delete"),),
        credentials=("token", ("webhook_secret", True)),
    )
    tg = Manifest(
        name="telegram",
        type=UnitType.PLATFORM,
        register=lambda c: None,
        display_name="Telegram",
        api_version="7.0",
        platform=caps,
    )
    assert tg.platform is caps
    assert tg.platform.auth_type == "token" and tg.platform.events[0] == ("message", "Message")
    # frozen value object (immutable declaration)
    with pytest.raises(AttributeError):
        caps.auth_type = "basic_auth"  # type: ignore[misc]


def test_form_html_child_is_a_plain_container() -> None:
    from moderatorim.sdk import FormHtml, FormTab

    h = FormHtml(order=0, id="auth")
    tab = FormTab(label="Authentication", order=0, views=(h,))
    assert tab.ordered_views[0] is h
    assert h.id == "auth" and h.order == 0
