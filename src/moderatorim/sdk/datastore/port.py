"""The ``DataStore`` port — persistence behind a narrow interface.

A backend implements ``DataStore`` to provision tables and read/write records as plain dicts. The
query surface is deliberately narrow: a fixed set of filter operators (no arbitrary query language),
so every backend implements it faithfully and no app can smuggle backend-specific query semantics
through the port.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from moderatorim.sdk.models.schema import ResolvedSchema

# A record is a plain dict — the port never leaks an ORM row or a backend-native object.
Record = dict[str, Any]


class FilterOp(Enum):
    """The fixed, backend-neutral filter-operator set. Compound queries AND a list of clauses."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    CONTAINS = "contains"  # substring / membership (backend maps to LIKE / array-contains)


@dataclass(frozen=True, slots=True)
class Filter:
    """One filter clause: ``field <op> value``. A list is ANDed by :meth:`DataStore.list`; there is
    no raw-query escape hatch."""

    field: str
    op: FilterOp
    value: Any

    def __post_init__(self) -> None:
        if not self.field:
            raise ValueError("Filter.field must be a non-empty field name")
        if self.op is FilterOp.IN and not isinstance(self.value, list | tuple | set):
            raise ValueError("FilterOp.IN requires a list/tuple/set value")


@dataclass(frozen=True, slots=True)
class Search:
    """A free-text search: match ``term`` (case-insensitive substring) against ANY of ``fields``.

    This is the ONE place the query surface expresses OR — a search box types one term that may
    match several columns. Backends emit ``(field1 ILIKE %term% OR field2 ILIKE %term% …)`` and AND
    that group with the :class:`Filter` list (which stays AND-only). The generic filter list is
    deliberately NOT extended to carry OR — search is a distinct, bounded, typed capability, so no
    backend has to grow an arbitrary boolean-expression engine. LIKE metacharacters in ``term`` are
    treated as literals by the backend (escaped), so a ``%`` in a search box is not a wildcard. An
    empty ``term`` or empty ``fields`` is a no-op (matches all rows)."""

    term: str
    fields: tuple[str, ...]

    def is_empty(self) -> bool:
        return not self.term or not self.fields


# Module-scope aliases so annotations don't resolve `list` inside the class (where the `list`
# METHOD shadows the builtin under string-evaluated annotations).
FilterList = list[Filter]
RecordList = list[Record]


@runtime_checkable
class DataStore(Protocol):
    """Persistence port. Backends implement this; the core depends only on it.

    Records are plain dicts keyed by field name. Every model carries an implicit ``id`` (str)
    primary key and, when soft-delete is enabled, a ``deleted_at`` marker managed by the backend.
    """

    async def ensure_table(self, schema: ResolvedSchema) -> None:
        """Provision (create or migrate) the table for a resolved schema. Idempotent."""
        ...

    async def get(self, table: str, id: str) -> Record | None:
        """Fetch one record by primary key, or ``None`` if absent / soft-deleted."""
        ...

    async def list(
        self,
        table: str,
        filters: FilterList | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
        search: Search | None = None,
    ) -> RecordList:
        """Return records matching ALL ``filters`` (ANDed) AND, when given, the ``search`` group
        (its fields ORed), with optional paging/ordering."""
        ...

    async def create(self, table: str, data: Record) -> Record:
        """Insert a record. If ``id`` is absent the backend assigns one. Returns the stored row."""
        ...

    async def update(self, table: str, id: str, data: Record) -> Record:
        """Partially update a record by id (only the supplied fields). Returns the stored row."""
        ...

    async def delete(self, table: str, id: str) -> None:
        """Delete by id. Soft delete (set ``deleted_at``) when the schema enables it, else hard."""
        ...

    async def count(
        self, table: str, filters: FilterList | None = None, *, search: Search | None = None
    ) -> int:
        """Count records matching ALL ``filters`` (ANDed) AND the optional ``search`` group."""
        ...


class TableAccessDenied(Exception):
    """Raised when a caller is denied a table-level operation by the table-ACL gate
    (:attr:`TableModel.role`, enforced in the core-owned guarded store — see moderatorim-table-acl).

    Distinct from a route-layer permission denial: this is the DATA floor (L1), refused because the
    caller's principal holds none of the table's declared roles. The routing framework maps an
    uncaught instance to a 403. ``table`` is the physical table name, ``op`` the attempted operation
    (e.g. ``"list"``), ``principal`` a short principal descriptor for the log/message.
    """

    def __init__(self, table: str, op: str, principal: str = "") -> None:
        self.table = table
        self.op = op
        self.principal = principal
        who = f" for {principal}" if principal else ""
        super().__init__(f"table-ACL: {op!r} on {table!r} denied{who}")
