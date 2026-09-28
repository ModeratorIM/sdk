"""Tests for ``DataFilterCondition`` — one ServiceNow-style filter row: field ▾ / operator ▾ /
type-aware value (via render_column). Changing the field hx-GETs the row endpoint.
Presentation-only.
"""

from __future__ import annotations

from moderatorim.sdk import FieldType, TableColumn
from moderatorim.ui import ConditionField, DataFilterCondition


def _fields() -> list[ConditionField]:
    return [
        ConditionField(
            column=TableColumn(name="email", type=FieldType.TEXT, label="Email"),
            ops=("contains", "eq"),
        ),
        ConditionField(
            column=TableColumn(name="active", type=FieldType.BOOLEAN, label="Active"),
            ops=("eq",),
        ),
        ConditionField(
            column=TableColumn(
                name="group_id", type=FieldType.REF, label="Group", relation="core_group"
            ),
            ops=("eq", "ne"),
            options=[("g1", "Group One")],
        ),
    ]


def test_field_change_rerenders_row_server_side() -> None:
    html = str(DataFilterCondition(_fields(), selected="email", row_path="/u/filter-row"))
    assert 'hx-get="/u/filter-row"' in html  # ServiceNow round-trip on field change
    assert 'hx-target="closest .mim-filter-row"' in html
    assert 'hx-trigger="change"' in html
    assert "mim-filter-field" in html and "mim-filter-op" in html


def test_text_field_value_is_a_text_input() -> None:
    html = str(DataFilterCondition(_fields(), selected="email", row_path="/u/filter-row"))
    assert "mim-filter-value" in html
    assert 'name="email"' in html  # render_column produced a text input
    assert "contains" in html  # its operators


def test_bool_field_value_is_a_switch() -> None:
    html = str(DataFilterCondition(_fields(), selected="active", row_path="/u/filter-row"))
    assert "checkbox" in html.lower()  # Switch renders a checkbox control


def test_ref_field_value_is_a_candidate_select() -> None:
    html = str(DataFilterCondition(_fields(), selected="group_id", row_path="/u/filter-row"))
    assert "Group One" in html and 'value="g1"' in html  # select of ref candidates


def test_prefills_op_and_value_on_active_condition() -> None:
    html = str(
        DataFilterCondition(
            _fields(), selected="email", op="eq", value="a@x.com", row_path="/u/filter-row"
        )
    )
    assert 'value="a@x.com"' in html
    # the eq operator is marked selected
    assert 'value="eq" selected="selected"' in html or 'selected="selected"' in html
