"""Tests for the ``DataFilter`` component (ui-view-components) — the multi-field filter control:
a filter_list icon toggle, a below-search panel with removable active-condition chips and an
add-condition builder. Presentation-only.
"""

from __future__ import annotations

from moderatorim.ui import DataFilter, FilterField, FilterState


def _filter(active: tuple[tuple[str, str, str], ...] = ()) -> str:
    state = FilterState(
        fields=(
            FilterField(key="email", label="Email", ops=("eq", "contains")),
            FilterField(key="active", label="Active", ops=("eq",)),
        ),
        active=active,
    )
    return str(DataFilter(state, base_path="/admin/users"))


def test_icon_toggle_and_panel() -> None:
    html = _filter()
    assert "filter_list" in html  # icon trigger
    assert 'title="Filters"' in html
    assert "mim-filter-panel" in html  # the below-search expandable region


def test_ops_catalogue_and_builder() -> None:
    html = _filter()
    assert 'data-ops="email:eq,contains;active:eq"' in html  # per-field ops for the JS
    assert "mim-filter-add" in html and "mim-filter-apply" in html
    assert "mim-filter-template" in html  # clone template for new rows


def test_active_conditions_render_as_removable_chips() -> None:
    html = _filter(active=(("email", "contains", "x.com"),))
    assert "mim-filter-chip" in html
    assert "Email contains x.com" in html  # chip text
    assert "mim-filter-chip-remove" in html  # the ✕
    # the chip carries the composed param so it re-submits on Apply
    assert 'name="f_email_contains"' in html and 'value="x.com"' in html


def test_no_fields_renders_nothing() -> None:
    assert str(DataFilter(FilterState(), base_path="/x")) == ""
