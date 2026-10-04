"""Declarative view descriptors — the app-facing API for model-driven views (Stage 1).

An app declares a page as a :class:`PageView` (a model + a root view) and maps paths to PageViews in
its ``routes.py`` via :class:`ViewRoute` (path + PageView + role gate). These are PURE DATA — no
rendering, no store access. Core reads them to generate List/Form/Calendar screens, gate them via
RBAC, and compose search/filter/sort/paginate into one ``ctx.store`` query.

Stage 1 ships :class:`Field` + :class:`ListView`; Form/Calendar descriptors arrive in later stages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from moderatorim.sdk.models.field import TableColumn


@dataclass(frozen=True, slots=True)
class Field:
    """A view's reference to one of the model's columns, plus view-only options.

    This is NOT a storage column (that is ``TableColumn``, which owns the ``FieldType``). A
    ``Field`` only NAMES a column and carries how the VIEW treats it:

    * ``name`` — the model column name it renders.
    * ``order`` — sort key for field placement (ascending; lower first).
    * ``roles`` — field-level visibility gate (L3): shown only to a caller holding one of these
      roles (empty = visible to all who can see the page). Enforced at render via ``ctx.has_role``.
    * ``span`` — how many form columns this field spans in a ``FormFields`` block (Stage 2).
    * ``display_field`` — for a REF column, the target column to show as its label; defaults to the
      target's ``display=True`` column (convention).
    * ``help`` — helper/placeholder text; falls back to the column's own label.
    * ``read_only`` — VIEW-level lock: render this field non-editable even in a form's edit mode
      (e.g. a profile's ``email``, which is the login identity and changes via a separate verified
      flow). Independent of the column's own ``read_only``; composes by OR.
    * ``custom`` — ESCAPE HATCH (design §7.3): a ``(record) -> cell content`` callback that renders
      a computed / non-field List cell (a status badge, a derived value, an action button like
      admin's super-user toggle). RETURN A UI PRIMITIVE (``tag(...)`` / ``Raw(...)``) — a plain
      string is escaped as safe text (XSS-safe default), so HTML must be a ``Raw``/tag. When set,
      ``name`` is a synthetic COLUMN KEY + header label, no backing model column is required, and
      the cell is neither sortable nor filterable. List-only.
    """

    name: str
    order: int = 100
    roles: tuple[str, ...] = ()
    span: int = 1
    display_field: str = ""
    help: str = ""
    read_only: bool = False
    custom: Callable[[dict[str, Any]], Any] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Field.name must be a non-empty column name")
        if self.span < 1:
            raise ValueError("Field.span must be >= 1")

    @property
    def is_custom(self) -> bool:
        """True when this field renders via a ``custom`` callback (no backing model column)."""
        return self.custom is not None


@dataclass(frozen=True, slots=True)
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
    """

    fields: tuple[Field, ...] = ()
    search: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    sort: tuple[str, str] | None = None
    enable_actions: bool = True
    # Multi-select set-editor mode (tabbed-form-subviews §7): when "multi", the list renders a
    # leading checkbox column (rows pre-checked by the caller's current set) so it can be used
    # inside a ModalView as a "pick the members" editor whose Save submits the checked keys. ""
    # (default) is an ordinary navigable list.
    select: str = ""
    # The column whose value is the checkbox's submitted key when select="multi" (defaults to the
    # display column). For roles' permission picker this is "permission".
    select_key: str = ""
    # multiselect: the ergonomic public flag — render a leading checkbox column in the list itself
    # (DataTable), so the ListView can be used as a set editor. Equivalent to select="multi"; either
    # turns the checkbox column on. The checkbox value comes from `select_key` (else the row id).
    multiselect: bool = False
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    @property
    def is_multiselect(self) -> bool:
        """True when the list should render its checkbox column (new flag OR legacy select)."""
        return self.multiselect or self.select == "multi"

    def __post_init__(self) -> None:
        if self.sort is not None and (len(self.sort) != 2 or self.sort[1] not in ("asc", "desc")):
            raise ValueError("ListView.sort must be (column, 'asc'|'desc')")

    @property
    def ordered_fields(self) -> tuple[Field, ...]:
        """Fields sorted by their declared ``order`` (stable)."""
        return tuple(sorted(self.fields, key=lambda f: f.order))


# --- Form view (Stage 2) -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FormFields:
    """A form child view: renders the record's OWN fields in a ``columns``-wide grid.

    Widget per field comes from the model column's ``FieldType`` (core owns the mapping). Fields
    auto-flow across ``columns`` by their ``order``; ``Field(span=k)`` widens one. ``columns``
    (default 1) collapses to 1 on mobile — it lives HERE, not on the tab or the FormView.
    """

    fields: tuple[Field, ...] = ()
    columns: int = 1
    order: int = 100

    def __post_init__(self) -> None:
        if self.columns < 1:
            raise ValueError("FormFields.columns must be >= 1")


@dataclass(frozen=True, slots=True)
class FormOverview:
    """A form child view: the record header (display-name + status). Empty on the create form."""

    order: int = 100


@dataclass(frozen=True, slots=True)
class FormList:
    """A form child view: an embedded list of a RELATED model inside a tab (tabbed-form-subviews
    §2). Unlike ``FormFields`` (which renders the record's own columns), a ``FormList`` renders rows
    of ``model`` via ``view`` — e.g. a role's granted permissions (``core_role_permission``) shown
    inside the role form's Permissions tab.

    ``link`` is the REF column ON ``model`` that points back at the PARENT form's table; core scopes
    the list to ``{link} = {parent record_id}``. Leave it ``""`` to AUTO-DETECT (the single REF on
    ``model`` whose ``relation`` is the parent table); name it explicitly only when ``model`` has
    more than one REF to the parent. The link is a reverse-REF relation — a related tab therefore
    requires a saved parent record (it cannot scope on create).

    ``id`` is this view object's identity (ARCHITECTURE D5). When set, the engine renders it as the
    element id and uses it as the htmx refresh target (``hx-target="#{id}"``); when empty it
    defaults to the enclosing tab panel's id, so an Add/Remove action re-renders just this list,
    not the whole form. (``region_id`` is the DEPRECATED former name of this field — still accepted
    for one release, mapped to ``id`` with a warning.)
    """

    model: Any  # the related ViewModel / TableModel whose rows are listed
    view: ListView  # how to render the rows
    link: str = ""  # the REF column on `model` -> parent table; "" = auto-detect the single REF
    order: int = 100
    id: str = ""  # explicit htmx refresh target id; defaults to the tab panel id (D5)
    region_id: str = ""  # DEPRECATED alias of `id`; mapped in __post_init__ (remove next release)

    def __post_init__(self) -> None:
        if self.model is None:
            raise ValueError("FormList.model is required")
        if self.view is None:
            raise ValueError("FormList.view is required")
        if self.region_id:
            if self.id:
                raise ValueError(
                    "FormList: pass only one of `id` / `region_id` (region_id is deprecated)"
                )
            import warnings

            object.__setattr__(self, "id", self.region_id)
            warnings.warn(
                "FormList.region_id is deprecated; use `id`.", DeprecationWarning, stacklevel=3
            )


@dataclass(frozen=True, slots=True)
class ListCardField:
    """One labelled fact shown inside a :class:`ListCard` row-card.

    * ``label`` — the human caption (e.g. "Device", "Last seen").
    * ``value`` — the model column name whose per-row value is shown.
    * ``format`` — an OPTIONAL core-owned formatter key applied to ``value`` before display:
      ``"datetime"`` renders a timestamp readably; ``"browser"`` summarizes a raw user-agent string
      into a short "Browser on OS" label and falls back to "Unknown device" when blank. ``""`` shows
      the value verbatim. A value-leaf — no ``id`` (D5: only element-rendering container views carry
      one; a field is content inside its card).
    """

    label: str
    value: str
    format: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("ListCardField.label is required")
        if not self.value:
            raise ValueError("ListCardField.value is required")


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class FormTab:
    """One tab of a :class:`FormView`. Holds an ordered list of child views (``views``).

    The lowest-``order`` tab (conventionally ``Detail``) is the default shown on load. ``roles``
    gates the tab's own visibility at render (layer 3, via ``ctx.has_role``) — a viewer lacking the
    role simply doesn't see the tab.
    """

    label: str
    views: tuple[object, ...] = ()  # FormFields / FormOverview / FormList (embedded list)
    order: int = 100
    roles: tuple[str, ...] = ()
    actions: tuple[FormAction, ...] = ()  # per-tab OVERFLOW (more_vert) actions
    # The set-editor opened by this tab's permission-driven Edit control (tabbed-form-subviews §7).
    # When set, the tab's Edit (shown if the viewer holds the resource's .update) opens this modal
    # instead of toggling the record into form-edit mode. A fields tab leaves this None (Edit =
    # form edit mode).
    editor: ModalView | None = None
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("FormTab.label is required")

    @property
    def ordered_views(self) -> tuple[object, ...]:
        return tuple(sorted(self.views, key=lambda v: getattr(v, "order", 100)))

    @property
    def ordered_actions(self) -> tuple[FormAction, ...]:
        return tuple(sorted(self.actions, key=lambda a: a.order))


@dataclass(frozen=True, slots=True)
class FormAction:
    """A declared button on a form, invoking ``handler`` (a ``@app.action``-style callable) — gated
    by ``roles`` at render (layer 3). E.g. the admin super-user toggle."""

    label: str
    handler: object  # a callable core binds to {path}/{id}/action/{name}
    roles: tuple[str, ...] = ()
    order: int = 100

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("FormAction.label is required")
        if self.handler is None:
            raise ValueError("FormAction.handler is required")


@dataclass(frozen=True, slots=True)
class StatusBadge:
    """A record-derived status chip rendered in a form header, beside the Edit button.

    PRESENTATION-ONLY and read-only: it reflects a column's value, it does not edit it. ``field``
    is the record column to read; ``mapping`` maps a (coerced-to-str) value to ``(text, variant)``
    where ``variant`` picks the themed colour. ``default`` applies when the value is missing or
    unmapped.

    Variants are theme tokens, NOT colours — core renders them as ``.mim-form-badge--<variant>`` and
    the CSS draws them from the theme's success/surface/… variables, so a badge re-themes with the
    app. Declared on :attr:`FormView.badges`.
    """

    label: str
    field: str
    mapping: dict[str, tuple[str, str]]  # value(str) -> (display_text, variant)
    default: tuple[str, str] = ("—", "neutral")
    order: int = 100

    _VARIANTS = frozenset({"success", "neutral", "warn", "danger"})

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("StatusBadge.label is required")
        if not self.field:
            raise ValueError("StatusBadge.field is required")
        for _text, variant in (*self.mapping.values(), self.default):
            if variant not in self._VARIANTS:
                raise ValueError(
                    f"StatusBadge variant {variant!r} invalid; one of {sorted(self._VARIANTS)}"
                )

    def resolve(self, record: dict[str, Any] | None) -> tuple[str, str]:
        """(text, variant) for ``record`` — the mapped pair, else ``default``."""
        value = "" if not record else record.get(self.field)
        key = "" if value is None else str(value)
        return self.mapping.get(key, self.default)


@runtime_checkable
class FormSave(Protocol):
    """Optional save delegate for a :class:`FormView` (declarative-views save seam). An app
    supplies one when a resource's create/update/delete must run domain logic instead of a generic
    ``ctx.store`` table write — e.g. roles reconcile ``core_role_permission`` grants and refuse
    system-row mutation through ``ctx.authz.define_role``/``delete_role``.

    All three methods are OPTIONAL; core calls whichever is defined and falls back to the generic
    store path for any the delegate omits. ``data`` is the validated+coerced field dict; ``ctx`` is
    the request context (carries ``ctx.authz``, ``ctx.store``, ``ctx.form()``).
    """

    async def create(self, ctx: Any, model: Any, data: dict[str, Any]) -> dict[str, Any]: ...

    async def update(
        self, ctx: Any, model: Any, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def delete(self, ctx: Any, model: Any, record_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class FormView:
    """A single root form view composed of :class:`FormTab`s (ordered) + declared ``actions``.

    New and Edit share one FormView — edit pre-fills from the resolved record; create renders empty
    (``ctx.is_new``). The first tab (lowest order) is the default.

    ``save`` is an OPTIONAL delegate (a :class:`FormSave`). When set, core routes the form's
    create/update/delete through it INSTEAD of the generic ``ctx.store`` write path — the seam for
    a resource whose mutations must run domain logic (e.g. roles reconcile grants + guard system
    rows via ``ctx.authz.define_role``, never a raw table write). When None (the default) the
    generic store path is used, unchanged.
    """

    tabs: tuple[FormTab, ...] = ()
    actions: tuple[FormAction, ...] = ()
    badges: tuple[StatusBadge, ...] = ()  # record-status chips beside Edit (presentation-only)
    save: FormSave | None = None
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)

    def __post_init__(self) -> None:
        if not self.tabs:
            raise ValueError("FormView requires at least one FormTab")

    @property
    def ordered_badges(self) -> tuple[StatusBadge, ...]:
        return tuple(sorted(self.badges, key=lambda b: b.order))

    @property
    def ordered_tabs(self) -> tuple[FormTab, ...]:
        return tuple(sorted(self.tabs, key=lambda t: t.order))

    @property
    def ordered_actions(self) -> tuple[FormAction, ...]:
        return tuple(sorted(self.actions, key=lambda a: a.order))

    @property
    def all_actions(self) -> tuple[FormAction, ...]:
        """The unified, ordered action list that defines the ``/action/{idx}`` index space:
        form-level actions first, then each tab's actions in tab order (tabbed-form-subviews §3).
        BOTH the route binding (``App.form_view``) and the core renderer walk THIS list, so a
        per-tab action button's index matches the route core bound for it.
        """
        out: list[FormAction] = list(self.ordered_actions)
        for tab in self.ordered_tabs:
            out.extend(tab.ordered_actions)
        return tuple(out)


@dataclass(frozen=True, slots=True)
class ModalAction:
    """A declared button in a :class:`ModalView`'s header. Like :class:`FormAction`, but its
    completion CLOSES the modal (and the opener refreshes its region). Used for the modal's Save in
    a set-editor (reconcile the checked set → close → refresh the tab panel that opened it).
    """

    label: str
    handler: object  # a callable core binds to the modal's action route
    roles: tuple[str, ...] = ()
    order: int = 100

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("ModalAction.label is required")
        if self.handler is None:
            raise ValueError("ModalAction.handler is required")


@dataclass(frozen=True, slots=True)
class ModalView:
    """A dialog container that renders an inner ``view`` in a ``<dialog class="modal">``
    (tabbed-form-subviews §7). Like :class:`FormView`/:class:`FormTab`, it is a pure CONTAINER — the
    inner view supplies the content, and ``actions`` (``ModalAction``s) are the modal's header
    controls (a modal action closes the dialog on completion). Opened by a permission-driven Edit
    control on the tab that declares it as its ``editor``.

    ``view`` is typically a :class:`ListView` with ``select="multi"`` (a set-editor), or a
    :class:`FormView` (edit a related record in a modal). ``label`` names the modal (trigger text /
    dialog title).
    """

    view: object
    label: str = ""
    actions: tuple[ModalAction, ...] = ()
    order: int = 100
    # Optional async resolver supplying the modal body's rows when the inner view is a select-mode
    # ListView (tabbed-form-subviews §7): ``rows(ctx, parent_id) -> list[dict]`` returns the
    # CANDIDATE rows, each with the view's ``select_key`` plus a truthy ``_checked`` for the ones
    # currently a member. Core renders the checkbox list from it (``/editor`` GET). The app owns
    # this because candidates + current membership are domain-specific (e.g. roles: the permission
    # catalog, checked = the role's grants). Reconcile on Save is the ModalAction's own handler.
    rows: object = None

    def __post_init__(self) -> None:
        if self.view is None:
            raise ValueError("ModalView.view is required")

    @property
    def ordered_actions(self) -> tuple[ModalAction, ...]:
        return tuple(sorted(self.actions, key=lambda a: a.order))


@dataclass(frozen=True, slots=True)
class ViewExtension:
    """A cross-app injection into another resource's Form (design §5b), keyed by the target form's
    base path (e.g. ``/shop/orders``). The extending app OWNS the injected tabs/actions — they are
    gated by their own ``roles`` (a FormTab's / FormAction's ``roles``), resolved at boot, merged
    into the target FormView's tabs/actions (by ``order``), and disappear when the app is
    uninstalled. Injection does NOT change page access — the target's own route gate still applies.
    """

    target: str  # the target form's base path
    add_tabs: tuple[FormTab, ...] = ()
    add_actions: tuple[FormAction, ...] = ()

    def __post_init__(self) -> None:
        if not self.target:
            raise ValueError("ViewExtension.target (the target form's base path) is required")


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


@dataclass(frozen=True, slots=True)
class ViewRoute:
    """One GENERATED model-driven route: a path bound to a :class:`PageView` (model + view); NO
    handler — core expands it into the query→store→render flow. Each expanded sub-route (list GET,
    create ``POST`` on the collection, ``/{id}`` GET/PATCH/DELETE) gates on its OWN single full
    permission, supplied by the expansion from the resource prefix — no verb is inferred at
    enforcement.

    Named ``ViewRoute`` (not ``Route``) so it never collides with the web framework's route type in
    core. Core resolves new-vs-edit from the path shape (``/x`` list, ``/x/new`` create, ``/x/{id}``
    edit) — see the routing framework.

    GATE — ``permission``: the SINGLE capability the LIST route requires, a full key (e.g.
    ``"admin.users.read"``). Leave it ``None`` (the norm) and the generated expansion supplies each
    op its own single permission from the resource prefix — list/detail GET → ``.read``, create →
    ``.create``, update → ``.update``, delete → ``.delete`` — so a viewer holding only ``.read`` can
    view records but is denied create/update/delete. Set ``permission`` only to OVERRIDE the list
    op's gate. ROLES are never declared here — they are granted at RUNTIME in RBAC data.
    """

    path: str
    view: PageView
    permission: Permission | str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("ViewRoute.path must be non-empty")


class PermissionAction(StrEnum):
    """The CRUD capability a :class:`Permission` grants — the ``{action}`` segment of a permission
    key. A ``StrEnum`` (Python 3.11+): each member compares and serializes AS its lowercase verb
    (``PermissionAction.READ == "read"``), so a :class:`Permission` renders straight to the string
    key core enforces.

    DISTINCT from :class:`RouteMethod` (the HTTP transport): a permission's action is a capability
    fact, not the wire verb. The two are not 1:1 — a ``GET`` create-form route needs
    ``PermissionAction.CREATE``, and create/update/delete arrive over ``POST``/``PATCH``/``DELETE``
    — so reusing the HTTP-method enum here would re-introduce the method→verb coupling the gate
    model deliberately removed. Keep them separate: ``RouteMethod`` is transport,
    ``PermissionAction`` is capability.
    """

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class Permission:
    """A structured permission key — the typed, model-driven replacement for a hand-written dotted
    string like ``"admin.users.create"``. Renders to that exact string via :meth:`__str__`, so it is
    type-safe at the authoring layer and a plain key at the enforcement seam (the same pattern as
    :class:`RouteMethod` passing straight to the framework).

    The key is ``{source}.{resource}.{action}``:

    * ``source`` — the declaring UNIT's name (its ``Manifest.name``): an app, backend, or platform
      alike (e.g. ``"admin"``, ``"moderation"``). This is the ``{X}`` namespace segment; it is
      DECLARED explicitly, never derived from the folder — a silently-derived prefix a developer
      forgets is the same foot-gun as a hidden table prefix.
    * ``resource`` — the thing acted on (e.g. ``"users"``).
    * ``action`` — the CRUD :class:`PermissionAction` (``READ``/``CREATE``/``UPDATE``/``DELETE``).

    A unit's full permission catalog generates itself instead of being hand-typed::

        _PERMISSIONS = tuple(
            Permission(source="admin", resource=r, action=a)
            for r in ("users", "roles", "groups")
            for a in PermissionAction
        )

    A :class:`Route` / :class:`ViewRoute` ``permission`` accepts a ``Permission`` or a bare ``str``;
    core normalizes with ``str()`` and compares the rendered key, so enforcement is unchanged.
    """

    source: str
    resource: str
    action: PermissionAction

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("Permission.source must be non-empty (the declaring unit's name)")
        if not self.resource:
            raise ValueError("Permission.resource must be non-empty")

    def __str__(self) -> str:
        return f"{self.source}.{self.resource}.{self.action}"


class RouteMethod(StrEnum):
    """The HTTP method a :class:`Route` serves. A ``StrEnum`` (Python 3.11+): each member compares
    and serializes AS its string (``RouteMethod.GET == "GET"``), so it passes straight to the
    framework boundary (Starlette ``methods=[route.method]``) with no conversion — type safety at
    the authoring layer, a plain string at the framework seam.

    ``GET`` = a page (returns a Page); ``POST`` / ``PATCH`` / ``DELETE`` = a mutation / re-render
    (returns Redirect | Rendered). The verb carries the operation on a RESTful resource: ``POST``
    creates on the collection, ``PATCH`` updates the record at ``/{id}``, ``DELETE`` removes it —
    no ``/delete`` path suffix. The app is htmx-driven, so the edit/delete controls issue these via
    ``hx-patch`` / ``hx-delete`` (an HTML ``<form>`` alone could only GET/POST)."""

    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True, slots=True)
class Route:
    """One CUSTOM route: a ``path`` served by a hand-written ``handler``, keyed by ``method``.
    GET returns a :class:`~moderatorim.sdk.Page`; POST / PATCH / DELETE return a
    :class:`~moderatorim.sdk.Redirect` / :class:`~moderatorim.sdk.Rendered`. Replaces the
    ``@app.page`` / ``@app.action`` / ``@app.post`` decorators and the old standalone
    ``PageRoute`` and the old ``RouteAction`` — one item object, method-driven, so a domain's
    ``routes.py`` is a uniform tuple of declarations.

    * ``path`` — the URL path (must be non-empty).
    * ``handler`` — an ``async (ctx) -> Page | Redirect | Rendered`` callable (required).
    * ``method`` — :class:`RouteMethod`. GET renders a page; POST/PATCH/DELETE perform a mutation /
      in-place re-render. One Route = one method.
    * ``title`` — GET pages only: the document ``<title>``.
    * ``nav`` — GET pages only: contribute a gate-aware left-rail nav entry (shown when the gate
      passes).
    * ``permission`` — the GATE.

    GATE — ``permission``: the SINGLE app/system-level capability this route REQUIRES, a full key
    (e.g. ``"admin.users.create"``). The caller passes when their RESOLVED permission set (derived
    from the roles granted to them) contains it. ``None`` ⇒ ungated (public, e.g. ``/signin``). One
    route requires one permission — to ACCESS a record you need ``.read`` (the GET page), and each
    mutating route names the one capability its action needs (``.create`` / ``.update`` /
    ``.delete``). The permission is a fact about the ROUTE, declared at code-time; ROLES (user-level
    bundles of permissions) are NOT declared here — they are granted at RUNTIME in RBAC data
    (users→groups→roles→permissions). A viewer holding only ``.read`` is denied create/update/delete
    because they don't hold those permissions. There is no method→verb inference — the required
    capability is always the explicit full ``permission``.
    """

    path: str
    handler: object  # async (ctx) -> Page | Redirect | Rendered
    method: RouteMethod = RouteMethod.GET
    title: str | None = None
    nav: str | None = None
    permission: Permission | str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("Route.path must be non-empty")
        if self.handler is None:
            raise ValueError("Route.handler is required")


@dataclass(frozen=True, slots=True)
class PageRoute:
    """A domain's ROUTE BUNDLE — the declarative replacement for ``app.mount(...)``. Groups the
    generated ``views`` (:class:`ViewRoute`) + custom ``routes`` (:class:`Route`) + the default
    resource ``permission`` prefix (+ an optional ``enrich`` hook for the views' lists). A domain's
    ``register()`` RETURNS one; core collects it and expands every item. Pure declaration — no
    ``app`` handle, no imperative call.

    * ``views`` — generated model-driven routes (:class:`ViewRoute`).
    * ``routes`` — custom hand-written routes (:class:`Route`).
    * ``permission`` — the default resource permission PREFIX for this bundle (documentation /
      grouping; e.g. ``"admin.roles"``). Not a gate itself — each route declares its own single
      ``permission``.
    * ``enrich`` — optional ``async (ctx, rows) -> None`` hook applied to the bundle's list views
      (attach per-row computed data before render).

    NOTE: this REPURPOSES the name ``PageRoute`` (was: a single custom GET page). Every old
    ``PageRoute(path=, handler=)`` is now a :class:`Route` ``(path=, handler=)``; ``PageRoute``
    graduates to the bundle.
    """

    views: tuple[ViewRoute, ...] = ()
    routes: tuple[Route, ...] = ()
    permission: str | None = None  # default resource prefix (documentation/grouping)
    enrich: object | None = None  # optional async (ctx, rows) -> None for views' lists


# --- Dashboard visuals (dashboard-visuals spec) ------------------------------------------------
# Server-rendered SVG widgets. Each widget BINDS to a table the same way PageView.model does: via a
# MetricSource/SeriesSource whose `model` names the table and `filters` (reusing Filter/FilterOp)
# restrict it. The engine resolves the aggregate through ctx.store (table-ACL enforced); no app
# query in the common case. (See specs/moderatorim/dashboard-visuals.)


@dataclass(frozen=True, slots=True)
class MetricSource:
    """WHAT table a single-number widget reads — the dashboard analogue of ``PageView.model`` + a
    view's filters. ``agg`` over ``model.name`` restricted by ``filters``; ``column`` is required
    for a non-count aggregate. Resolved by the engine via ``ctx.store`` (table-ACL enforced)."""

    model: object  # a ViewModel/TableModel (names the table), like PageView.model
    agg: str = "count"  # count | sum | avg | min | max
    column: str = ""  # required for non-count aggs
    filters: tuple[Any, ...] = ()  # tuple[Filter, ...] — the datastore filter grammar


@dataclass(frozen=True, slots=True)
class SeriesSource:
    """A chart's multi-point series: the same table binding plus a GROUP BY, so the engine returns
    ``[(group_label, value)]`` — one point per distinct ``group_by`` value (or date ``bucket``)."""

    model: object
    group_by: str  # column to group rows by (one bar per distinct value)
    agg: str = "count"
    column: str = ""
    filters: tuple[Any, ...] = ()
    bucket: str = ""  # optional date bucket for a date group_by: day | week | month


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class ScoreCard:
    """A single score on a bounded scale (default 0..``max``), rendered as a server-SVG gauge with
    threshold ``bands``. The moderation policy-score surface."""

    label: str
    source: MetricSource
    bands: tuple[ScoreBand, ...] = ()
    max: float = 100.0
    span: int = 3
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)


@dataclass(frozen=True, slots=True)
class BarChart:
    """A labelled vertical bar chart, server-rendered SVG, from a grouped ``SeriesSource``."""

    title: str
    source: SeriesSource
    span: int = 6
    height: int = 160  # px, SVG viewport height
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)


@dataclass(frozen=True, slots=True)
class DashboardView:
    """A dashboard = an ordered set of visual widgets (StatCard | ScoreCard | BarChart) laid out in
    the BeerCSS grid. Pure declaration; the renderer dispatches by widget class name."""

    widgets: tuple[object, ...] = ()
    id: str = ""  # view-object identity → DOM id / htmx target / CSS hook when set (D5)
