"""Dashboard widget descriptors (metrics, cards, charts, DashboardView).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricSource:
    """WHAT table a single-number widget reads — the dashboard analogue of ``PageView.model`` + a
    view's filters. ``agg`` over ``model.name`` restricted by ``filters``; ``column`` is required
    for a non-count aggregate. Resolved by the engine via ``ctx.store`` (table-ACL enforced)."""

    model: object  # a ViewModel/TableModel (names the table), like PageView.model
    agg: str = "count"  # count | sum | avg | min | max
    column: str = ""  # required for non-count aggs
    filters: tuple[Any, ...] = ()  # tuple[Filter, ...] — the datastore filter grammar


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesSource:
    """A chart's multi-point series: the same table binding plus a GROUP BY, so the engine returns
    ``[(group_label, value)]`` — one point per distinct ``group_by`` value (or date ``bucket``)."""

    model: object
    group_by: str  # column to group rows by (one bar per distinct value)
    agg: str = "count"
    column: str = ""
    filters: tuple[Any, ...] = ()
    bucket: str = ""  # optional date bucket for a date group_by: day | week | month


@dataclass(frozen=True, slots=True, kw_only=True)
class StatCard:
    """A single generic metric: big value + label + optional ▲/▼ delta vs. a prior period."""

    label: str
    source: MetricSource
    delta_source: MetricSource | None = None  # optional prior-period metric for the delta
    span: int = 3  # BeerCSS 12-col grid span
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)


@dataclass(frozen=True, slots=True)
class ScoreBand:
    """One threshold band of a ScoreCard. The first band (in declared order) whose ``upto`` is
    >= the value wins, setting the gauge fill + status label."""

    upto: float
    label: str
    intent: str = "neutral"  # up | down | neutral -> fill/status color (CSS var)


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreCard:
    """A single score on a bounded scale (default 0..``max``), rendered as a server-SVG gauge with
    threshold ``bands``. The moderation policy-score surface."""

    label: str
    source: MetricSource
    bands: tuple[ScoreBand, ...] = ()
    max: float = 100.0
    span: int = 3
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)


@dataclass(frozen=True, slots=True, kw_only=True)
class BarChart:
    """A labelled vertical bar chart, server-rendered SVG, from a grouped ``SeriesSource``."""

    title: str
    source: SeriesSource
    span: int = 6
    height: int = 160  # px, SVG viewport height
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)


@dataclass(frozen=True, slots=True, kw_only=True)
class DashboardView:
    """A dashboard = an ordered set of visual widgets (StatCard | ScoreCard | BarChart) laid out in
    the BeerCSS grid. Pure declaration; the renderer dispatches by widget class name."""

    widgets: tuple[object, ...] = ()
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)
