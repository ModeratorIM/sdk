"""Tests for the type->widget renderer + validator generation (foundations P3)."""

from __future__ import annotations

from moderatorim.sdk import Choice, FieldType, TableColumn
from moderatorim.ui import column_validators, render_column


def _html(column: TableColumn, value=None, **kw) -> str:
    return str(render_column(column, value, **kw).render())


def test_text_renders_input() -> None:
    html = _html(TableColumn(name="email", type=FieldType.TEXT, label="Email"))
    assert "<input" in html and 'name="email"' in html and 'type="text"' in html


def test_textarea_renders_textarea() -> None:
    html = _html(TableColumn(name="bio", type=FieldType.TEXTAREA))
    assert "<textarea" in html


def test_integer_renders_number_input() -> None:
    html = _html(TableColumn(name="age", type=FieldType.INTEGER))
    assert 'type="number"' in html


def test_boolean_renders_switch() -> None:
    html = _html(TableColumn(name="active", type=FieldType.BOOLEAN), value=True)
    assert "switch" in html and 'type="checkbox"' in html


def test_date_renders_date_input() -> None:
    assert 'type="date"' in _html(TableColumn(name="d", type=FieldType.DATE))


def test_required_column_renders_required_by_default() -> None:
    html = _html(TableColumn(name="id", type=FieldType.TEXT, required=True))
    assert "required" in html


def test_required_override_false_drops_required() -> None:
    # A filter value must be optional even when its column is a required storage column — otherwise
    # an empty required input on a hidden tab blocks the page's form submit (not-focusable error).
    html = _html(TableColumn(name="id", type=FieldType.TEXT, required=True), required=False)
    assert "required" not in html


def test_choice_renders_select_from_choices() -> None:
    html = _html(
        TableColumn(
            name="status",
            type=FieldType.CHOICE,
            choices=(
                Choice(value="open", label="Open"),
                Choice(value="closed", label="Closed"),
            ),
        )
    )
    # stored values + human labels both present; it is a <select>
    assert "<select" in html and "open" in html and "Open" in html and "Closed" in html


def test_ref_renders_select() -> None:
    html = _html(
        TableColumn(name="owner", type=FieldType.REF, relation="core_user"),
        options=[("1", "Alice")],
    )
    assert "<select" in html and "Alice" in html


def test_listref_renders_pills() -> None:
    html = _html(
        TableColumn(name="tags", type=FieldType.LISTREF, relation="core_tag"),
        selected=[("1", "urgent"), ("2", "bug")],
    )
    assert "chip" in html and "urgent" in html and "bug" in html


def test_read_only_switch_disabled() -> None:
    html = _html(TableColumn(name="x", type=FieldType.BOOLEAN, read_only=True))
    assert "disabled" in html


def test_column_validators_generated() -> None:
    vs = column_validators(TableColumn(name="n", type=FieldType.TEXT, required=True, max_length=20))
    names = [v.__class__.__name__ for v in vs]
    assert "Required" in names and "MaxLength" in names
    choice_vs = column_validators(
        TableColumn(
            name="s",
            type=FieldType.CHOICE,
            choices=(Choice(value="a", label="A"), Choice(value="b", label="B")),
        )
    )
    assert "OneOf" in [v.__class__.__name__ for v in choice_vs]
