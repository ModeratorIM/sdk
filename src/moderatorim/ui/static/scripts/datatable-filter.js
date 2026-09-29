// ModeratorIM filter builder for the DataTable (ui-view-components). Each `.mim-filter-row` is a
// ServiceNow-style [field ▾][operator ▾][typed value] row. CHANGING THE FIELD is an htmx round-trip
// (the field <select> carries hx-get; the server re-renders the row typed for the new field via
// render_column) — the JS does NOT rebuild inputs or operators. The query engine reads
// `f_<field>_<op>=value`, so on op-change / submit we compose the value control's submit `name` to
// `f_<field>_<op>`. The value control lives INSIDE `.mim-filter-value` (a wrapper the server emits
// around whatever render_column produced). "+ Add condition" clones the template row; ✕ removes.
//
// Swap-safe like form-tabs.js: everything is DELEGATED on document (an htmx swap destroys one-shot
// listeners).
(function () {
  "use strict";

  // The actual form control (input/select/textarea) inside a row's value wrapper.
  function valueControl(row) {
    var wrap = row.querySelector(".mim-filter-value");
    return wrap ? wrap.querySelector("input, select, textarea") : null;
  }

  // Compose the value control's submit name to f_<field>_<op> so the query engine sees it.
  function composeName(row) {
    var fieldSel = row.querySelector(".mim-filter-field");
    var opSel = row.querySelector(".mim-filter-op");
    var ctrl = valueControl(row);
    if (!fieldSel || !opSel || !ctrl) return;
    var field = fieldSel.value;
    var op = opSel.value;
    if (field && op) {
      ctrl.name = "f_" + field + "_" + op;
    } else {
      ctrl.removeAttribute("name");
    }
  }

  document.addEventListener("change", function (evt) {
    var t = evt.target;
    if (!t.closest) return;
    // Field change is handled by htmx (re-renders the row); we only recompose on OPERATOR change.
    if (t.classList.contains("mim-filter-op")) {
      var row = t.closest(".mim-filter-row");
      if (row) composeName(row);
    }
  });

  document.addEventListener("click", function (evt) {
    if (!evt.target.closest) return;
    // Filters panel toggle (button + separate full-width panel).
    var filtTrigger = evt.target.closest("[data-mim-filter-toggle]");
    if (filtTrigger) {
      evt.preventDefault();
      var filters = filtTrigger.closest(".mim-list-filters");
      var panel = filters && filters.querySelector(".mim-filter-panel");
      if (panel) panel.classList.toggle("active");
      return;
    }
    // Columns popup toggle.
    var colTrigger = evt.target.closest("[data-mim-columns-toggle]");
    if (colTrigger) {
      evt.preventDefault();
      var editor = colTrigger.closest(".mim-cols-editor");
      var menu = editor && editor.querySelector(".mim-cols-menu");
      if (menu) menu.classList.toggle("active");
      return;
    }
    // Row-actions (more_vert) popup toggle. Close any other open row menu first so only one is
    // open at a time.
    var rowTrigger = evt.target.closest("[data-mim-rowmenu-toggle]");
    if (rowTrigger) {
      evt.preventDefault();
      var wrap = rowTrigger.closest(".mim-rowmenu");
      var rmenu = wrap && wrap.querySelector(".mim-rowmenu-menu");
      var wasActive = rmenu && rmenu.classList.contains("active");
      document.querySelectorAll(".mim-rowmenu-menu.active").forEach(function (m) {
        m.classList.remove("active");
      });
      if (rmenu && !wasActive) rmenu.classList.add("active");
      return;
    }
    // Open a delete-confirmation modal (Beer <dialog class="modal">). The row menu closes.
    var modalOpen = evt.target.closest("[data-mim-modal-open]");
    if (modalOpen) {
      evt.preventDefault();
      var openId = modalOpen.getAttribute("data-mim-modal-open");
      var dlg = openId && document.getElementById(openId);
      document.querySelectorAll(".mim-rowmenu-menu.active").forEach(function (m) {
        m.classList.remove("active");
      });
      if (dlg && typeof dlg.showModal === "function") dlg.showModal();
      else if (dlg) dlg.setAttribute("open", "true");
      return;
    }
    // Close a modal (Cancel, or after the confirm button dispatches its hx-delete).
    var modalClose = evt.target.closest("[data-mim-modal-close]");
    if (modalClose) {
      var closeId = modalClose.getAttribute("data-mim-modal-close");
      var dlg2 = closeId && document.getElementById(closeId);
      if (dlg2 && typeof dlg2.close === "function") dlg2.close();
      else if (dlg2) dlg2.removeAttribute("open");
      // do NOT preventDefault on the confirm button — htmx still needs to fire its hx-delete.
      return;
    }
    // Add a condition: clone the template row.
    var add = evt.target.closest(".mim-filter-add");
    if (add) {
      evt.preventDefault();
      var box = add.closest(".mim-list-filters");
      var tpl = box && box.querySelector(".mim-filter-template");
      var rows = box && box.querySelector(".mim-filter-rows");
      if (tpl && rows && tpl.content) {
        var clone = tpl.content.firstElementChild.cloneNode(true);
        rows.appendChild(clone);
        // htmx must (re)process the clone so the field <select>'s hx-get is live.
        if (window.htmx && window.htmx.process) window.htmx.process(clone);
        composeName(clone);
      }
      return;
    }
    // Remove a condition row (keep at least one).
    var rm = evt.target.closest(".mim-filter-remove");
    if (rm) {
      evt.preventDefault();
      var r = rm.closest(".mim-filter-row");
      var container = r && r.parentNode;
      if (r && container && container.querySelectorAll(".mim-filter-row").length > 1) {
        r.remove();
      } else if (r) {
        var c = valueControl(r);
        if (c) c.value = "";
      }
    }
  });

  // On submit, compose every row's value name (a row never touched still needs its name).
  document.addEventListener("submit", function (evt) {
    var form = evt.target;
    if (!form.classList || !form.classList.contains("mim-filter-form")) return;
    var rows = form.querySelectorAll(".mim-filter-row");
    for (var i = 0; i < rows.length; i++) composeName(rows[i]);
  });
})();
