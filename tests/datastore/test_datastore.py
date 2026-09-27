"""Contract tests for the datastore domain (the DataStore port + Filter/FilterOp)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import DataStore, Filter, FilterOp, TableAccessDenied


def test_table_access_denied_carries_context() -> None:
    err = TableAccessDenied("moderation_report", "list", "user:42")
    assert err.table == "moderation_report"
    assert err.op == "list"
    assert err.principal == "user:42"
    msg = str(err)
    assert "moderation_report" in msg and "list" in msg and "user:42" in msg


def test_table_access_denied_principal_optional() -> None:
    err = TableAccessDenied("core_role", "create")
    assert err.principal == ""
    assert "core_role" in str(err) and "create" in str(err)


def test_table_access_denied_is_exception() -> None:
    with pytest.raises(TableAccessDenied):
        raise TableAccessDenied("t", "get")


def test_filter_in_requires_sequence() -> None:
    assert Filter("x", FilterOp.EQ, 1).op is FilterOp.EQ
    with pytest.raises(ValueError, match="IN requires"):
        Filter("x", FilterOp.IN, 1)


def test_datastore_is_runtime_checkable_protocol() -> None:
    class Fake:
        async def ensure_table(self, schema: object) -> None: ...
        async def get(self, table: str, id: str) -> object: ...
        async def list(self, table: str, filters: object = None, **kw: object) -> list: ...  # type: ignore[type-arg]
        async def create(self, table: str, data: object) -> object: ...
        async def update(self, table: str, id: str, data: object) -> object: ...
        async def delete(self, table: str, id: str) -> None: ...
        async def count(self, table: str, filters: object = None) -> int: ...

    assert isinstance(Fake(), DataStore)
