// ModeratorIM form-tab switcher for the generated Form view (ui-view-design). A tabbed form
// (cross-app extend_view adds tabs) renders a `.mim-form-tabs` nav of `.mim-form-tab[data-tab]`
// buttons + sibling `.mim-form-panel[data-panel]` panels; only the panel whose data-panel matches
// the active tab's data-tab is shown (CSS `.active`).
//
// Swap-safe, like nav-collapse.js/theme-toggle.js: the authenticated shell swaps the whole <body>
// via htmx, destroying any one-shot listener. So the click is DELEGATED on document and survives
// swaps. No DOMContentLoaded bind.
(function () {
  "use strict";
  document.addEventListener("click", function (evt) {
    var tab = evt.target.closest ? evt.target.closest(".mim-form-tab") : null;
    if (!tab) return;
    var key = tab.getAttribute("data-tab");
    if (!key) return;
    evt.preventDefault();
    var form = tab.closest(".mim-form");
    if (!form) return;
    // Activate the clicked tab, deactivate its siblings.
    var tabs = form.querySelectorAll(".mim-form-tab");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle("active", tabs[i] === tab);
    }
    // Show the matching panel, hide the rest.
    var panels = form.querySelectorAll(".mim-form-panel");
    for (var j = 0; j < panels.length; j++) {
      panels[j].classList.toggle("active", panels[j].getAttribute("data-panel") === key);
    }
  });
})();
