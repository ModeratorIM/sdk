"""Tests for the ``DataFilter`` shell (ui-view-components) — the filter_list icon toggle + a
below-search panel holding caller-composed condition rows + Add + Apply. Presentation-only.
"""

from __future__ import annotations

from moderatorim.ui import DataFilter, tag


def test_icon_toggle_and_panel() -> None:
    row = tag("div", "ROW", **{"class": "mim-filter-row"})
    html = str(DataFilter([row], base_path="/admin/users"))
    assert "filter_list" in html  # icon trigger
    assert 'title="Filters"' in html
    assert "mim-filter-panel" in html  # the below-search expandable region
    assert 'data-mim-filter-toggle="true"' in html  # JS toggle hook


def test_rows_add_and_apply() -> None:
    row = tag("div", "ROW-A", **{"class": "mim-filter-row"})
    tpl = tag("div", "BLANK", **{"class": "mim-filter-row"})
    html = str(DataFilter([row], template_row=tpl, base_path="/admin/users"))
    assert "ROW-A" in html  # the active condition row is composed in
    assert "mim-filter-add" in html and "mim-filter-apply" in html
    assert "mim-filter-template" in html  # clone prototype for new rows
    assert 'hx-get="/admin/users"' in html  # Apply hx-GETs the list region


def test_no_fields_renders_nothing() -> None:
    assert str(DataFilter([], has_fields=False)) == ""
