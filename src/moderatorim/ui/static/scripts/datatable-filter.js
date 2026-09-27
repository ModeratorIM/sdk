// ModeratorIM multi-field filter builder for the DataTable (ui-view-components). A
// `.mim-filter-builder` holds `.mim-filter-row`s, each a field <select>, an operator <select> and
// a value <input>; the query engine reads `f_<field>_<op>=value`, so on any change we recompose the
// value input's `name` to `f_<field>_<op>` and repopulate the operator select from the chosen
// field's allowed ops. "+ Add condition" clones the `<template class="mim-filter-template">` row;
// the ✕ removes its row. Apply is a normal htmx form GET — the composed names ride along.
//
// Swap-safe like form-tabs.js: everything is DELEGATED on document (the htmx region swap destroys
// one-shot listeners), and per-field operators come from the builder's `data-ops`
// ("field:op,op;field:op,op") so no per-row catalogue is needed.
(function () {
  "use strict";

  function opsFor(builder, fieldKey) {
    var spec = builder.getAttribute("data-ops") || "";
    var groups = spec.split(";");
    for (var i = 0; i < groups.length; i++) {
      var parts = groups[i].split(":");
      if (parts[0] === fieldKey) return parts[1] ? parts[1].split(",") : [];
    }
    return [];
  }

  function syncRow(row) {
    var builder = row.closest(".mim-filter-builder");
    if (!builder) return;
    var fieldSel = row.querySelector(".mim-filter-field");
    var opSel = row.querySelector(".mim-filter-op");
    var valInput = row.querySelector(".mim-filter-value");
    if (!fieldSel || !opSel || !valInput) return;
    var fieldKey = fieldSel.value;
    // Repopulate the operator select for this field, preserving the current choice if still valid.
    var want = opSel.value;
    var ops = opsFor(builder, fieldKey);
    opSel.innerHTML = "";
    for (var i = 0; i < ops.length; i++) {
      var o = document.createElement("option");
      o.value = ops[i];
      o.textContent = ops[i];
      if (ops[i] === want) o.selected = true;
      opSel.appendChild(o);
    }
    // Compose the value input's submit name so the server sees f_<field>_<op>=value.
    if (fieldKey && opSel.value) {
      valInput.name = "f_" + fieldKey + "_" + opSel.value;
    } else {
      valInput.removeAttribute("name");
    }
  }

  document.addEventListener("change", function (evt) {
    var t = evt.target;
    if (!t.closest) return;
    if (t.classList.contains("mim-filter-field") || t.classList.contains("mim-filter-op")) {
      var row = t.closest(".mim-filter-row");
      if (row) syncRow(row);
    }
  });

  document.addEventListener("click", function (evt) {
    if (!evt.target.closest) return;
    var add = evt.target.closest(".mim-filter-add");
    if (add) {
      evt.preventDefault();
      var details = add.closest(".mim-list-filters");
      var tpl = details && details.querySelector(".mim-filter-template");
      var rows = details && details.querySelector(".mim-filter-rows");
      if (tpl && rows && tpl.content) {
        var clone = tpl.content.firstElementChild.cloneNode(true);
        rows.appendChild(clone);
        syncRow(clone);
      }
      return;
    }
    var rm = evt.target.closest(".mim-filter-remove");
    if (rm) {
      evt.preventDefault();
      var r = rm.closest(".mim-filter-row");
      var container = r && r.parentNode;
      if (r && container && container.querySelectorAll(".mim-filter-row").length > 1) {
        r.remove();
      } else if (r) {
        // keep at least one row; just clear its value
        var v = r.querySelector(".mim-filter-value");
        if (v) v.value = "";
      }
    }
  });

  // On submit, make sure every row's name is composed (a row never changed still needs its name).
  document.addEventListener("submit", function (evt) {
    var form = evt.target;
    if (!form.classList || !form.classList.contains("mim-filter-form")) return;
    var rows = form.querySelectorAll(".mim-filter-row");
    for (var i = 0; i < rows.length; i++) syncRow(rows[i]);
  });
})();
