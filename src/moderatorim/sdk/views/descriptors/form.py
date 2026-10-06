"""Form view descriptors (FormView + tabs/fields/actions/modals + save protocol).

Split from the former single ``views/descriptors.py`` (SDK cleanup G3) — pure move, same public
symbols, re-exported from the package ``__init__``. Sibling references are type annotations only
(lazy via ``from __future__ import annotations``) under ``TYPE_CHECKING`` to avoid import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from moderatorim.sdk.views.descriptors.common import Field
    from moderatorim.sdk.views.descriptors.list_ import ListView


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
class FormHtml:
    """A form child view that renders BESPOKE pre-rendered HTML in a tab, supplied by the handler
    via ``subview_data[tab_index]`` (the same inline-data seam ``FormList`` uses).

    For a tab whose content the generic model-driven renderer cannot express — e.g. a key/value
    satellite editor (platform credentials) rather than the record's own columns. The handler
    renders the fragment and passes it in ``subview_data``; ``render_form`` places it. A
    ``FormHtml`` tab with no matching ``subview_data`` entry renders empty (not an error)."""

    order: int = 100
    id: str = ""  # DOM id / htmx target for the panel region (D5); defaults to the per-tab fallback


@dataclass(frozen=True, slots=True, kw_only=True)
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
    enrich: object = None  # optional async (ctx, rows) -> None: attach computed cells before render
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


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
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


@dataclass(frozen=True, slots=True, kw_only=True)
class ModalView:
    """A dialog container that renders an inner ``view`` in a ``<dialog class="modal">``
    (tabbed-form-subviews §7). Like :class:`FormView`/:class:`FormTab`, it is a pure CONTAINER — the
    inner view supplies the content, and ``actions`` (``ModalAction``s) are the modal's header
    controls (a modal action closes the dialog on completion). Opened by a permission-driven Edit
    control on the tab that declares it as its ``editor``.

    ``view`` is typically a :class:`ListView` with ``multiselect=True`` (a set-editor), or a
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


@dataclass(frozen=True, slots=True, kw_only=True)
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
