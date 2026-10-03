"""``DataTable`` — a Beer CSS data-table COMPOSITE (ui-view-components spec).

Beer CSS gives you a styled ``<table>`` (the primitive); this composite adds the *datatable*
behavior on top: sortable headers, a realtime search box, a pagination footer and per-row actions,
plus SLOTS for a filter control and a column-visibility control that the caller composes and passes
in (``DataFilter`` / ``DataColumns``) — components never import each other, so the renderer wires
them together.

**Pure presentation.** It receives already-resolved data + state (rows, columns, sort/search state,
pre-built control components) and renders HTML; it does NOT query, know the store, or resolve REF
labels — the caller (the ListView renderer, or any app) does that. This is what makes it reusable.

Follows the ``Component`` contract (``render() -> Raw``, composes via ``tag``, imports only
``component`` + ``html``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, tag

_DEFAULT_REGION = "mim-list-region"


@dataclass(frozen=True, kw_only=True)
class Column:
    """One table column. ``key`` is the row-dict key; ``label`` is the header text.

    ``kind`` drives cell rendering: ``"text"`` (default, escaped), ``"bool"`` (a check/close icon),
    ``"ref"`` (the caller pre-resolves the id→label in the DataRow cell). ``sortable`` renders the
    header as a sort link. ``custom`` is the escape hatch: a ``(row) -> cell content`` callback,
    invoked with the raw row dict; a custom column is neither sortable nor filterable.
    """

    key: str
    label: str = ""
    kind: str = "text"
    sortable: bool = True
    custom: Callable[[dict[str, Any]], Any] | None = None

    @property
    def header(self) -> str:
        return self.label or self.key.replace("_", " ").title()


@dataclass(frozen=True, kw_only=True)
class DataRow:
    """One table row. ``cells`` maps column-key → already-resolved display value (a REF cell holds
    the label, not the id). ``id`` identifies the record; ``href``, when set and the table is
    ``row_href``, makes the whole row hx-GET to it (open the edit form)."""

    id: str
    cells: dict[str, Any]
    href: str = ""


@dataclass(frozen=True, kw_only=True)
class SortState:
    """Active sort: the column key + direction. The header for ``key`` shows the arrow and its
    link toggles asc↔desc; other sortable headers link to ``asc``."""

    key: str = ""
    descending: bool = False


@dataclass(frozen=True, kw_only=True)
class SearchState:
    """Realtime search box state: the current ``term``. Rendered only when supplied."""

    term: str = ""


@dataclass(frozen=True, kw_only=True)
class PageState:
    """Pagination: 1-based ``page`` of ``pages`` total, ``total`` record count."""

    page: int = 1
    pages: int = 1
    total: int = 0


class DataTable(Component):
    """A Beer CSS data table with sort, realtime search, filter + columns control slots,
    pagination and row actions. See the module docstring for the presentation-only contract."""

    def __init__(
        self,
        *,
        columns: Sequence[Column],
        rows: Sequence[DataRow],
        base_path: str = "",
        region_id: str = _DEFAULT_REGION,
        sort: SortState | None = None,
        search: SearchState | None = None,
        filter_control: Component | Raw | str = "",
        columns_control: Component | Raw | str = "",
        pagination: PageState | None = None,
        row_href: bool = False,
        row_actions: Sequence[tuple[str, Component | Raw | str]] = (),
        actions: Sequence[Component | Raw | str] = (),
        toolbar_extra: Sequence[Component | Raw | str] = (),
        empty_label: str = "No records yet.",
    ) -> None:
        self.columns = tuple(columns)
        self.rows = tuple(rows)
        self.base_path = base_path
        self.region_id = region_id
        self.sort = sort
        self.search = search
        # filter_control / columns_control: pre-built DataFilter / DataColumns components, composed
        # by the caller (component isolation — DataTable never imports them). Either may be blank.
        self.filter_control = filter_control
        self.columns_control = columns_control
        self.pagination = pagination
        self.row_href = row_href
        self.row_actions = tuple(row_actions)
        # actions: list-level action buttons (bulk actions), right-aligned bar ABOVE the toolbar.
        self.actions = tuple(actions)
        self.toolbar_extra = tuple(toolbar_extra)
        self.empty_label = empty_label

    # ---- cells -------------------------------------------------------------
    def _cell_value(self, col: Column, row: DataRow) -> Any:
        if col.custom is not None:
            return col.custom(dict(row.cells, id=row.id))
        value = row.cells.get(col.key)
        if value is None or value == "":
            return ""
        if col.kind == "bool":
            on = bool(value) and value not in ("0", "false", "False")
            # A Material icon marks the boolean: a check when true, a muted close when false.
            return tag(
                "i",
                "check" if on else "close",
                **{
                    "class": "mim-cell-bool" + ("" if on else " mim-cell-bool-off"),
                    "title": "Yes" if on else "No",
                },
            )
        return str(value)

    # ---- header ------------------------------------------------------------
    def _sort_href(self, col: Column) -> str:
        active = self.sort and self.sort.key == col.key
        nxt = "desc" if (active and not self.sort.descending) else "asc"  # type: ignore[union-attr]
        return f"{self.base_path}?sort={col.key}:{nxt}"

    def _header(self) -> Raw:
        cells: list[Any] = []
        for col in self.columns:
            if col.sortable and col.custom is None and self.base_path:
                arrow = ""
                if self.sort and self.sort.key == col.key:
                    arrow = " ▼" if self.sort.descending else " ▲"
                cells.append(
                    tag(
                        "th",
                        tag(
                            "a",
                            col.header + arrow,
                            **{
                                "hx-get": self._sort_href(col),
                                "hx-target": f"#{self.region_id}",
                                "hx-swap": "outerHTML",
                            },
                        ),
                    )
                )
            else:
                cells.append(tag("th", col.header))
        if self.row_actions:
            cells.append(tag("th", "Actions"))
        return tag("thead", tag("tr", *cells))

    # ---- body --------------------------------------------------------------
    def _body(self) -> Raw:
        body_rows: list[Any] = []
        for row in self.rows:
            cells = [
                tag("td", self._cell_value(col, row), **{"data-label": col.header})
                for col in self.columns
            ]
            if self.row_actions:
                action_cells = [rendered for _id, rendered in self.row_actions]
                cells.append(
                    tag(
                        "td",
                        *action_cells,
                        **{"data-label": "Actions", "class": "mim-list-actions"},
                    )
                )
            attrs: dict[str, Any] = {}
            if self.row_href and row.href:
                # Row is click-to-edit, BUT a click inside the actions cell (the more_vert menu,
                # its items, or the delete-confirm modal) must NOT navigate. An htmx event filter
                # on the row's own trigger is the reliable guard: it runs on the <tr> handler
                # itself, so it suppresses navigation at the source regardless of event bubbling
                # (a delegated document-level stopPropagation fires too late — htmx is bound to the
                # <tr>, earlier in the bubble path).
                attrs = {
                    "hx-get": row.href,
                    "hx-target": "body",
                    "hx-trigger": "click[!event.target.closest('.mim-rowmenu')]",
                    "class": "mim-list-row",
                }
            body_rows.append(tag("tr", *cells, **attrs))
        return tag("tbody", *body_rows)

    # ---- toolbar -----------------------------------------------------------
    def _search_box(self) -> Any:
        # The search box id is PAGE-SPECIFIC (derived from region_id, which is the list region's
        # id) rather than a global "mim-list-search". hx-preserve below matches purely by id: with
        # a global id, navigating /users -> /roles (a full-body hx-swap) made htmx PRESERVE the old
        # /users search box into the /roles page — so it kept the stale value AND its hx-get=/users,
        # firing searches at the wrong resource until a hard refresh. A per-region id means the two
        # pages' search boxes have different ids, so there is nothing to preserve across the nav,
        # while within one page the region's own self-swap still preserves this element (keeps
        # focus/caret while typing). Falls back to the stable name="q" the handler reads either way.
        search_id = f"mim-list-search-{self.region_id}"
        return tag(
            "input",
            **{
                "type": "search",
                "name": "q",
                "id": search_id,
                "value": self.search.term if self.search else "",
                "placeholder": "Search…",
                "hx-get": self.base_path,
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "hx-trigger": "input changed delay:300ms",
                # Lives inside the region it swaps (outerHTML), so hx-preserve keeps THIS element
                # across the region's own self-swap — otherwise the input is destroyed each
                # keystroke, losing focus. The per-page id above stops it leaking across nav.
                "hx-preserve": "true",
                "class": "mim-list-search",
            },
        )

    def _footer(self) -> Any:
        p = self.pagination
        if p is None:
            return ""
        bits: list[Any] = [tag("span", f"{p.total} total · page {p.page}/{p.pages}")]
        if p.page > 1:
            bits.append(
                tag(
                    "a",
                    "‹ Prev",
                    **{
                        "hx-get": f"{self.base_path}?page={p.page - 1}",
                        "hx-target": f"#{self.region_id}",
                        "hx-swap": "outerHTML",
                        "class": "button small",
                    },
                )
            )
        if p.page < p.pages:
            bits.append(
                tag(
                    "a",
                    "Next ›",
                    **{
                        "hx-get": f"{self.base_path}?page={p.page + 1}",
                        "hx-target": f"#{self.region_id}",
                        "hx-swap": "outerHTML",
                        "class": "button small",
                    },
                )
            )
        return tag("div", *bits, **{"class": "mim-list-footer"})

    # ---- compose -----------------------------------------------------------
    def render(self) -> Raw:
        # Toolbar top row: search + the control icons (filter / columns) + any toolbar_extra.
        controls: list[Any] = []
        if self.search is not None:
            controls.append(self._search_box())
        if self.filter_control:
            controls.append(self.filter_control)
        if self.columns_control:
            controls.append(self.columns_control)
        controls.extend(self.toolbar_extra)

        if not self.rows:
            table_or_empty: Any = tag("p", self.empty_label, **{"class": "mim-list-empty"})
        else:
            table_or_empty = tag(
                "table",
                self._header(),
                self._body(),
                **{"class": "border stripes mim-list-table"},
            )

        parts: list[Any] = []
        # ListAction bar: list-level actions, right-aligned ABOVE the toolbar. Only when supplied.
        if self.actions:
            parts.append(tag("div", *self.actions, **{"class": "mim-list-actionbar"}))
        parts.append(tag("div", *controls, **{"class": "mim-list-toolbar"}))
        parts.append(table_or_empty)
        parts.append(self._footer())

        return tag("div", *parts, **{"class": "mim-list", "id": self.region_id})
