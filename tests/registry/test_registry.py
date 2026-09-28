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


def test_manifest_system_users_default_empty_and_carries_declaration() -> None:
    # default: no system users
    m = Manifest(name="widget", type=UnitType.APP, register=lambda c: None)
    assert m.system_users == {}
    # carries a declared {name: (groups,)} mapping verbatim (SDK only records; core validates/seeds)
    declared = {"cron.user": ("cron-runners",), "cron.worker": ("cron-runners", "cron-heavy")}
    m2 = Manifest(
        name="cron",
        type=UnitType.APP,
        register=lambda c: None,
        system_users=declared,
    )
    assert m2.system_users == declared


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
