"""Composed view descriptors (ViewModel, PageView, CalendarView).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass

from moderatorim.sdk.models.field import TableColumn


@dataclass(frozen=True, slots=True)
class CalendarView:
    """A month calendar over a model (design §6). Renders records as events positioned by a
    DATE/DATETIME ``start_field``; ``title_field`` is the event label; optional ``end_field`` spans
    multi-day events. v1 = server-rendered month grid + prev/next navigation (``?month=YYYY-MM``);
    clicking an event opens the record's edit Form, an empty day opens the new Form with the date
    pre-filled. Fetches the month's records with a date-range filter under the hood.
    """

    start_field: str
    title_field: str
    end_field: str | None = None
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    def __post_init__(self) -> None:
        if not self.start_field:
            raise ValueError("CalendarView.start_field (the DATE/DATETIME field) is required")
        if not self.title_field:
            raise ValueError("CalendarView.title_field (the event label field) is required")


@dataclass(frozen=True, slots=True)
class ViewModel:
    """A READ-ONLY reference to a table a view reads — NOT a model declaration.

    A view often lists a table another unit OWNS (e.g. the admin app lists ``core_user``). The app
    must not declare a :class:`~moderatorim.sdk.TableModel` for it: that would MINT the table into
    ``manifest.models`` and the boot ownership guard forbids a non-owning unit declaring a foreign
    (``{other}_``) table. A ``ViewModel`` is a REFERENCE instead — the same "declare vs reference"
    line the guard already draws for ``permission=`` strings — carrying just the column metadata the
    view engine needs (name, type, label, relation, choices, display). It is never provisioned and
    never validated for ownership; it only describes columns the view renders/filters.

    Exposes the same read surface the engine uses on a ``TableModel`` (``name`` / ``column_map`` /
    ``display_label``), so it is a drop-in for :class:`PageView`'s ``model``.
    """

    name: str  # the physical table it reads (may be another unit's, e.g. "core_user")
    columns: tuple[TableColumn, ...] = ()
    label: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ViewModel.name (the table it reads) is required")

    @property
    def column_map(self) -> dict[str, TableColumn]:
        return {c.name: c for c in self.columns}

    @property
    def display_label(self) -> str:
        if self.label:
            return self.label
        tail = self.name.split("_", 1)[-1] if "_" in self.name else self.name
        return tail.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class PageView:
    """One page = one model + one root view (a :class:`ListView` / :class:`FormView` /
    :class:`CalendarView`). A :class:`DashboardView` is the exception: it binds its tables
    per-widget (each widget's ``source.model``), so ``model`` is omitted for one.

    Access ``roles`` live on the :class:`ViewRoute` binding, NOT here — the same PageView can be
    bound at several paths with different gates (list vs new vs edit)."""

    view: object  # a ListView / FormView / CalendarView / DashboardView
    model: object | None = None  # a TableModel; None only for a DashboardView (per-widget binding)

    def __post_init__(self) -> None:
        if self.view is None:
            raise ValueError("PageView.view is required")
        # A DashboardView carries its tables on each widget's source.model, so it needs no page
        # model; every other view type is bound to exactly one model.
        if self.model is None and type(self.view).__name__ != "DashboardView":
            raise ValueError("PageView.model is required (except for a DashboardView)")
