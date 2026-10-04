"""The ``TableModel`` declaration — an app declares a model as an INSTANCE (not a subclass),
setting ``name``, ``columns``, and an optional table-ACL ``role``.

A model is a *declaration*, not an ORM row: it describes a schema. The core provisions it through
the ``DataStore`` port; model names are app-namespaced to prevent collisions between apps.
"""

from __future__ import annotations

from dataclasses import dataclass

from moderatorim.sdk.models.field import TableColumn

# Every model carries an implicit primary key and soft-delete marker; backends honor these.
ID_FIELD = "id"
SOFT_DELETE_FIELD = "deleted_at"

# Implicit audit columns, injected by the schema resolver (never hand-declared). created_* are set
# once on insert; updated_* on every write. created_by/updated_by hold a user id ("" = system).
CREATED_AT_FIELD = "created_at"
CREATED_BY_FIELD = "created_by"
UPDATED_AT_FIELD = "updated_at"
UPDATED_BY_FIELD = "updated_by"

# Names a model may not declare — all are managed by the core/backend.
_RESERVED_COLUMN_NAMES = frozenset(
    {
        ID_FIELD,
        SOFT_DELETE_FIELD,
        CREATED_AT_FIELD,
        CREATED_BY_FIELD,
        UPDATED_AT_FIELD,
        UPDATED_BY_FIELD,
    }
)


@dataclass(frozen=True, slots=True)
class TableModel:
    """A declared model.

      * ``name`` — the model's identity AND its physical table name, prefixed with the owning unit
        (``<unit>_<name>``, lowercase snake_case, e.g. ``admin_post``). You DECLARE the full name —
        the framework does NOT generate or rewrite it. It is what ``Extends.base`` references, and
        what the backend provisions. Core validates at boot that the prefix matches the owning unit
        (``boot.py`` §6) and FAILS LOUDLY otherwise.
      * ``label`` — the human display name for the model (e.g. ``Users``), used by the views layer
        for page titles / nav. Defaults to a title-cased derivation of ``name`` when omitted.
      * ``columns`` — an ordered tuple of :class:`~moderatorim.sdk.models.field.TableColumn`.
      * ``role`` — DEPRECATED legacy table-ACL (a role-NAME tuple, op-blind). Superseded by
        ``acl`` (permission-based, per-op). Retained for one release; unused by the current store
        gate when ``acl`` is set. New models should use ``acl``.
      * ``acl`` — the TABLE ACL gate (moderatorim-table-acl-hardening): a RESOURCE-PERMISSION BASE
        like ``"core.session"``. Empty = open (governed only by the route layer). When set, the
        store gate derives the required permission PER OP and resolves the caller's effective
        permissions against it — read-family ops (get/list/count) require ``{acl}.read``, writes
        require ``{acl}.create`` / ``.update`` / ``.delete``. The SAME permission currency the
        route layer checks; super-user + the system principal bypass. Enforced in the store,
        unbypassable by apps.
      * ``soft_delete`` — if True (default), ``DataStore.delete`` is a soft delete.

    Column names ``id``, ``deleted_at``, ``created_at``, ``created_by``, ``updated_at`` and
    ``updated_by`` are reserved (managed by the core/backend).
    """

    name: str
    label: str = ""
    columns: tuple[TableColumn, ...] = ()
    role: tuple[str, ...] = ()
    acl: str = ""
    soft_delete: bool = True

    def __post_init__(self) -> None:
        _validate_name(self.name)
        _validate_columns(self.columns)

    @property
    def column_map(self) -> dict[str, TableColumn]:
        return {c.name: c for c in self.columns}

    @property
    def display_label(self) -> str:
        """The human label, deriving one from ``name`` when ``label`` was not set."""
        if self.label:
            return self.label
        # core_user -> "User"; strip the leading unit prefix, title-case the rest.
        tail = self.name.split("_", 1)[-1] if "_" in self.name else self.name
        return tail.replace("_", " ").title()


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError("TableModel.name must be a non-empty string")
    if not name.islower() or " " in name:
        raise ValueError(f"TableModel.name must be lowercase snake_case: {name!r}")
    if "_" not in name:
        raise ValueError(f"TableModel.name must be app-namespaced as '<app>_<name>' (got {name!r})")


def _validate_columns(columns: tuple[TableColumn, ...]) -> None:
    seen: set[str] = set()
    display_count = 0
    for c in columns:
        if not isinstance(c, TableColumn):
            raise TypeError(f"column must be a TableColumn, got {type(c).__name__}")
        if c.name in _RESERVED_COLUMN_NAMES:
            raise ValueError(f"column name {c.name!r} is reserved by the core")
        if c.name in seen:
            raise ValueError(f"duplicate column name {c.name!r}")
        seen.add(c.name)
        if c.display:
            display_count += 1
    if display_count > 1:
        raise ValueError("at most one column may set display=True")
