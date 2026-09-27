"""``DataTable`` — a Beer CSS data-table COMPOSITE (ui-view-components spec).

Beer CSS gives you a styled ``<table>`` (the primitive); this composite adds the *datatable*
behavior on top: sortable headers, a realtime search box, a **multi-field** filter builder
(add N field+operator+value conditions, AND-combined by the query engine), a column-visibility
editor, a pagination footer and per-row actions — all wired for an htmx region swap.

**Pure presentation.** It receives already-resolved data + state (rows, columns, sort/search/filter
state) and renders HTML; it does NOT query, know the store, or resolve REF labels — the caller
(the ListView renderer, or any app) does that and hands over the results. This is what makes it
reusable: any screen that produces ``Column``/``DataRow`` data gets the same dynamic table.

Follows the ``Component`` contract (``render() -> Raw``, composes via ``tag``, imports only
``component`` + ``html``). The dynamic add/remove of filter-condition rows is driven by
``datatable-filter.js`` (registered in ``assets``); the server reads the ``f_<field>_<op>=value``
params the query engine already understands, so the filter is genuinely multi-field.
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

    ``kind`` drives cell rendering: ``"text"`` (default, escaped), ``"bool"`` (a status pill),
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
class FilterField:
    """One filter-able field offered in the builder: its key, header label, and the operator
    tokens valid for its type (e.g. ``("eq", "contains")``)."""

    key: str
    label: str
    ops: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class FilterState:
    """Multi-field filter builder state. ``fields`` are the pickable columns (each with its own
    operator set); ``active`` are the conditions currently applied, as ``(field, op, value)``
    triples, so they re-render on a region swap. Rendered only when ``fields`` is non-empty."""

    fields: tuple[FilterField, ...] = ()
    active: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True, kw_only=True)
class PageState:
    """Pagination: 1-based ``page`` of ``pages`` total, ``total`` record count."""

    page: int = 1
    pages: int = 1
    total: int = 0


class DataTable(Component):
    """A Beer CSS data table with sort, realtime search, a multi-field filter, column editor,
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
        filters: FilterState | None = None,
        columns_editor: Component | Raw | str = "",
        pagination: PageState | None = None,
        row_href: bool = False,
        row_actions: Sequence[tuple[str, Component | Raw | str]] = (),
        toolbar_extra: Sequence[Component | Raw | str] = (),
        empty_label: str = "No records yet.",
    ) -> None:
        self.columns = tuple(columns)
        self.rows = tuple(rows)
        self.base_path = base_path
        self.region_id = region_id
        self.sort = sort
        self.search = search
        self.filters = filters
        self.columns_editor = columns_editor
        self.pagination = pagination
        self.row_href = row_href
        # row_actions: (id, rendered-cell) pairs would be per-row; instead the caller passes a
        # callback via a custom Column, or we render an actions column when actions_for is given.
        self.row_actions = tuple(row_actions)
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
                tag(
                    "td",
                    self._cell_value(col, row),
                    **{"data-label": col.header},
                )
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
                attrs = {
                    "hx-get": row.href,
                    "hx-target": "body",
                    "class": "mim-list-row",
                }
            body_rows.append(tag("tr", *cells, **attrs))
        return tag("tbody", *body_rows)

    # ---- toolbar -----------------------------------------------------------
    def _search_box(self) -> Any:
        return tag(
            "input",
            **{
                "type": "search",
                "name": "q",
                "id": "mim-list-search",
                "value": self.search.term if self.search else "",
                "placeholder": "Search…",
                "hx-get": self.base_path,
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "hx-trigger": "input changed delay:300ms",
                # Lives inside the region it swaps (outerHTML), so hx-preserve keeps THIS element
                # across the swap — otherwise the input is destroyed each keystroke, losing focus.
                "hx-preserve": "true",
                "class": "mim-list-search",
            },
        )

    def _filter_builder(self) -> Any:
        """A MULTI-FIELD filter: a form whose rows each pick a field, an operator and a value; a
        + button clones a row (datatable-filter.js), Apply hx-GETs the region with every
        ``f_<field>_<op>=value`` param. The field/op catalogue rides in a data attribute so the JS
        can populate the operator select when the field changes."""
        f = self.filters
        assert f is not None

        # catalogue: field key → (label, ops[]) — consumed by the JS to build rows.
        cat_opts = [tag("option", ff.label, value=ff.key) for ff in f.fields]
        ops_by_field = ";".join(f"{ff.key}:{','.join(ff.ops)}" for ff in f.fields)

        # pre-render the active conditions so they survive a region swap.
        active_rows: list[Any] = []
        for fld, op, val in f.active:
            active_rows.append(self._condition_row(f, selected=(fld, op, val)))
        if not active_rows:
            active_rows.append(self._condition_row(f))

        body = tag(
            "div",
            tag("div", *active_rows, **{"class": "mim-filter-rows"}),
            tag(
                "div",
                tag(
                    "button",
                    tag("i", "add"),
                    " Add condition",
                    **{"type": "button", "class": "button border small mim-filter-add"},
                ),
                tag(
                    "button",
                    "Apply",
                    **{"type": "submit", "class": "button small mim-filter-apply"},
                ),
                **{"class": "mim-filter-controls"},
            ),
            **{
                "class": "mim-filter-builder",
                "data-region": self.region_id,
                "data-ops": ops_by_field,
            },
        )
        form = tag(
            "form",
            body,
            **{
                "hx-get": self.base_path,
                "hx-target": f"#{self.region_id}",
                "hx-swap": "outerHTML",
                "class": "mim-filter-form",
            },
        )
        # a hidden template row for the JS to clone (field select with all options).
        template = tag(
            "template",
            self._condition_row(f),
            **{"class": "mim-filter-template"},
        )
        return tag(
            "details",
            tag("summary", "Filters", **{"class": "button border small mim-filter-toggle"}),
            form,
            template,
            tag("div", *cat_opts, **{"hidden": "hidden", "class": "mim-filter-fieldopts"}),
            **{"class": "mim-list-filters"},
        )

    def _condition_row(self, f: FilterState, selected: tuple[str, str, str] | None = None) -> Any:
        """One field+op+value condition. Names are ``f_<field>_<op>`` — but since field/op are
        chosen client-side, the JS rewrites the value input's ``name`` to the composed token on
        change/submit; the pre-rendered active rows already carry the composed name so a swap
        re-applies them without JS."""
        sel_field, sel_op, sel_val = selected or ("", "", "")
        field_opts = [
            tag(
                "option",
                ff.label,
                **(
                    {"value": ff.key, "selected": "selected"}
                    if ff.key == sel_field
                    else {"value": ff.key}
                ),
            )
            for ff in f.fields
        ]
        # operator options: for a pre-selected field, that field's ops; else the first field's.
        current = next(
            (ff for ff in f.fields if ff.key == sel_field), f.fields[0] if f.fields else None
        )
        op_opts = []
        if current:
            for op in current.ops:
                op_opts.append(
                    tag(
                        "option",
                        op,
                        **(
                            {"value": op, "selected": "selected"} if op == sel_op else {"value": op}
                        ),
                    )
                )
        value_name = f"f_{sel_field}_{sel_op}" if sel_field and sel_op else ""
        return tag(
            "div",
            tag("select", *field_opts, **{"class": "mim-filter-field"}),
            tag("select", *op_opts, **{"class": "mim-filter-op"}),
            tag(
                "input",
                **{
                    "type": "text",
                    "class": "mim-filter-value",
                    "value": sel_val,
                    **({"name": value_name} if value_name else {}),
                },
            ),
            tag(
                "button",
                tag("i", "close"),
                **{"type": "button", "class": "button transparent circle small mim-filter-remove"},
            ),
            **{"class": "mim-filter-row"},
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
        toolbar: list[Any] = []
        if self.search is not None:
            toolbar.append(self._search_box())
        if self.filters is not None and self.filters.fields:
            toolbar.append(self._filter_builder())
        if self.columns_editor:
            toolbar.append(self.columns_editor)
        toolbar.extend(self.toolbar_extra)

        if not self.rows:
            table_or_empty: Any = tag("p", self.empty_label, **{"class": "mim-list-empty"})
        else:
            table_or_empty = tag(
                "table",
                self._header(),
                self._body(),
                **{"class": "border stripes mim-list-table"},
            )

        return tag(
            "div",
            tag("div", *toolbar, **{"class": "mim-list-toolbar"}),
            table_or_empty,
            self._footer(),
            **{"class": "mim-list", "id": self.region_id},
        )
