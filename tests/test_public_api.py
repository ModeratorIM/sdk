"""Public-API guard: the exact set of names exported from ``moderatorim.sdk``.

This is the mechanical half of the versioning policy (see VERSIONING.md). The SDK's public surface
is a compatibility contract, so any change to it must be a CONSCIOUS decision:

- ADDING a name → this test fails → add the name below, and it is a MINOR (pre-1.0: PATCH→MINOR per
  the policy) bump + a CHANGELOG `Added` entry.
- REMOVING/RENAMING a name → this test fails → it is a BREAKING change (MAJOR; pre-1.0 MINOR) + a
  CHANGELOG `Removed`/`Changed` entry + a deprecation window per the policy.

If this test fails and you did not intend a public-API change, you exported (or dropped) something
by accident — fix the code, not this snapshot.
"""

from __future__ import annotations

import moderatorim.sdk

# The frozen public surface. Update DELIBERATELY, alongside a version bump + CHANGELOG entry.
EXPECTED_PUBLIC_API = {
    # models
    "TableModel",
    "TableColumn",
    "FieldType",
    "Extends",
    "ResolvedColumn",
    "ResolvedSchema",
    "ID_FIELD",
    "SOFT_DELETE_FIELD",
    "ref",
    "enum",
    "listref",
    "text",
    # datastore port
    "DataStore",
    "Filter",
    "FilterList",
    "FilterOp",
    "Record",
    "RecordList",
    # cachestore port
    "CacheStore",
    # bus
    "Event",
    "EventKind",
    "Action",
    "ActionKind",
    "EventBus",
    "Handler",
    # manifest / registry
    "Manifest",
    "UnitType",
    "NavEntry",
    "AuthMethod",
    # validation
    "Validator",
    "Required",
    "MinLength",
    "MaxLength",
    "Min",
    "Max",
    "Pattern",
    "Email",
    "OneOf",
    "PasswordPolicy",
    "ValidationError",
    "Result",
    "validate_field",
    "validate_form",
    "build_validators",
    # web facade
    "App",
    "Ctx",
    "Page",
    "Fragment",
    "Rendered",
    "Redirect",
    "redirect",
    "RouteDef",
    "Kind",
}


def test_public_api_matches_snapshot() -> None:
    actual = set(moderatorim.sdk.__all__)
    added = actual - EXPECTED_PUBLIC_API
    removed = EXPECTED_PUBLIC_API - actual
    assert not added and not removed, (
        f"moderatorim.sdk public API changed — added={sorted(added)} removed={sorted(removed)}. "
        "This is a versioned contract change: update EXPECTED_PUBLIC_API here, bump the version, "
        "and add a CHANGELOG entry (see VERSIONING.md)."
    )


def test_every_public_name_is_importable() -> None:
    # __all__ must not advertise a name that isn't actually exported.
    for name in moderatorim.sdk.__all__:
        assert hasattr(moderatorim.sdk, name), f"__all__ lists {name!r} but it is not importable"
