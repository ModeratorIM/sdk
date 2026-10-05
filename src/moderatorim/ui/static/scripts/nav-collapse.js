// ModeratorIM nav-rail collapse switcher. Toggles the mini (icon-only) rail by adding Beer CSS's
// own `small` class to nav.left, and persists the choice in localStorage.
//
// Swap-safe, exactly like theme-toggle.js: the authenticated shell swaps the whole <body> via
// htmx on navigation, which destroys the toggle button + listener AND resets the rail class. So
// (1) the click is DELEGATED on document (survives swaps), and (2) the saved state is RE-APPLIED
// after every htmx swap and on load. NEVER a one-shot DOMContentLoaded bind.
(function () {
  "use strict";
  var KEY = "mim-nav-collapsed";

  function collapsed() {
    return localStorage.getItem(KEY) === "1";
  }

  function apply(isCollapsed) {
    var rail = document.querySelector(".mim-nav-rail");
    if (rail) rail.classList.toggle("small", isCollapsed);
    var icon = document.querySelector("[data-mim-nav-icon]");
    // chevron points the way it will move the rail
    if (icon) icon.textContent = isCollapsed ? "chevron_right" : "chevron_left";
  }

  // Delegated toggle: works no matter when the button entered the DOM.
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    // Mini collapse/expand (desktop rail).
    if (t.closest("[data-mim-nav-toggle]")) {
      var next = !collapsed();
      localStorage.setItem(KEY, next ? "1" : "0");
      apply(next);
      return;
    }
    // Mobile drawer: open button.
    if (t.closest("[data-mim-nav-open]")) {
      document.body.classList.add("mim-nav-drawer-open");
      return;
    }
    // Account menu: toggle Beer CSS's `.active` on the nested <menu> (opens/closes it).
    var acctBtn = t.closest("[data-mim-account-toggle]");
    if (acctBtn) {
      var block = acctBtn.closest(".mim-account-block");
      var menu = block ? block.querySelector(".mim-account-menu") : null;
      if (menu) {
        var willOpen = !menu.classList.contains("active");
        menu.classList.toggle("active", willOpen);
        acctBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      }
      return;
    }
    // Click outside an open account menu closes it (a click on a menu item falls through so the
    // navigation still happens; the swap handler below closes it afterwards).
    if (!t.closest(".mim-account-menu")) {
      var openMenu = document.querySelector(".mim-account-menu.active");
      if (openMenu) {
        openMenu.classList.remove("active");
        var ob = openMenu.closest("[data-mim-account-toggle]");
        if (ob) ob.setAttribute("aria-expanded", "false");
      }
    }
    // Language switcher: toggle `.active` on the sibling <menu> (same anchored-popup idiom as the
    // account menu). The trigger + menu share a `.mim-lang-switcher` wrapper.
    var langBtn = t.closest("[data-mim-lang-toggle]");
    if (langBtn) {
      var wrap = langBtn.closest(".mim-lang-switcher");
      var lmenu = wrap ? wrap.querySelector(".mim-lang-menu") : null;
      if (lmenu) {
        var langOpen = !lmenu.classList.contains("active");
        lmenu.classList.toggle("active", langOpen);
        langBtn.setAttribute("aria-expanded", langOpen ? "true" : "false");
      }
      return;
    }
    // Click outside an open language menu closes it (a row click falls through so the POST fires).
    if (!t.closest(".mim-lang-menu")) {
      var openLang = document.querySelector(".mim-lang-menu.active");
      if (openLang) {
        openLang.classList.remove("active");
        var lb = openLang.closest(".mim-lang-switcher");
        var lt = lb ? lb.querySelector("[data-mim-lang-toggle]") : null;
        if (lt) lt.setAttribute("aria-expanded", "false");
      }
    }
    // Mobile drawer: close on scrim tap, or after tapping a nav link inside the drawer.
    if (t.closest("[data-mim-nav-scrim]") || t.closest(".mim-nav-item")) {
      document.body.classList.remove("mim-nav-drawer-open");
    }
  });

  // Re-apply after every htmx swap (navigation replaces the body) and once on load.
  function reapply() {
    apply(collapsed());
  }
  document.addEventListener("htmx:afterSettle", reapply);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", reapply);
  } else {
    reapply();
  }
})();
