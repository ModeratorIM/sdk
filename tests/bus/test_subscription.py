"""Contract tests for the declarative Subscription + optional Manifest.register."""

from __future__ import annotations

import pytest

from moderatorim.sdk import EventKind, Subscription, UnitType
from moderatorim.sdk.registry.manifest import Manifest


def test_subscription_carries_kind_and_factory() -> None:
    def make(core):  # noqa: ANN001, ANN202
        async def handler(event):  # noqa: ANN001, ANN202
            return []

        return handler

    sub = Subscription(kind=EventKind.MESSAGE_RECEIVED, factory=make)
    assert sub.kind is EventKind.MESSAGE_RECEIVED and sub.factory is make
    with pytest.raises(ValueError, match="factory"):
        Subscription(kind=EventKind.MESSAGE_RECEIVED, factory=None)


def test_manifest_register_is_optional_and_subscriptions_default_empty() -> None:
    # An app that only declares needs no register hook.
    m = Manifest(name="declared_only", type=UnitType.APP)
    assert m.subscriptions == () and callable(m.register)
    m.register(object())  # the default no-op is safely callable
