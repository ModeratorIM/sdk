"""The data-model contract domain: columns, the TableModel declaration, inheritance, and the
resolved schema."""

from moderatorim.sdk.models.field import (
    FIELD_TYPE_OPERATORS,
    INHERIT_ONLY_FACETS,
    OVERRIDABLE_FACETS,
    Choice,
    ChoiceReference,
    FieldType,
    TableColumn,
    assert_valid_override,
    choice,
    is_filterable,
    listref,
    operators_for,
    ref,
    text,
)
from moderatorim.sdk.models.inherit import Extends
from moderatorim.sdk.models.model import (
    CREATED_AT_FIELD,
    CREATED_BY_FIELD,
    ID_FIELD,
    SOFT_DELETE_FIELD,
    UPDATED_AT_FIELD,
    UPDATED_BY_FIELD,
    TableModel,
)
from moderatorim.sdk.models.schema import ResolvedColumn, ResolvedSchema

__all__ = [
    "TableColumn",
    "FieldType",
    "FIELD_TYPE_OPERATORS",
    "operators_for",
    "is_filterable",
    "Choice",
    "ChoiceReference",
    "text",
    "ref",
    "listref",
    "choice",
    "assert_valid_override",
    "OVERRIDABLE_FACETS",
    "INHERIT_ONLY_FACETS",
    "TableModel",
    "ID_FIELD",
    "SOFT_DELETE_FIELD",
    "CREATED_AT_FIELD",
    "CREATED_BY_FIELD",
    "UPDATED_AT_FIELD",
    "UPDATED_BY_FIELD",
    "Extends",
    "ResolvedColumn",
    "ResolvedSchema",
]
