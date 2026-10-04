"""The data-model contract domain: columns, the TableModel declaration, inheritance, and the
resolved schema."""

from moderatorim.sdk.models.field import (
    FieldChoice,
    FieldType,
    TableColumn,
    choice,
    listref,
    ref,
    text,
)
from moderatorim.sdk.models.inherit import Extends
from moderatorim.sdk.models.model import ID_FIELD, SOFT_DELETE_FIELD, TableModel
from moderatorim.sdk.models.schema import ResolvedColumn, ResolvedSchema

__all__ = [
    "TableColumn",
    "FieldType",
    "FieldChoice",
    "text",
    "ref",
    "listref",
    "choice",
    "TableModel",
    "ID_FIELD",
    "SOFT_DELETE_FIELD",
    "Extends",
    "ResolvedColumn",
    "ResolvedSchema",
]
