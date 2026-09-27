"""Declarative event subscription (design §1: prefer declaration objects over imperative wiring).

A :class:`Subscription` names an :class:`EventKind` + a ``factory`` — a ``(core) -> Handler``
callable core invokes ONCE at boot to build the bound handler (closing over the store / bus it
needs), then subscribes it. This replaces the per-app imperative ``register(core)`` +
``core.bus.subscribe(kind, make_handler(core.store))`` boilerplate: an app declares
``subscriptions = (Subscription(EventKind.X, factory=make_handler),)`` on its manifest and core
wires it. The factory keeps the handler's dependency-injection (store/core) explicit while making
the WIRING declarative.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from moderatorim.sdk.bus.events import EventKind


@dataclass(frozen=True, slots=True)
class Subscription:
    """A manifest-declared event subscription. ``factory`` is ``(core) -> Handler``; core calls it
    at boot with the app's core context and subscribes the returned handler to ``kind``."""

    kind: EventKind
    factory: Callable[[Any], Any]

    def __post_init__(self) -> None:
        if self.factory is None:
            raise ValueError("Subscription.factory is required (a (core) -> Handler callable)")
