"""The resolved-schema contract — the shape a backend's ``DataStore.ensure_table`` receives.

The core computes this (its merge of a base model + any ``Extends`` links) before any backend call;
the backend only sees the result. The merge logic (``effective_schema``) lives in core, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

from moderatorim.sdk.models.field import TableColumn


@dataclass(frozen=True, slots=True)
class ResolvedColumn:
    """One column in a resolved schema — a column plus its final name."""

    name: str
    field: TableColumn


@dataclass(frozen=True, slots=True)
class ResolvedSchema:
    """The final, materializable schema a backend provisions.

    Carries the table name, a human ``label`` (the model's display name, e.g. ``Users`` for
    ``core_user`` — empty when the model declared none), the ordered columns (including the
    implicit primary key and, when ``soft_delete`` is set, the soft-delete marker), and the
    soft_delete flag. A backend maps each column's
    :class:`~moderatorim.sdk.models.field.FieldType` onto its own storage.
    """

    table: str
    columns: tuple[ResolvedColumn, ...]
    soft_delete: bool
    label: str = ""

    def column_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)
