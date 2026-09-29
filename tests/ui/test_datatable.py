"""Tests for the ``DataTable`` composite (ui-view-components).

Presentation-only: the component receives resolved data + state and renders the Beer data table
with sort links, a focus-safe realtime search, a MULTI-FIELD filter builder, pagination and
clickable rows. These assert the rendered structure the ListView renderer (and any app) relies on.
"""

from __future__ import annotations

from moderatorim.ui import (
    Column,
    DataRow,
    DataTable,
    PageState,
    SearchState,
    SortState,
)


def _table(**over: object) -> str:
    kw: dict[str, object] = dict(
        columns=[
            Column(key="email", label="Email"),
            Column(key="is_super_user", label="Super user", kind="bool"),
        ],
        rows=[
            DataRow(id="u1", cells={"email": "a@x.com", "is_super_user": True}, href="/u/u1"),
            DataRow(id="u2", cells={"email": "b@x.com", "is_super_user": False}),
        ],
        base_path="/admin/users",
    )
    kw.update(over)
    return str(DataTable(**kw))  # type: ignore[arg-type]


def test_renders_beer_table_with_rows() -> None:
    html = _table()
    assert "border stripes mim-list-table" in html  # Beer table classes
    assert "a@x.com" in html and "b@x.com" in html
    assert 'data-label="Email"' in html  # responsive card-list label


def test_bool_cell_is_an_icon() -> None:
    html = _table()
    assert "mim-cell-bool" in html
    assert ">check<" in html  # is_super_user True → check icon
    assert ">close<" in html and "mim-cell-bool-off" in html  # is_super_user False → muted close
    assert 'title="Yes"' in html and 'title="No"' in html  # accessible label


def test_sortable_header_links_to_region_sort_toggle() -> None:
    html = _table(sort=SortState(key="email", descending=False))
    assert "sort=email:desc" in html  # active asc → link toggles to desc
    assert 'hx-target="#mim-list-region"' in html
    assert "▲" in html  # asc arrow on the active column


def test_row_href_makes_the_row_clickable() -> None:
    html = _table(row_href=True)
    assert 'class="mim-list-row"' in html
    assert 'hx-get="/u/u1"' in html
    # a click inside the actions cell (menu/modal) must NOT navigate: the row's hx-trigger is
    # filtered to ignore clicks whose target is inside .mim-rowmenu.
    assert "hx-trigger=" in html and "mim-rowmenu" in html
    assert "closest(" in html  # the event filter guards on target.closest('.mim-rowmenu')
    # a row with no href is not clickable
    assert html.count("mim-list-row") == 1


def test_search_box_is_focus_safe() -> None:
    html = _table(search=SearchState(term="ab"))
    assert 'id="mim-list-search"' in html
    assert 'hx-preserve="true"' in html  # survives the region swap, keeps focus
    assert 'value="ab"' in html


def test_filter_and_columns_slots_render_in_toolbar() -> None:
    from moderatorim.ui import tag

    filt = tag("div", "FILTER-SLOT", **{"class": "mim-list-filters"})
    cols = tag("div", "COLUMNS-SLOT", **{"class": "mim-cols-editor"})
    html = _table(search=SearchState(), filter_control=filt, columns_control=cols)
    assert "FILTER-SLOT" in html and "COLUMNS-SLOT" in html
    # slots render inside the toolbar, after the search
    assert html.index("mim-list-search") < html.index("FILTER-SLOT")


def test_actions_bar_renders_above_toolbar() -> None:
    from moderatorim.ui import tag

    new_btn = tag("a", "New", **{"href": "/x/new", "class": "button"})
    html = _table(actions=[new_btn])
    assert "mim-list-actionbar" in html
    assert ">New<" in html
    # the action bar comes before the toolbar in the markup (rendered above it)
    assert html.index("mim-list-actionbar") < html.index("mim-list-toolbar")


def test_no_actions_no_bar() -> None:
    html = _table()  # no actions supplied
    assert "mim-list-actionbar" not in html  # empty → no bar rendered


def test_pagination_footer() -> None:
    html = _table(pagination=PageState(page=2, pages=3, total=42))
    assert "42 total · page 2/3" in html
    assert "page=1" in html and "page=3" in html  # prev + next links


def test_empty_state() -> None:
    html = _table(rows=[], empty_label="No users yet.")
    assert "mim-list-empty" in html
    assert "No users yet." in html
    assert "mim-list-table" not in html  # no table when empty


def test_custom_cell_escape_hatch() -> None:
    html = _table(
        columns=[Column(key="x", label="X", custom=lambda row: f"id={row['id']}")],
        rows=[DataRow(id="u9", cells={})],
    )
    assert "id=u9" in html


def test_esc_prevents_injection_in_text_cell() -> None:
    html = _table(
        columns=[Column(key="email", label="Email")],
        rows=[DataRow(id="u1", cells={"email": "<script>x</script>"})],
    )
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html
