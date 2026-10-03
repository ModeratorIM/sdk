"""Contract tests for the models domain (TableColumn/FieldType, TableModel, Extends,
ResolvedSchema)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import (
    Extends,
    FieldType,
    ResolvedColumn,
    ResolvedSchema,
    TableColumn,
    TableModel,
    enum,
    listref,
    ref,
)


def test_column_source_defaults_to_none_not_core() -> None:
    # source is manifest-derived (filled by core at boot). The dataclass default is None
    # ("unattributed"), deliberately NOT "core" — so a forgotten source can never silently
    # masquerade as core-owned (app-owned-columns design §1).
    assert TableColumn(name="c", type=FieldType.TEXT).source is None
    # An explicit source is preserved as given (core's stamp overwrites it at boot regardless).
    assert TableColumn(name="c", type=FieldType.TEXT, source="shop").source == "shop"


def test_column_ref_requires_relation() -> None:
    with pytest.raises(ValueError, match="requires `relation`"):
        TableColumn(name="c", type=FieldType.REF)
    assert ref("contact", "contact_contact").relation == "contact_contact"


def test_listref_requires_relation() -> None:
    assert listref("recipients", "core_contact").type is FieldType.LISTREF
    with pytest.raises(ValueError, match="requires `relation`"):
        TableColumn(name="r", type=FieldType.LISTREF)


def test_column_enum_invariants() -> None:
    assert enum("status", "a", "b").choices == ("a", "b")
    with pytest.raises(ValueError, match="ENUM column"):
        TableColumn(name="s", type=FieldType.ENUM)


def test_max_length_only_on_text() -> None:
    assert TableColumn(name="n", type=FieldType.TEXT, max_length=200).max_length == 200
    with pytest.raises(ValueError, match="max_length"):
        TableColumn(name="n", type=FieldType.INTEGER, max_length=200)


def test_default_type_consistency() -> None:
    assert TableColumn(name="b", type=FieldType.BOOLEAN, default=False).default is False
    with pytest.raises(ValueError, match="BOOLEAN"):
        TableColumn(name="b", type=FieldType.BOOLEAN, default="yes")
    with pytest.raises(ValueError, match="not in choices"):
        TableColumn(name="s", type=FieldType.ENUM, choices=("a", "b"), default="c")


def test_model_table_must_be_namespaced() -> None:
    with pytest.raises(ValueError, match="app-namespaced"):
        TableModel(name="contacts")
    good = TableModel(
        name="contact_contact",
        columns=(TableColumn(name="name", type=FieldType.TEXT),),
    )
    assert good.name == "contact_contact"


def test_model_reserved_column_rejected() -> None:
    with pytest.raises(ValueError, match="reserved"):
        TableModel(name="app_thing", columns=(TableColumn(name="id", type=FieldType.TEXT),))


def test_model_display_cardinality() -> None:
    with pytest.raises(ValueError, match="display=True"):
        TableModel(
            name="app_thing",
            columns=(
                TableColumn(name="a", type=FieldType.TEXT, display=True),
                TableColumn(name="b", type=FieldType.TEXT, display=True),
            ),
        )


def test_model_role_is_table_acl() -> None:
    m = TableModel(name="app_thing", role=("app.thing.read",))
    assert m.role == ("app.thing.read",)


def test_extends_validates() -> None:
    e = Extends(base="core.auth.User", delegate_to="contact_contact", link="contact_id")
    assert e.link == "contact_id"
    with pytest.raises(ValueError, match="link"):
        Extends(base="x", delegate_to="y", link="not an identifier")


def test_resolved_schema_column_names() -> None:
    s = ResolvedSchema(
        table="app_thing",
        columns=(ResolvedColumn("id", TableColumn(name="id", type=FieldType.TEXT)),),
        soft_delete=False,
    )
    assert s.column_names() == ("id",)


def test_model_acl_base() -> None:
    # acl is an optional permission base; empty by default (open table).
    assert TableModel(name="app_thing").acl == ""
    gated = TableModel(name="core_session", acl="core.session")
    assert gated.acl == "core.session"
    # role (deprecated) still constructs alongside, for the one-release overlap.
    legacy = TableModel(name="core_session", role=("core.session_manager",))
    assert legacy.role == ("core.session_manager",)
