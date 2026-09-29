"""Tests for DataRowActions: a more_vert popup menu of row actions + a delete-confirmation modal."""

from __future__ import annotations

from moderatorim.ui import DataRowActions


def _html(**kw: object) -> str:
    return str(DataRowActions("7", base_path="/admin/users", **kw).render())  # type: ignore[arg-type]


def test_more_vert_menu_with_edit_and_delete() -> None:
    html = _html(can_update=True, can_delete=True, label="Acme")
    # a more_vert trigger opening a popup menu (not inline buttons)
    assert "more_vert" in html
    assert 'data-mim-rowmenu-toggle="true"' in html
    assert "mim-rowmenu-menu" in html
    # Edit is an hx-GET to the record form (text-only, no icon)
    assert 'hx-get="/admin/users/7"' in html and ">Edit</a>" in html
    assert "<i>edit</i>" not in html  # icons dropped per design


def test_delete_opens_confirmation_modal_not_immediate() -> None:
    html = _html(can_update=True, can_delete=True, label="Acme")
    # the Delete menu item OPENS the modal; it does not carry the hx-delete itself
    assert 'data-mim-modal-open="mim-delete-7"' in html
    # the confirm modal is a Beer dialog; its confirm button carries the hx-delete
    assert 'class="modal mim-delete-modal"' in html
    assert 'id="mim-delete-7"' in html
    assert 'hx-delete="/admin/users/7"' in html
    # the record label appears in the confirm copy
    assert "Acme" in html


def test_update_only_has_no_delete_modal() -> None:
    html = _html(can_update=True, can_delete=False)
    assert ">Edit</a>" in html
    assert "mim-delete-modal" not in html and "hx-delete" not in html


def test_delete_only_has_no_edit() -> None:
    html = _html(can_update=False, can_delete=True)
    assert "mim-delete-modal" in html
    assert ">Edit</a>" not in html


def test_no_permissions_renders_nothing() -> None:
    assert _html(can_update=False, can_delete=False) == ""


def test_no_id_renders_nothing() -> None:
    assert str(DataRowActions("", base_path="/x", can_update=True, can_delete=True).render()) == ""


def test_label_is_escaped() -> None:
    html = _html(can_delete=True, label="<script>x</script>")
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html
