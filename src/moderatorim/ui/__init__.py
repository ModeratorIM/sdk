"""ModeratorIM UI component library — generic BeerCSS components, the single source of truth.

``moderatorim.ui`` holds ONLY generic, reusable BeerCSS components — no ModeratorIM-specific chrome
(navigation rails, account menus, branded bars, screen-title blocks live in core). Both core and
apps import these (``from moderatorim.ui import Card, Button, Header, ...``); an app composes its
own UI, e.g. ``Header("Members", actions=[Button("Invite", icon="add")])``.

A top-level peer of ``moderatorim.sdk``/``moderatorim.cli`` under the PEP 420 ``moderatorim``
namespace (SDK-owned by convention; imports stdlib + ``moderatorim.sdk`` contracts only, never
``moderatorim.core``). The BeerCSS/base assets ship here too (``ui_asset_dir``/``ui_asset_tags``).
"""

from moderatorim.ui.alert import Alert
from moderatorim.ui.assets import ui_asset_dir, ui_asset_tags
from moderatorim.ui.avatar import Avatar
from moderatorim.ui.button import Button
from moderatorim.ui.card import Card
from moderatorim.ui.component import Component
from moderatorim.ui.datacolumns import ColumnOption, DataColumns
from moderatorim.ui.datafilter import DataFilter
from moderatorim.ui.datafiltercondition import ConditionField, DataFilterCondition
from moderatorim.ui.datatable import (
    Column,
    DataRow,
    DataTable,
    PageState,
    SearchState,
    SortState,
)
from moderatorim.ui.field import Field
from moderatorim.ui.header import Header
from moderatorim.ui.html import Raw, attrs, esc, tag
from moderatorim.ui.icon import Icon
from moderatorim.ui.input import Input
from moderatorim.ui.layout import Grid, Nav, Row
from moderatorim.ui.pills import Pills
from moderatorim.ui.render import column_validators, render_column
from moderatorim.ui.select import Select
from moderatorim.ui.stepper import Stepper
from moderatorim.ui.switch import Switch
from moderatorim.ui.textarea import Textarea

__all__ = [
    # primitives
    "Component",
    "Raw",
    "attrs",
    "esc",
    "tag",
    # assets (shipped BeerCSS/MDC/base CSS+JS; host mounts + emits refs)
    "ui_asset_dir",
    "ui_asset_tags",
    # generic BeerCSS components
    "Alert",
    "Avatar",
    "Button",
    "Card",
    "Column",
    "ColumnOption",
    "ConditionField",
    "DataColumns",
    "DataFilter",
    "DataFilterCondition",
    "DataRow",
    "DataTable",
    "Field",
    "Grid",
    "Header",
    "Icon",
    "Input",
    "Nav",
    "PageState",
    "Pills",
    "Row",
    "SearchState",
    "Select",
    "SortState",
    "Stepper",
    "Switch",
    "Textarea",
    # model field rendering
    "render_column",
    "column_validators",
]
