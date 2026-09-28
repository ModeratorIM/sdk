"""Tests for the ``DataColumns`` component (ui-view-components) — the column-visibility control:
a view_column icon trigger + a Beer CSS popup menu of column checkboxes. Presentation-only.
"""

from __future__ import annotations

from moderatorim.ui import ColumnOption, DataColumns


def _cols() -> str:
    return str(
        DataColumns(
            [
                ColumnOption(key="email", label="Email", shown=True),
                ColumnOption(key="name", label="Name", shown=False),
            ],
            base_path="/admin/users",
        )
    )


def test_icon_trigger_and_beer_menu() -> None:
    html = _cols()
    assert "view_column" in html  # icon trigger
    assert 'title="Columns"' in html
    assert "data-mim-columns-toggle" in html  # JS toggle hook
    assert "mim-cols-menu" in html  # Beer popup <menu>


def test_checkboxes_reflect_visibility() -> None:
    html = _cols()
    assert 'value="email"' in html and 'value="name"' in html
    # shown column is checked, hidden is not
    assert 'value="email"' in html and "checked" in html
    # posts the checked set to {base_path}/columns
    assert 'hx-post="/admin/users/columns"' in html


def test_no_options_renders_nothing() -> None:
    assert str(DataColumns([], base_path="/x")) == ""
