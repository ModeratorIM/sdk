"""List + card view descriptors (ListView, ListCard family).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from moderatorim.sdk.views.descriptors.common import Field


@dataclass(frozen=True, slots=True, kw_only=True)
class ListView:
    """A table generated from ``fields`` (ordered), with mandatory list affordances.

    * ``fields`` — the columns to show, ordered by each :class:`Field`'s ``order``.
    * ``search`` — column names the free-text search box matches (OR, case-insensitive). Empty = no
      search box.
    * ``filters`` — an OPTIONAL RESTRICTION on the runtime filter builder. The List view offers an
      "add filter" builder over the model's own columns; the operators for each come from the
      column's ``FieldType`` (core owns the type→operator mapping). Leave ``filters`` EMPTY to make
      every filterable column pickable (the default); provide a tuple to LIMIT the picker to those
      columns (e.g. hide sensitive columns from filtering). Non-filterable types (JSON/LIST/LISTREF)
      are auto-excluded regardless.
    * ``sort`` — the initial ``(column, "asc"|"desc")`` order, or None for the store default.
    * ``enable_actions`` — whether to render per-row Edit/Delete + the New button (default True).
      Set False for a READ-ONLY list that has no paired ``form_view`` (e.g. a catalog, or a list
      whose records are managed elsewhere) — otherwise a caller holding ``.update``/``.create``
      would see action controls linking to form routes that do not exist. A suppress-only VETO:
      permission (``ctx.can``) decides whether the CRUD buttons show; this only forces them off.
      Independent of permission gating.
    * ``new_href`` — an OPTIONAL custom path for the toolbar "New" button. When set, the New button
      navigates here (a full-page GET) instead of the generated ``{base}/new`` CRUD form — the
      entry point for a read-only catalog (``enable_actions=False``) whose "add" flow is a BESPOKE
      route, not the generated create form (e.g. the platform catalog's ``/platforms/new`` picker).
    * ``row_clickable`` — on a READ-ONLY list (``enable_actions=False``) rows are normally
      non-navigable, because the generated form routes they would open do not exist. Set this True
      when a read-only list DOES have a destination form at ``{base}/{id}`` (e.g. the platform
      catalog, whose rows open the per-platform FormView) so a row-click navigates there while
      Edit/Delete/New stay suppressed. Still honours read permission. Ignored on an actionable list
      (rows are already clickable) and never applies to a ``multiselect`` picker (row toggles its
      checkbox). ``False`` (default) keeps the read-only non-navigable behaviour.
    """

    fields: tuple[Field, ...] = ()
    search: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None
    enable_actions: bool = True
    new_href: str = ""
    row_clickable: bool = False
    # The column whose value is the checkbox's submitted key when `multiselect` is set (defaults
    # to the display column). For roles' permission picker this is "permission".
    select_key: str = ""
    # multiselect: render a leading checkbox column in the list itself (DataTable), so the ListView
    # can be used as a set editor inside a ModalView ("pick the members"), rows pre-checked by the
    # caller's current set and Save submitting the checked keys (tabbed-form-subviews §7). The
    # checkbox value comes from `select_key` (else the row id). False (default) is an ordinary
    # navigable list.
    multiselect: bool = False
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    def __post_init__(self) -> None:
        if self.sort is not None and (len(self.sort) != 2 or self.sort[1] not in ("asc", "desc")):
            raise ValueError("ListView.sort must be (column, 'asc'|'desc')")

    @property
    def ordered_fields(self) -> tuple[Field, ...]:
        """Fields sorted by their declared ``order`` (stable)."""
        return tuple(sorted(self.fields, key=lambda f: f.order))


@dataclass(frozen=True, slots=True, kw_only=True)
class GridView:
    """A ListView rendered as a grid of SELECTABLE cards (setup-wizard style) — same table-backed
    semantics as :class:`ListView`, different UI. The engine lists the ``PageView.model``'s rows and
    renders each as a radio-selectable card (``fields`` shown per card, ``search``/``sort`` as on a
    list). Selecting a card enables the view's ``actions`` (declarative :class:`FormAction`s shown
    in the content header); there is no navigate-on-click and no built-in Continue — the action is
    the control.

    * ``fields`` — the columns shown on each card, ordered by each :class:`Field`'s ``order``.
    * ``title_field`` — the field rendered as the card's bold heading (defaults to the model's
      display column when empty).
    * ``select_key`` — the column whose value a selected card submits (defaults to the row ``id``).
    * ``actions`` — the :class:`FormAction`s the selection enables (e.g. open the selected
      platform). Rendered in the header; disabled until a card is selected.
    * ``search`` — column names the client-side filter box matches (OR, case-insensitive).
    * ``sort`` — the initial ``(column, "asc"|"desc")`` order, or None for the store default.
    * ``empty_label`` — shown when the model lists no rows.
    """

    fields: tuple[Field, ...] = ()
    title_field: str = ""
    select_key: str = ""
    actions: tuple[Any, ...] = ()  # FormAction(s) enabled by a selection
    search: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None
    empty_label: str = "Nothing here yet."
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    def __post_init__(self) -> None:
        if self.sort is not None and (len(self.sort) != 2 or self.sort[1] not in ("asc", "desc")):
            raise ValueError("GridView.sort must be (column, 'asc'|'desc')")

    @property
    def ordered_fields(self) -> tuple[Field, ...]:
        """Fields sorted by their declared ``order`` (stable)."""
        return tuple(sorted(self.fields, key=lambda f: f.order))


# --- Form view (Stage 2) -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCardField:
    """One labelled fact shown inside a :class:`ListCard` row-card.

    * ``label`` — the human caption (e.g. "Device", "Last seen").
    * ``value`` — the model column name whose per-row value is shown.
    * ``format`` — an OPTIONAL core-owned formatter key applied to ``value`` before display:
      ``"datetime"`` renders a timestamp readably; ``"browser"`` summarizes a raw user-agent string
      into a short "Browser on OS" label and falls back to "Unknown device" when blank. ``""`` shows
      the value verbatim. A value-leaf — no ``id`` (D5: only element-rendering container views carry
      one; a field is content inside its card).
    * ``icon`` — an OPTIONAL Material Symbols glyph name (e.g. ``"lan"``, ``"devices"``) rendered as
      a leading icon before the value. ``""`` (default) renders no icon — the field shows its label
      and value only.
    """

    label: str
    value: str
    format: str = ""
    icon: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("ListCardField.label is required")
        if not self.value:
            raise ValueError("ListCardField.value is required")


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCardAction:
    """A per-card button on a :class:`ListCard` (e.g. Revoke). Unlike :class:`FormAction`, which
    binds a handler callable to a generated route, a ``ListCardAction`` POSTs directly to a FIXED,
    owner-declared route (``hx_post``) — the right shape when the owning unit (here core) already
    owns a concrete endpoint. ``{id}`` in ``hx_post`` is filled with the row's id at render.

    * ``label`` — the button text.
    * ``hx_post`` — the POST path template; ``{id}`` → the row id (e.g.
      ``/settings/sessions/{id}/revoke``).
    * ``roles`` — render-time gate (L3): the button is HIDDEN unless the caller holds one of these
      roles (empty = shown to anyone who can see the card).
    * ``confirm`` — optional confirmation prompt text; when set the action asks before firing.
    * ``variant`` — a visual intent key (e.g. ``"danger"`` for a destructive action like Revoke).
    A value-leaf — no ``id`` (D5).
    """

    label: str
    hx_post: str
    roles: tuple[str, ...] = ()
    confirm: str = ""
    variant: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("ListCardAction.label is required")
        if not self.hx_post:
            raise ValueError("ListCardAction.hx_post is required")


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCard:
    """A list rendered as ONE CARD PER ROW (not a table) — e.g. a user's active sessions. Each card
    shows its ``fields`` (label/value facts) and ``actions`` (per-card buttons); ``onclick`` makes
    the whole card navigate. The data model + binding mirror :class:`FormList`: ``model`` names the
    related table and ``link`` the REF back to the parent, so core scopes the cards to the parent
    record's rows, with optional extra ``filters``.

    ``id`` is this view object's identity (ARCHITECTURE D5): the engine renders it as the card
    container's DOM id and uses it as the htmx swap target, so a per-card action can re-render just
    this card list. It MUST be set DISTINCTLY when the same ``ListCard`` is mounted in two places
    (e.g. a self ``/settings`` tab and an admin user form) so one mount's swap can never
    cross-target the other. Empty → the enclosing tab panel's id.
    """

    model: Any  # the row table (e.g. the Session TableModel)
    fields: tuple[ListCardField, ...] = ()
    actions: tuple[ListCardAction, ...] = ()
    onclick: str = ""  # optional per-card nav path template (e.g. "/x/{id}"); "" = non-navigable
    link: str = ""  # REF column on `model` -> parent table; "" = auto-detect the single REF
    filters: tuple[Any, ...] = ()  # extra row filters (e.g. state == ACTIVE); core Filter grammar
    order: int = 100
    id: str = ""  # D5: card-list identity → DOM id + htmx swap target; "" = enclosing tab panel id
    empty_label: str = "Nothing here yet."

    def __post_init__(self) -> None:
        if self.model is None:
            raise ValueError("ListCard.model is required")
