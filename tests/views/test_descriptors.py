"""Contract tests for the model-driven view descriptors (Stage 1)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import (
    Field,
    FieldType,
    ListView,
    PageView,
    StatusBadge,
    TableColumn,
    ViewModel,
    ViewRoute,
)


def test_viewmodel_read_surface_mirrors_tablemodel() -> None:
    vm = ViewModel(
        name="core_user",
        columns=(
            TableColumn(name="email", type=FieldType.TEXT, display=True),
            TableColumn(name="active", type=FieldType.BOOLEAN),
        ),
    )
    assert vm.name == "core_user"
    assert set(vm.column_map) == {"email", "active"}
    assert vm.display_label == "User"  # derived from core_user
    assert ViewModel(name="core_user", label="People").display_label == "People"
    import pytest

    with pytest.raises(ValueError, match="required"):
        ViewModel(name="")


def test_field_defaults_and_validation() -> None:
    f = Field(name="email")
    assert f.order == 100 and f.roles == () and f.span == 1
    with pytest.raises(ValueError, match="non-empty"):
        Field(name="")
    with pytest.raises(ValueError, match="span"):
        Field(name="x", span=0)


def test_listview_ordered_fields() -> None:
    v = ListView(fields=(Field("b", order=20), Field("a", order=10)))
    assert [f.name for f in v.ordered_fields] == ["a", "b"]


def test_listview_sort_validation() -> None:
    assert ListView(sort=("name", "asc")).sort == ("name", "asc")
    with pytest.raises(ValueError, match="sort"):
        ListView(sort=("name", "sideways"))  # type: ignore[arg-type]


def test_listview_filters_optional_restriction() -> None:
    # empty (default) = all filterable columns pickable at runtime
    assert ListView().filters == ()
    # provided = restrict the picker to these columns
    assert ListView(filters=("active", "status")).filters == ("active", "status")


def test_pageview_requires_model_and_view() -> None:
    lv = ListView(fields=(Field("email"),))
    pv = PageView(model=object(), view=lv)
    assert pv.view is lv
    with pytest.raises(ValueError, match="model"):
        PageView(model=None, view=lv)
    with pytest.raises(ValueError, match="view"):
        PageView(model=object(), view=None)


def test_viewroute_binds_path_view_permissions() -> None:
    pv = PageView(model=object(), view=ListView())
    r = ViewRoute(path="/users", view=pv, permission="admin.users.read")
    assert r.path == "/users" and r.permission == "admin.users.read" and r.view is pv
    assert ViewRoute(path="/x", view=pv).permission is None  # None = expansion supplies per-op keys
    with pytest.raises(ValueError, match="path"):
        ViewRoute(path="", view=pv)


def test_form_descriptors() -> None:
    from moderatorim.sdk import (
        FormAction,
        FormFields,
        FormOverview,
        FormTab,
        FormView,
    )

    ff = FormFields(fields=(Field("email"), Field("bio", span=2)), columns=2)
    assert ff.columns == 2
    with pytest.raises(ValueError, match="columns"):
        FormFields(columns=0)

    tab = FormTab(
        label="Detail",
        order=10,
        views=(FormFields(fields=(Field("email"),), order=20), FormOverview(order=10)),
    )
    # ordered_views sorts child views by their order (overview 10 before fields 20)
    assert [type(v).__name__ for v in tab.ordered_views] == ["FormOverview", "FormFields"]
    with pytest.raises(ValueError, match="label"):
        FormTab(label="")

    act = FormAction(label="Make super", handler=lambda ctx: None, roles=("admin.manager",))
    assert act.label == "Make super"
    with pytest.raises(ValueError, match="handler"):
        FormAction(label="x", handler=None)

    fv = FormView(
        tabs=(FormTab(label="B", order=20), FormTab(label="A", order=10)),
        actions=(act,),
    )
    assert [t.label for t in fv.ordered_tabs] == ["A", "B"]  # by order
    assert fv.ordered_actions[0] is act
    with pytest.raises(ValueError, match="at least one FormTab"):
        FormView(tabs=())


def test_modalview_and_modalaction() -> None:
    from moderatorim.sdk import FormTab, ListView, ModalAction, ModalView

    # ListView multiselect (set-editor) mode
    lv = ListView(fields=(), multiselect=True, select_key="permission")
    assert lv.multiselect is True and lv.select_key == "permission"

    # ModalAction requires label + handler
    import pytest

    with pytest.raises(ValueError, match="label"):
        ModalAction(label="", handler=lambda c: None)
    with pytest.raises(ValueError, match="handler"):
        ModalAction(label="Save", handler=None)

    # ModalView wraps a view + ordered modal actions; requires a view
    a2 = ModalAction(label="Save", handler=lambda c: None, order=20)
    a1 = ModalAction(label="Reset", handler=lambda c: None, order=10)
    mv = ModalView(view=lv, label="Edit permissions", actions=(a2, a1))
    assert mv.label == "Edit permissions" and mv.view is lv
    assert [a.label for a in mv.ordered_actions] == ["Reset", "Save"]
    with pytest.raises(ValueError, match="view"):
        ModalView(view=None)

    # a tab can carry an editor modal (opened by its permission-driven Edit)
    tab = FormTab(label="Permissions", editor=mv)
    assert tab.editor is mv
    assert mv.rows is None  # default: no resolver

    async def _rows(ctx, pid):
        return []

    assert ModalView(view=lv, rows=_rows).rows is _rows


def test_formtab_actions_and_formlist() -> None:
    from moderatorim.sdk import FormAction, FormList, FormTab, ListView

    # FormTab.actions default empty; ordered_actions sorts by order.
    assert FormTab(label="D").actions == ()
    a1 = FormAction(label="Add", handler=lambda ctx: None, order=20)
    a2 = FormAction(label="Edit", handler=lambda ctx: None, order=10)
    tab = FormTab(label="Permissions", actions=(a1, a2))
    assert [a.label for a in tab.ordered_actions] == ["Edit", "Add"]  # by order

    # all_actions on the view = form-level actions first, then each tab's (tab order) — the
    # unified /action/{idx} index space shared by route-binding and the renderer.
    from moderatorim.sdk import FormView

    fv = FormView(
        actions=(FormAction(label="Delete", handler=lambda ctx: None, order=5),),
        tabs=(FormTab(label="Perms", order=10, actions=(a2, a1)),),
    )
    assert [a.label for a in fv.all_actions] == ["Delete", "Edit", "Add"]

    # FormList carries a related model + a ListView, with an optional refresh id (D5).
    lv = ListView(fields=())
    fl = FormList(model="core_role_permission", view=lv, id="perm-list")
    assert fl.model == "core_role_permission" and fl.view is lv and fl.id == "perm-list"
    assert fl.link == ""  # default = auto-detect the single REF back to the parent
    assert FormList(model="core_role_permission", view=lv, link="role_id").link == "role_id"
    # region_id is the DEPRECATED alias of id — still accepted, mapped to id with a warning.
    with pytest.warns(DeprecationWarning):
        legacy = FormList(model="core_role_permission", view=lv, region_id="perm-list")
    assert legacy.id == "perm-list"
    with pytest.raises(ValueError, match="model"):
        FormList(model=None, view=lv)
    with pytest.raises(ValueError, match="view"):
        FormList(model="x", view=None)


def test_list_card() -> None:
    from moderatorim.sdk import FormTab, ListCard, ListCardAction, ListCardField

    field = ListCardField(label="Device", value="user_agent", format="browser")
    assert field.label == "Device" and field.value == "user_agent" and field.format == "browser"
    assert field.icon == ""  # icon defaults to empty (no leading glyph)
    assert not hasattr(field, "id")  # value-leaf — no D5 id

    # icon round-trips when set (Material Symbols glyph before the value)
    iconed = ListCardField(label="IP", value="ip", icon="lan")
    assert iconed.icon == "lan"

    action = ListCardAction(
        label="Revoke",
        hx_post="/settings/sessions/{id}/revoke",
        roles=("core.session.delete",),
        confirm="Revoke this session?",
        variant="danger",
    )
    assert action.hx_post == "/settings/sessions/{id}/revoke"
    assert (
        action.roles == ("core.session.delete",) and action.confirm and action.variant == "danger"
    )
    assert not hasattr(action, "id")  # value-leaf — no D5 id

    card = ListCard(
        model="core_session",
        fields=(field,),
        actions=(action,),
        link="user_id",
        filters=("state == active",),
        id="mim-sessions-self",
    )
    assert card.model == "core_session" and card.id == "mim-sessions-self"
    assert card.fields == (field,) and card.actions == (action,)
    assert card.link == "user_id" and card.onclick == ""  # non-navigable by default
    assert card.empty_label == "Nothing here yet."

    # ListCard is a valid FormTab child (the Sessions tab holds one).
    tab = FormTab(label="Sessions", order=20, views=(card,))
    assert tab.views == (card,)

    # distinct ids per mount so a swap can't cross-target (D5).
    admin_card = ListCard(model="core_session", fields=(field,), id="mim-sessions-admin")
    assert admin_card.id != card.id

    with pytest.raises(ValueError, match="label"):
        ListCardField(label="", value="x")
    with pytest.raises(ValueError, match="value"):
        ListCardField(label="x", value="")
    with pytest.raises(ValueError, match="label"):
        ListCardAction(label="", hx_post="/x")
    with pytest.raises(ValueError, match="hx_post"):
        ListCardAction(label="x", hx_post="")
    with pytest.raises(ValueError, match="model"):
        ListCard(model=None)


def test_formview_save_delegate() -> None:
    from moderatorim.sdk import FormSave, FormTab, FormView

    # Default: no save delegate -> generic ctx.store path (save is None).
    assert FormView(tabs=(FormTab(label="D"),)).save is None

    # A delegate implementing the FormSave protocol is carried on the view and is runtime-checkable.
    class RoleSave:
        async def create(self, ctx, model, data):  # type: ignore[no-untyped-def]
            return {}

        async def update(self, ctx, model, record_id, data):  # type: ignore[no-untyped-def]
            return {}

        async def delete(self, ctx, model, record_id):  # type: ignore[no-untyped-def]
            return None

    rs = RoleSave()
    fv = FormView(tabs=(FormTab(label="D"),), save=rs)
    assert fv.save is rs
    assert isinstance(rs, FormSave)  # structural (runtime_checkable Protocol)


def test_view_extension_and_app_extend_view() -> None:
    from moderatorim.sdk import App, FormAction, FormTab, ViewExtension

    ext = ViewExtension(
        target="/shop/orders",
        add_tabs=(FormTab(label="Shipping"),),
        add_actions=(FormAction(label="Refund", handler=lambda ctx: None),),
    )
    assert ext.target == "/shop/orders" and len(ext.add_tabs) == 1
    with pytest.raises(ValueError, match="target"):
        ViewExtension(target="")

    app = App()
    app.extend_view("/shop/orders", add_tabs=(FormTab(label="Shipping"),))
    assert len(app.extensions) == 1 and app.extensions[0].target == "/shop/orders"


def test_field_custom_cell_escape_hatch() -> None:
    from moderatorim.sdk import Field

    plain = Field("name")
    assert plain.is_custom is False and plain.custom is None

    badge = Field("status_badge", custom=lambda rec: f"<b>{rec.get('status', '')}</b>")
    assert badge.is_custom is True
    assert badge.custom({"status": "active"}) == "<b>active</b>"
    # a custom field still needs a non-empty name (its column key + header label)
    with pytest.raises(ValueError, match="non-empty"):
        Field("", custom=lambda rec: "x")
    from moderatorim.sdk import App, CalendarView, Kind

    cal = CalendarView(start_field="starts_at", title_field="subject", end_field="ends_at")
    assert cal.start_field == "starts_at" and cal.title_field == "subject"
    with pytest.raises(ValueError, match="start_field"):
        CalendarView(start_field="", title_field="t")
    with pytest.raises(ValueError, match="title_field"):
        CalendarView(start_field="s", title_field="")

    app = App()
    app.calendar_view("/events", model=object(), view=cal, permission="cal.events")
    r = app.routes[0]
    assert r.kind is Kind.CALENDAR and r.methods == ("GET",)
    assert r.permission == "cal.events.read" and r.resource_permission == "cal.events"


def test_list_view_enable_actions_default_and_off() -> None:
    from moderatorim.sdk import ListView

    assert ListView().enable_actions is True  # default shows Edit/Delete/New
    assert ListView(enable_actions=False).enable_actions is False  # read-only list opts out


def test_app_mount_expands_viewroutes_with_permissions() -> None:
    from moderatorim.sdk import (
        App,
        Field,
        FieldType,
        FormFields,
        FormTab,
        FormView,
        Kind,
        ListView,
        PageView,
        TableColumn,
        TableModel,
        ViewRoute,
    )

    Widget = TableModel(
        name="shop_widget",
        columns=(TableColumn(name="name", type=FieldType.TEXT, display=True),),
    )
    list_pv = PageView(model=Widget, view=ListView(fields=(Field("name"),)))
    form_pv = PageView(
        model=Widget,
        view=FormView(
            tabs=(FormTab(label="Detail", views=(FormFields(fields=(Field("name"),)),)),)
        ),
    )
    app = App()
    app.mount(
        (
            ViewRoute(path="/widgets", view=list_pv),
            ViewRoute(path="/widgets/new", view=form_pv),
            ViewRoute(path="/widgets/{id}", view=form_pv),
        ),
        permission="shop.widget",
    )
    by = {(r.path, r.methods[0]): r for r in app.routes}
    # List binding → Kind.LIST gated by the expansion's single .read key
    assert by[("/widgets", "GET")].kind is Kind.LIST
    assert by[("/widgets", "GET")].permission == "shop.widget.read"
    # Form bindings dedupe to one RESTful route-set (5 routes), each with its own single permission:
    # GET /new (.create form), GET /{id} (.read edit form), POST /widgets (.create), PATCH /{id}
    # (.update), DELETE /{id} (.delete) — no /delete path suffix.
    assert by[("/widgets/new", "GET")].kind is Kind.FORM
    assert by[("/widgets/new", "GET")].permission == "shop.widget.create"
    assert by[("/widgets", "POST")].permission == "shop.widget.create"  # create on collection
    assert by[("/widgets/{id}", "GET")].permission == "shop.widget.read"
    assert by[("/widgets/{id}", "PATCH")].permission == "shop.widget.update"
    assert by[("/widgets/{id}", "DELETE")].permission == "shop.widget.delete"
    # exactly one form set (deduped): 5 form routes for the base
    form_routes = [r for r in app.routes if r.kind is Kind.FORM]
    assert len(form_routes) == 5
    # no /delete path suffix anywhere
    assert not any(r.path.endswith("/delete") for r in app.routes)
    # permission prefix derived from the path for the row-action / table-ACL layer
    assert by[("/widgets", "GET")].resource_permission == "shop.widget"


def test_mount_actions_records_post_route() -> None:
    from moderatorim.sdk import App, Kind, Route, RouteMethod

    async def define_role(ctx):  # noqa: ANN001, ANN202
        return None

    # A standalone route-action is a Route(method=POST); mount(actions=) records it as Kind.ACTION.
    ra = Route(
        path="/admin/roles/define",
        handler=define_role,
        method=RouteMethod.POST,
        permission="admin.roles.create",
    )
    app = App()
    app.mount((), actions=(ra,))
    rd = next(r for r in app.routes if r.path == "/admin/roles/define")
    assert rd.kind is Kind.ACTION and rd.methods == ("POST",)
    assert rd.handler is define_role and rd.permission == "admin.roles.create"


def test_route_descriptor_get_and_post() -> None:
    from moderatorim.sdk import Route, RouteMethod

    async def home(ctx):  # noqa: ANN001, ANN202
        return None

    # RouteMethod is a StrEnum: compares/serializes as the plain HTTP verb.
    assert RouteMethod.GET == "GET" and RouteMethod.POST == "POST"
    assert RouteMethod.PATCH == "PATCH" and RouteMethod.DELETE == "DELETE"
    assert str(RouteMethod.POST) == "POST"

    # a GET page defaults method=GET and may carry title/nav + a single permission
    g = Route(path="/admin", handler=home, title="Admin", nav="Admin", permission="a.b.read")
    assert g.method is RouteMethod.GET and g.title == "Admin" and g.nav == "Admin"
    assert g.permission == "a.b.read"
    # a POST action
    p = Route(path="/admin/do", handler=home, method=RouteMethod.POST, permission="a.b.create")
    assert p.method is RouteMethod.POST and p.permission == "a.b.create"
    # None permission = public (e.g. /signin)
    assert Route(path="/signin", handler=home).permission is None

    with pytest.raises(ValueError, match="path"):
        Route(path="", handler=home)
    with pytest.raises(ValueError, match="handler"):
        Route(path="/x", handler=None)


def test_permission_object_renders_key_and_is_typed() -> None:
    import pytest

    from moderatorim.sdk import Permission, PermissionAction

    # PermissionAction is a StrEnum of the CRUD verbs, DISTINCT from the HTTP-method RouteMethod.
    assert PermissionAction.READ == "read" and PermissionAction.CREATE == "create"
    assert PermissionAction.UPDATE == "update" and PermissionAction.DELETE == "delete"
    assert [a.value for a in PermissionAction] == ["read", "create", "update", "delete"]

    # __str__ renders the full {source}.{resource}.{action} key core enforces.
    p = Permission(source="admin", resource="users", action=PermissionAction.CREATE)
    assert str(p) == "admin.users.create"
    assert f"gate={p}" == "gate=admin.users.create"

    # frozen + value-equal
    assert p == Permission(source="admin", resource="users", action=PermissionAction.CREATE)
    with pytest.raises(Exception):  # noqa: B017 - frozen dataclass rejects assignment
        p.resource = "roles"  # type: ignore[misc]

    # source + resource must be non-empty (the declaring unit's namespace segment)
    with pytest.raises(ValueError, match="source"):
        Permission(source="", resource="users", action=PermissionAction.READ)
    with pytest.raises(ValueError, match="resource"):
        Permission(source="admin", resource="", action=PermissionAction.READ)


def test_permission_catalog_generates_itself() -> None:
    from moderatorim.sdk import Permission, PermissionAction

    # The whole point: a unit's catalog is generated from resources × CRUD, not hand-typed strings.
    catalog = tuple(
        Permission(source="admin", resource=r, action=a)
        for r in ("users", "roles", "groups")
        for a in PermissionAction
    )
    keys = [str(p) for p in catalog]
    assert len(keys) == 12
    assert "admin.users.read" in keys and "admin.groups.delete" in keys
    # a platform unit shares the exact shape — source is kind-agnostic
    assert str(
        Permission(source="moderation", resource="reports", action=PermissionAction.UPDATE)
    ) == ("moderation.reports.update")


def test_route_accepts_permission_object_normalized_to_key() -> None:
    # A Route/ViewRoute may declare permission= as a Permission OBJECT or a bare string;
    # the expansion normalizes both to the same plain key on the RouteDef, so core enforces
    # identically (declarative-routes 3.2).
    from moderatorim.sdk import App, Permission, PermissionAction, Route, RouteMethod

    async def h(ctx):  # noqa: ANN001, ANN202
        return None

    app = App()
    # object form
    app.expand_route(
        Route(
            path="/users/new",
            handler=h,
            method=RouteMethod.POST,
            permission=Permission("admin", "users", PermissionAction.CREATE),
        )
    )
    # string form (same key)
    app.expand_route(
        Route(
            path="/roles/new", handler=h, method=RouteMethod.POST, permission="admin.roles.create"
        )
    )
    # None stays ungated
    app.expand_route(Route(path="/public", handler=h))
    by = {r.path: r for r in app.routes}
    assert by["/users/new"].permission == "admin.users.create"  # object → plain key
    assert isinstance(by["/users/new"].permission, str)  # normalized, not a Permission on RouteDef
    assert by["/roles/new"].permission == "admin.roles.create"  # string passes through
    assert by["/public"].permission is None  # ungated


def test_route_expands_get_page_and_post_action() -> None:
    from moderatorim.sdk import App, Kind, Route, RouteMethod

    async def page_h(ctx):  # noqa: ANN001, ANN202
        return None

    async def act_h(ctx):  # noqa: ANN001, ANN202
        return None

    app = App()
    app.expand_route(
        Route(path="/admin", handler=page_h, title="Admin", nav="Admin", permission="a.b.read")
    )
    app.expand_route(
        Route(path="/admin/do", handler=act_h, method=RouteMethod.POST, permission="a.b.create")
    )
    app.expand_route(
        Route(path="/admin/x", handler=act_h, method=RouteMethod.DELETE, permission="a.b.delete")
    )
    by = {(r.path, r.methods[0]): r for r in app.routes}
    # GET → Kind.PAGE, title/nav carried, single permission gate
    pg = by[("/admin", "GET")]
    assert pg.kind is Kind.PAGE and pg.title == "Admin" and pg.nav == "Admin"
    assert pg.permission == "a.b.read"
    # POST → Kind.ACTION, no title/nav, its own permission
    ac = by[("/admin/do", "POST")]
    assert ac.kind is Kind.ACTION and ac.title is None and ac.nav is None
    assert ac.permission == "a.b.create"
    # DELETE → Kind.ACTION too, method preserved
    dl = by[("/admin/x", "DELETE")]
    assert dl.kind is Kind.ACTION and dl.methods == ("DELETE",) and dl.permission == "a.b.delete"


def test_pageroute_bundle_and_collect() -> None:
    from moderatorim.sdk import (
        App,
        Field,
        FieldType,
        Kind,
        ListView,
        PageRoute,
        PageView,
        Route,
        RouteMethod,
        TableColumn,
        TableModel,
        ViewRoute,
    )
    from moderatorim.sdk.web import as_bundle_tuple

    async def define(ctx):  # noqa: ANN001, ANN202
        return None

    Widget = TableModel(
        name="shop_widget",
        columns=(TableColumn(name="name", type=FieldType.TEXT, display=True),),
    )
    list_pv = PageView(model=Widget, view=ListView(fields=(Field("name"),)))

    bundle = PageRoute(
        views=(ViewRoute(path="/widgets", view=list_pv),),
        routes=(
            Route(
                path="/widgets/define",
                handler=define,
                method=RouteMethod.POST,
                permission="shop.widget.create",
            ),
        ),
        permission="shop.widget",
    )
    # a bundle is pure data
    assert bundle.permission == "shop.widget" and len(bundle.views) == 1 and len(bundle.routes) == 1

    # as_bundle_tuple normalizes register() returns
    assert as_bundle_tuple(bundle) == (bundle,)
    assert as_bundle_tuple((bundle,)) == (bundle,)
    assert as_bundle_tuple(None) == ()  # a still-imperative register(app) → nothing collected

    # core collects the bundle: the ViewRoute expands to a List, the Route to a POST action
    app = App()
    app.collect_bundle(bundle)
    by = {(r.path, r.methods[0]): r for r in app.routes}
    assert by[("/widgets", "GET")].kind is Kind.LIST
    assert by[("/widgets", "GET")].permission == "shop.widget.read"
    assert by[("/widgets/define", "POST")].kind is Kind.ACTION
    assert by[("/widgets/define", "POST")].permission == "shop.widget.create"


def test_collect_bundle_dedups_form_declared_by_sibling_viewroutes() -> None:
    # A generated Form is declared by TWO sibling ViewRoutes — /new and /{id} — pointing at the same
    # FormView. collect_bundle must expand the form set ONCE (dedup by base path), exactly as a
    # single app.mount(all_views) call did. Regression: expanding each view in its own mount() pass
    # gave each a fresh seen_form_base and registered the whole form set twice (found dogfooding the
    # admin app in declarative-routes Stage 3).
    from moderatorim.sdk import (
        App,
        Field,
        FieldType,
        FormFields,
        FormView,
        ListView,
        PageRoute,
        PageView,
        TableColumn,
        TableModel,
        ViewRoute,
    )

    Widget = TableModel(
        name="shop_widget",
        columns=(TableColumn(name="name", type=FieldType.TEXT, display=True),),
    )
    list_pv = PageView(model=Widget, view=ListView(fields=(Field("name"),)))
    form_pv = PageView(model=Widget, view=FormView(tabs=(FormFields(fields=(Field("name"),)),)))
    bundle = PageRoute(
        views=(
            ViewRoute(path="/widgets", view=list_pv),
            ViewRoute(path="/widgets/new", view=form_pv),
            ViewRoute(path="/widgets/{id}", view=form_pv),
        ),
        permission="shop.widget",
    )

    app = App()
    app.collect_bundle(bundle)
    from collections import Counter

    counts = Counter((r.path, r.methods) for r in app.routes)
    dups = {k: v for k, v in counts.items() if v > 1}
    assert not dups, f"form set expanded more than once: {dups}"
    # per-verb single-permission gate intact after dedup, RESTful verbs, no /delete suffix:
    # POST /widgets → .create, PATCH /{id} → .update, DELETE /{id} → .delete
    by = {(r.path, r.methods[0]): r for r in app.routes}
    assert by[("/widgets", "POST")].permission == "shop.widget.create"
    assert by[("/widgets/{id}", "PATCH")].permission == "shop.widget.update"
    assert by[("/widgets/{id}", "DELETE")].permission == "shop.widget.delete"
    assert not any(r.path.endswith("/delete") for r in app.routes)


def test_custom_get_page_is_a_route_via_mount_pages() -> None:
    # The OLD single-page PageRoute/LegacyPageRoute shape is GONE (declarative-routes 3.4); a custom
    # GET page is a Route, recorded by mount(pages=) as a Kind.PAGE route.
    from moderatorim.sdk import App, Kind, Route

    async def home(ctx):  # noqa: ANN001, ANN202
        return None

    pr = Route(path="/admin", handler=home, title="Admin", permission="admin.users.read")
    app = App()
    app.mount((), pages=(pr,))
    rd = next(r for r in app.routes if r.path == "/admin")
    assert rd.kind is Kind.PAGE and rd.methods == ("GET",)
    assert rd.handler is home and rd.title == "Admin" and rd.permission == "admin.users.read"


# --- StatusBadge (admin-users-form R4) -------------------------------------


def test_status_badge_resolve_maps_value_and_falls_back() -> None:
    b = StatusBadge(
        label="Verification",
        field="email_verified",
        mapping={"True": ("Verified", "success"), "False": ("Unverified", "neutral")},
    )
    assert b.resolve({"email_verified": True}) == ("Verified", "success")
    assert b.resolve({"email_verified": False}) == ("Unverified", "neutral")
    # missing record / missing field / unmapped value → default
    assert b.resolve(None) == ("—", "neutral")
    assert b.resolve({}) == ("—", "neutral")


def test_status_badge_rejects_unknown_variant() -> None:
    with pytest.raises(ValueError, match="variant"):
        StatusBadge(label="X", field="f", mapping={"1": ("On", "purple")})


def test_status_badge_requires_label_and_field() -> None:
    with pytest.raises(ValueError):
        StatusBadge(label="", field="f", mapping={})
    with pytest.raises(ValueError):
        StatusBadge(label="X", field="", mapping={})
