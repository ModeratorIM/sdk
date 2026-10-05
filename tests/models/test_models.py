"""Contract tests for the models domain (TableColumn/FieldType, TableModel, Extends,
ResolvedSchema)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import (
    Choice,
    Extends,
    FieldType,
    ResolvedColumn,
    ResolvedSchema,
    TableColumn,
    TableModel,
    assert_valid_override,
    choice,
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


def test_column_choice_invariants() -> None:
    assert choice("status", Choice(value="a", label="A"), Choice(value="b", label="B")).choices == (
        Choice(value="a", label="A"),
        Choice(value="b", label="B"),
    )
    with pytest.raises(ValueError, match="CHOICE column"):
        TableColumn(name="s", type=FieldType.CHOICE)
    # duplicate choice values are rejected
    with pytest.raises(ValueError, match="duplicate choice values"):
        TableColumn(
            name="s",
            type=FieldType.CHOICE,
            choices=(Choice(value="a", label="A"), Choice(value="a", label="A2")),
        )


def test_choice_source_dynamic_options() -> None:
    from moderatorim.sdk import ChoiceReference

    # a CHOICE column may source its options from live data (a ChoiceReference) instead of a static
    # Choice tuple — both go through the single `choices=` field.
    col = TableColumn(
        name="source",
        type=FieldType.CHOICE,
        choices=ChoiceReference(model="core_app_permission", column="app"),
    )
    assert col.choices == ChoiceReference(model="core_app_permission", column="app")

    # label_column: show one column, store another (code stored, endonym shown)
    lc = TableColumn(
        name="language",
        type=FieldType.CHOICE,
        choices=ChoiceReference(model="core_language", column="code", label_column="name"),
    )
    assert isinstance(lc.choices, ChoiceReference)
    assert lc.choices.label_column == "name"

    # where: equality filters scope which rows are offered (e.g. only active catalog rows)
    wf = TableColumn(
        name="language",
        type=FieldType.CHOICE,
        choices=ChoiceReference(
            model="core_language", column="code", label_column="name", where=(("active", True),)
        ),
    )
    assert isinstance(wf.choices, ChoiceReference)
    assert wf.choices.where == (("active", True),)

    # a CHOICE column still requires `choices` (a Choice tuple or a ChoiceReference)
    with pytest.raises(ValueError, match="requires `choices`"):
        TableColumn(name="s", type=FieldType.CHOICE)

    # `choices` is only valid on a CHOICE column (a ChoiceReference on a TEXT column is rejected)
    with pytest.raises(ValueError, match="only valid on a CHOICE"):
        TableColumn(name="s", type=FieldType.TEXT, choices=ChoiceReference(model="m", column="c"))

    # ChoiceReference requires non-empty model + column
    with pytest.raises(ValueError, match="model must be non-empty"):
        ChoiceReference(model="", column="c")
    with pytest.raises(ValueError, match="column must be non-empty"):
        ChoiceReference(model="m", column="")


def test_max_length_only_on_text() -> None:
    assert TableColumn(name="n", type=FieldType.TEXT, max_length=200).max_length == 200
    with pytest.raises(ValueError, match="max_length"):
        TableColumn(name="n", type=FieldType.INTEGER, max_length=200)


def test_default_type_consistency() -> None:
    assert TableColumn(name="b", type=FieldType.BOOLEAN, default=False).default is False
    with pytest.raises(ValueError, match="BOOLEAN"):
        TableColumn(name="b", type=FieldType.BOOLEAN, default="yes")
    with pytest.raises(ValueError, match="not in choice values"):
        TableColumn(
            name="s",
            type=FieldType.CHOICE,
            choices=(Choice(value="a", label="A"), Choice(value="b", label="B")),
            default="c",
        )


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
    # the implicit audit columns are reserved too (view-column-resolution R1)
    for reserved in ("deleted_at", "created_at", "created_by", "updated_at", "updated_by"):
        with pytest.raises(ValueError, match="reserved"):
            TableModel(
                name="app_thing",
                columns=(TableColumn(name=reserved, type=FieldType.DATETIME),),
            )


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


def test_assert_valid_override_allows_presentation_facets() -> None:
    # A view override may re-skin: label/help/display/read_only/active — no raise.
    assert_valid_override(
        TableColumn(
            name="email",
            type=FieldType.TEXT,
            label="Email address",
            help="your login",
            display=True,
            read_only=True,
        )
    )


def test_assert_valid_override_rejects_storage_facets() -> None:
    # Setting any inherit-only (storage) facet on an override is rejected (R4/R5).
    for bad in (
        TableColumn(name="email", type=FieldType.TEXT, required=True),
        TableColumn(name="email", type=FieldType.TEXT, unique=True),
        TableColumn(name="email", type=FieldType.TEXT, max_length=320),
        TableColumn(name="email", type=FieldType.TEXT, encrypt=True),
        TableColumn(name="email", type=FieldType.TEXT, default="x"),
        TableColumn(
            name="tier",
            type=FieldType.CHOICE,
            choices=(Choice(value="a", label="A"),),
        ),
        TableColumn(name="owner", type=FieldType.REF, relation="core_user"),
    ):
        with pytest.raises(ValueError, match="may not set storage facet"):
            assert_valid_override(bad)
