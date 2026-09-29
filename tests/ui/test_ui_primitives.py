"""Tests for the ``moderatorim.ui`` primitive layer.

Includes the public-API snapshot (the mechanical half of the versioning policy) and the
markup-well-formedness regression that content-only assertions once missed (the ``class_`` →
broken ``class-=`` bug): assert attribute NAMES are well-formed, not just that content is present.
"""

from __future__ import annotations

import moderatorim.ui
from moderatorim.ui import Component, Raw, attrs, esc, tag

# The frozen public surface of moderatorim.ui. Update DELIBERATELY with a version bump + CHANGELOG.
EXPECTED_PUBLIC_API = {
    # primitives
    "Component",
    "Raw",
    "attrs",
    "esc",
    "tag",
    # assets
    "ui_asset_dir",
    "ui_asset_tags",
    # generic BeerCSS components
    "Alert",
    "Avatar",
    "Button",
    "Card",
    "Column",
    "ColumnOption",
    "ConditionField",
    "DataColumns",
    "DataFilter",
    "DataFilterCondition",
    "DataRow",
    "DataRowActions",
    "DataTable",
    "Field",
    "Grid",
    "Header",
    "Icon",
    "Input",
    "Nav",
    "PageState",
    "Pills",
    "Row",
    "SearchState",
    "Select",
    "SortState",
    "Stepper",
    "Switch",
    "Textarea",
    # model field rendering
    "render_column",
    "column_validators",
}


def test_public_api_snapshot() -> None:
    exported = {n for n in moderatorim.ui.__all__}
    assert exported == EXPECTED_PUBLIC_API
    for name in EXPECTED_PUBLIC_API:
        assert hasattr(moderatorim.ui, name), f"missing public name: {name}"


def test_class_attr_is_well_formed() -> None:
    # class_ must render as class=, NOT the broken class-= (single trailing underscore stripped
    # BEFORE underscore→hyphen conversion). This is the regression content-only tests missed.
    html = tag("div", "x", class_="mim-card")
    assert 'class="mim-card"' in html
    assert "class-=" not in html


def test_hx_attr_underscore_becomes_hyphen() -> None:
    html = tag("button", "Save", hx_post="/save")
    assert 'hx-post="/save"' in html


def test_for_attr_keyword_idiom() -> None:
    html = tag("label", "Name", for_="name")
    assert 'for="name"' in html
    assert "for-=" not in html


def test_esc_escapes_text() -> None:
    assert esc("<b>") == "&lt;b&gt;"
    assert esc(Raw("<b>")) == "<b>"  # Raw passes through


def test_boolean_and_omitted_attrs() -> None:
    assert attrs({"disabled": True}) == " disabled"
    assert attrs({"hidden": False}) == ""
    assert attrs({"x": None}) == ""


def test_void_element_self_closes() -> None:
    assert tag("input", type="text") == '<input type="text">'


def test_component_composes_as_child() -> None:
    class Btn(Component):
        def render(self) -> Raw:
            return tag("button", "Save")

    # A Component passed as a child renders via __html__ and is not re-escaped.
    html = tag("div", Btn())
    assert "<button>Save</button>" in html
