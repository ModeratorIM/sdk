"""``DataRowActions`` — the per-row action control for a ``DataTable`` (ui-view-components).

A ``more_vert`` icon button opens a **Beer CSS popup menu** (the same trigger+``<menu>`` pattern as
:class:`~moderatorim.ui.DataColumns`) holding the row's actions — **Edit** (hx-GET the record form)
and **Delete**. Delete does NOT fire immediately: it opens a **confirmation modal** (a Beer
``<dialog class="modal">``) whose confirm button carries the ``hx-delete``, so a destructive action
always requires a second, explicit click.

The menu and the modal are toggled by the swap-safe delegated handler in ``datatable-filter.js``
(``data-mim-rowmenu-toggle`` opens the menu; ``data-mim-modal-open`` / ``data-mim-modal-close``
drive the dialog) — one-shot listeners would die on an htmx region swap.

Pure presentation (the ``Component`` contract): it receives the record id + gate booleans and emits
HTML; it does not query or know the store. The caller (the ListView renderer, or any app) decides
``can_update`` / ``can_delete`` and supplies the record ``label`` for the confirm copy.
"""

from __future__ import annotations

from moderatorim.ui.component import Component
from moderatorim.ui.html import Raw, esc, tag

_DEFAULT_REGION = "mim-list-region"


class DataRowActions(Component):
    """A ``more_vert`` trigger + a Beer popup menu of row actions (Edit / Delete), with a
    per-row delete-confirmation modal. Renders nothing when neither action is permitted."""

    def __init__(
        self,
        record_id: str,
        *,
        base_path: str = "",
        region_id: str = _DEFAULT_REGION,
        can_update: bool = False,
        can_delete: bool = False,
        label: str = "",
    ) -> None:
        self.record_id = record_id
        self.base_path = base_path
        self.region_id = region_id
        self.can_update = can_update
        self.can_delete = can_delete
        self.label = label

    def render(self) -> Raw:
        rid = self.record_id
        if not rid or not (self.can_update or self.can_delete):
            return Raw("")

        menu_items: list[object] = []
        if self.can_update:
            menu_items.append(
                tag(
                    "a",
                    tag("i", "edit"),
                    tag("span", "Edit"),
                    **{
                        "hx-get": f"{self.base_path}/{rid}",
                        "hx-target": "body",
                        "class": "mim-rowmenu-item",
                    },
                )
            )

        modal: object = ""
        if self.can_delete:
            modal_id = f"mim-delete-{rid}"
            # Delete menu item just OPENS the confirm modal (no hx-delete here).
            menu_items.append(
                tag(
                    "button",
                    tag("i", "delete"),
                    tag("span", "Delete"),
                    **{
                        "type": "button",
                        "class": "mim-rowmenu-item mim-rowmenu-danger",
                        "data-mim-modal-open": modal_id,
                    },
                )
            )
            what = esc(self.label) if self.label else "this record"
            modal = tag(
                "dialog",
                tag("h6", "Delete confirmation"),
                tag("p", Raw(f"Delete <strong>{what}</strong>? This cannot be undone.")),
                tag(
                    "nav",
                    tag(
                        "button",
                        "Cancel",
                        **{
                            "type": "button",
                            "class": "button border",
                            "data-mim-modal-close": modal_id,
                        },
                    ),
                    tag(
                        "button",
                        "Delete",
                        **{
                            "type": "button",
                            "class": "button error",
                            "hx-delete": f"{self.base_path}/{rid}",
                            "hx-target": "body",
                            # close the dialog once the request is sent
                            "data-mim-modal-close": modal_id,
                        },
                    ),
                    **{"class": "right-align mim-modal-actions"},
                ),
                **{"id": modal_id, "class": "modal mim-delete-modal"},
            )

        trigger = tag(
            "button",
            tag("i", "more_vert"),
            **{
                "type": "button",
                "class": "button transparent circle mim-rowmenu-toggle",
                "title": "Actions",
                "data-mim-rowmenu-toggle": "true",
            },
        )
        menu = tag("div", *menu_items, **{"class": "mim-rowmenu-menu"})
        return tag("div", trigger, menu, modal, **{"class": "mim-rowmenu"})
