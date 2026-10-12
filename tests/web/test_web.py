"""Facade unit tests for the SDK web surface (registration only — dispatch is core's adapter)."""

from __future__ import annotations

from moderatorim.sdk import App, Ctx, Fragment, Kind, Page, Redirect, Rendered, redirect


def test_page_action_post_record_routedefs() -> None:
    app = App()

    @app.page("/hello", title="Hello", nav="Home")
    def hello(ctx: Ctx) -> Page:
        return Page(title="Hello", content=["hi"])

    @app.action("/go", permission="a.b")
    def go(ctx: Ctx) -> Redirect:
        return redirect("/dest")

    @app.post("/chip")
    def chip(ctx: Ctx) -> Fragment:
        return Fragment("<span>ok</span>")

    routes = app.routes
    assert [r.path for r in routes] == ["/hello", "/go", "/chip"]
    assert routes[0].kind is Kind.PAGE and routes[0].methods == ("GET",) and routes[0].nav == "Home"
    assert routes[1].kind is Kind.ACTION and routes[1].permission == "a.b"
    assert routes[2].kind is Kind.POST and routes[2].methods == ("POST",)


def test_action_custom_methods() -> None:
    app = App()

    @app.action("/x", methods=("POST", "DELETE"))
    def x(ctx: Ctx) -> Redirect:
        return redirect("/")

    assert app.routes[0].methods == ("POST", "DELETE")


def test_form_view_binds_single_rowid_action_route() -> None:
    """table-driven-actions: form_view emits ONE {id}/action/{action_id} route (row-id, core
    dispatcher) — NOT one positional /action/{idx} per declared FormAction. The route carries the
    resource_permission + a .read floor; the per-row role gate is enforced by core's dispatcher."""
    from moderatorim.sdk import FieldType, FormAction, FormTab, FormView, TableColumn, TableModel

    model = TableModel(name="t_rec", columns=(TableColumn(name="name", type=FieldType.TEXT),))
    view = FormView(
        tabs=(
            FormTab(
                label="Detail",
                actions=(FormAction(label="A", handler=lambda c: None),),
            ),
            FormTab(
                label="More",
                actions=(FormAction(label="B", handler=lambda c: None),),
            ),
        ),
    )
    app = App()
    app.form_view("/recs", model=model, view=view, permission="x.recs")

    action_routes = [r for r in app.routes if r.kind is Kind.ACTION]
    # exactly ONE action route regardless of how many FormActions are declared (2 here)
    assert len(action_routes) == 1
    r = action_routes[0]
    assert r.path == "/recs/{id}/action/{action_id}"
    assert r.methods == ("POST",)
    assert r.permission == "x.recs.read"  # reach-the-form floor; role gate is per-row in core
    assert r.resource_permission == "x.recs"


def test_form_view_expands_per_tab_save_routes() -> None:
    """per-tab-form-save: an EDITABLE non-Detail tab (a FormFields whose model != mount model)
    expands PATCH {base}/{id}/tab/{tab_id}; Detail (model=None) keeps the whole-form {base}/{id};
    a read-only (FormList) tab expands no save route."""
    import pytest

    from moderatorim.sdk import (
        Field,
        FieldType,
        FormFields,
        FormList,
        FormTab,
        FormView,
        ListView,
        TableColumn,
        TableModel,
    )

    model = TableModel(name="t_rec", columns=(TableColumn(name="name", type=FieldType.TEXT),))
    sat = TableModel(name="t_sat", columns=(TableColumn(name="token", type=FieldType.TEXT),))
    view = FormView(
        tabs=(
            FormTab(label="Detail", order=10, views=(FormFields(fields=(Field("name"),)),)),
            FormTab(
                label="Credential",
                id="credential",
                order=20,
                views=(FormFields(model=sat, fields=(Field("token"),)),),
            ),
            FormTab(
                label="History",
                order=30,
                views=(FormList(model=sat, view=ListView(fields=())),),
            ),
        ),
    )
    app = App()
    app.form_view("/recs", model=model, view=view, permission="x.recs")

    tab_routes = [r for r in app.routes if r.kind is Kind.FORM and "/tab/" in r.path]
    assert len(tab_routes) == 1  # only the Credential tab (satellite-bound FormFields)
    tr = tab_routes[0]
    assert tr.path == "/recs/{id}/tab/credential"
    assert tr.methods == ("PATCH",)
    assert tr.form_op == "tab_update"
    assert tr.permission == "x.recs.update"
    assert tr.resource_permission == "x.recs"
    # Detail still has the whole-form PATCH {base}/{id}; no /tab/ route for it.
    whole = [r for r in app.routes if r.path == "/recs/{id}" and r.methods == ("PATCH",)]
    assert len(whole) == 1 and whole[0].form_op == "update"

    # A non-default-model FormFields tab WITHOUT an id is refused (no addressable route).
    bad = FormView(
        tabs=(
            FormTab(label="Detail", order=10, views=(FormFields(fields=(Field("name"),)),)),
            FormTab(label="Credential", order=20, views=(FormFields(model=sat, fields=()),)),
        ),
    )
    with pytest.raises(ValueError, match="must set FormTab.id"):
        App().form_view("/bad", model=model, view=bad, permission="x.bad")


def test_nav_routes_only_nav_declared() -> None:
    app = App()

    @app.page("/dash", title="Dash", nav="Dashboard")
    def dash(ctx: Ctx) -> Page:
        return Page(title="Dash", content=[])

    @app.page("/hidden", title="Hidden")
    def hidden(ctx: Ctx) -> Page:
        return Page(title="Hidden", content=[])

    navs = app.nav_routes
    assert len(navs) == 1 and navs[0].nav == "Dashboard" and navs[0].path == "/dash"


def test_primitives() -> None:
    assert redirect("/x").url == "/x"
    assert redirect("/x", replace=True).replace is True
    assert Page(title="T", content=["b"], permission="p.q.read").permission == "p.q.read"
    assert Rendered("body", status=404).status == 404
    assert Fragment("<i>").html == "<i>"


def test_ctx_cookie_and_helpers() -> None:
    ctx = Ctx(config=object(), request=object())
    ctx.set_session("tok")
    assert ctx._set_session == "tok"
    ctx.clear_session()
    assert ctx._clear_session is True and ctx._set_session is None
    ctx.set_cookie("mim_setup_ok", "k", path="/setup", max_age=3600)
    assert ctx._extra_cookies == [("mim_setup_ok", "k", "/setup", 3600)]
    assert ctx.can("anything") is False  # default predicate denies
