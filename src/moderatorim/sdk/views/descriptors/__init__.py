"""Declarative view descriptors — app-facing model-driven-view API.

Split into cohesive modules (SDK cleanup G3); this package re-exports the full public set so every
``from moderatorim.sdk.views.descriptors import X`` import keeps resolving unchanged.
"""

from moderatorim.sdk.views.descriptors.common import (
    Field,
    FormOverview,
)
from moderatorim.sdk.views.descriptors.dashboard import (
    BarChart,
    DashboardView,
    MetricSource,
    ScoreBand,
    ScoreCard,
    SeriesSource,
    StatCard,
)
from moderatorim.sdk.views.descriptors.form import (
    FormAction,
    FormFields,
    FormHtml,
    FormList,
    FormSave,
    FormTab,
    FormView,
    ModalAction,
    ModalView,
    StatusBadge,
    ViewExtension,
)
from moderatorim.sdk.views.descriptors.list_ import (
    GridView,
    ListCard,
    ListCardAction,
    ListCardField,
    ListView,
)
from moderatorim.sdk.views.descriptors.route import (
    PageRoute,
    Permission,
    PermissionAction,
    Route,
    RouteMethod,
    ViewRoute,
)
from moderatorim.sdk.views.descriptors.view import (
    CalendarView,
    PageView,
    ViewModel,
)

__all__ = [
    "BarChart",
    "CalendarView",
    "DashboardView",
    "Field",
    "FormAction",
    "FormFields",
    "FormHtml",
    "FormList",
    "FormOverview",
    "FormSave",
    "FormTab",
    "FormView",
    "ListCard",
    "ListCardAction",
    "ListCardField",
    "GridView",
    "ListView",
    "MetricSource",
    "ModalAction",
    "ModalView",
    "PageRoute",
    "PageView",
    "Permission",
    "PermissionAction",
    "Route",
    "RouteMethod",
    "ScoreBand",
    "ScoreCard",
    "SeriesSource",
    "StatCard",
    "StatusBadge",
    "ViewExtension",
    "ViewModel",
    "ViewRoute",
]
