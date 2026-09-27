"""Contract tests for the model-driven view descriptors (Stage 1)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import Field, FieldType, ListView, PageView, TableColumn, ViewModel, ViewRoute


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


def test_viewroute_binds_path_view_roles() -> None:
    pv = PageView(model=object(), view=ListView())
    r = ViewRoute(path="/users", view=pv, roles=("admin.users.read",))
    assert r.path == "/users" and r.roles == ("admin.users.read",) and r.view is pv
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


def test_list_view_row_actions_default_and_off() -> None:
    from moderatorim.sdk import ListView

    assert ListView().row_actions is True  # default shows Edit/Delete/New
    assert ListView(row_actions=False).row_actions is False  # read-only list opts out


def test_app_mount_expands_viewroutes_with_roles() -> None:
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
            ViewRoute(path="/widgets", view=list_pv, roles=("shop.viewer",)),
            ViewRoute(path="/widgets/new", view=form_pv, roles=("shop.manager",)),
            ViewRoute(path="/widgets/{id}", view=form_pv, roles=("shop.viewer",)),
        )
    )
    by = {(r.path, r.methods[0]): r for r in app.routes}
    # List binding → Kind.LIST gated by its roles
    assert by[("/widgets", "GET")].kind is Kind.LIST
    assert by[("/widgets", "GET")].roles == ("shop.viewer",)
    # Form bindings dedupe to one form route-set (5 routes), all carrying the mount roles
    assert by[("/widgets/new", "GET")].kind is Kind.FORM
    assert by[("/widgets/new", "GET")].roles == ("shop.manager",)
    # exactly one form set (deduped): 5 form routes for the base
    form_routes = [r for r in app.routes if r.kind is Kind.FORM]
    assert len(form_routes) == 5
    # permission prefix derived from the path for the row-action / table-ACL layer
    assert (
        by[("/widgets", "GET")].resource_permission == "shop.widget"
        or by[("/widgets", "GET")].resource_permission == "widgets"
    )
