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
