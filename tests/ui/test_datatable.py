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
    # the search box id is PAGE-SPECIFIC (derived from region_id), not a global "mim-list-search",
    # so hx-preserve can't carry it across a cross-page body swap.
    assert 'id="mim-list-search-mim-list-region"' in html
    assert 'hx-preserve="true"' in html  # survives the region's OWN self-swap, keeps focus
    assert 'value="ab"' in html
    assert 'class="mim-list-search"' in html  # class unchanged (CSS selector still matches)


def test_search_box_id_is_per_page_no_preserve_collision() -> None:
    # Regression: searching on /users then navigating to /roles (a full-body hx-swap) must NOT
    # preserve the /users search box into /roles. hx-preserve matches by id, so the two pages'
    # search boxes must have DIFFERENT ids. Different region_ids => different search ids.
    users = _table(
        base_path="/admin/users", region_id="mim-list-region", search=SearchState(term="x")
    )
    roles = _table(base_path="/admin/roles", region_id="mim-roles-region", search=SearchState())
    import re

    uid = re.search(r'id="(mim-list-search-[^"]+)"', users).group(1)
    rid = re.search(r'id="(mim-list-search-[^"]+)"', roles).group(1)
    assert uid != rid  # no shared id => htmx has nothing to preserve across the nav
    # and each box targets its OWN resource/region
    assert 'hx-get="/admin/users"' in users and 'hx-get="/admin/roles"' in roles


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


def test_multiselect_renders_checkbox_column() -> None:
    from moderatorim.ui.datatable import DataRow

    rows = [
        DataRow(id="1", cells={"email": "a@x.com", "_checked": True}),
        DataRow(id="2", cells={"email": "b@x.com"}),
    ]
    html = _table(rows=rows, multiselect=True, select_key="email")
    # a header select-all checkbox ...
    assert "mim-list-selectall" in html and 'data-mim-select-all="true"' in html
    # ... one row checkbox per row, posting under name="selected" ...
    assert html.count("mim-list-rowcheck") == 2
    assert html.count('name="selected"') == 2
    # ... value taken from select_key, with _checked rows pre-checked ...
    assert 'value="a@x.com"' in html and 'value="b@x.com"' in html
    assert 'checked="checked"' in html  # the _checked row
    # ... and the unchecked row is not pre-checked.
    assert "checked" not in html.split('value="b@x.com"')[1][:40]


def test_multiselect_off_has_no_checkbox_column() -> None:
    html = _table()  # default multiselect=False
    assert "mim-list-rowcheck" not in html and "mim-list-selectall" not in html
