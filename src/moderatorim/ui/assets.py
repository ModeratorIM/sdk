"""Access to the BeerCSS/MDC/base assets shipped inside ``moderatorim.ui``.

The component library carries its own default design + behavior: the BeerCSS stylesheet + JS,
material-dynamic-colors, htmx, the component stylesheet ``ui.css``, and the JS that drives the
interactive components (``theme-toggle.js`` for ``ThemeToggle``, ``nav-collapse.js`` for
``NavRail``/``AccountMenu``). The brand/theme token sheets and core-chrome styles are a HOST
concern — the host serves them (as core's ``style.css`` + theme sheets) layered after these.
SERVING is a host job: a host locates the files via :func:`ui_asset_dir` (``importlib.resources``),
mounts them at a URL IT owns, and emits the ``<head>`` refs via :func:`ui_asset_tags` — so no
filename is hardcoded at the call site.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from moderatorim.ui.html import Raw, tag

# Stylesheets (order matters: BeerCSS framework first, then the component overrides). The brand/
# theme token sheets (theme-light/dark.css) are a HOST concern now — core serves them with its own
# chrome styles, layered after these.
STYLESHEETS: tuple[str, ...] = (
    "styles/beer.min.css",
    "styles/ui.css",
)

# Module scripts (BeerCSS + MDC are ES modules; component-behavior scripts are modules too).
MODULE_SCRIPTS: tuple[str, ...] = (
    "scripts/beer.min.js",
    "scripts/material-dynamic-colors.min.js",
    "scripts/theme-toggle.js",
    "scripts/nav-collapse.js",
    "scripts/form-tabs.js",
    "scripts/datatable-filter.js",
)

# Classic (non-module) scripts.
CLASSIC_SCRIPTS: tuple[str, ...] = ("scripts/htmx.min.js",)


def ui_asset_dir() -> Path:
    """Return the on-disk directory of the shipped ``moderatorim.ui`` assets.

    Resolved via ``importlib.resources`` so it works from an installed wheel, not just a source
    checkout. A host mounts this directory at a URL it owns (e.g. ``/static/ui``).
    """
    return Path(str(resources.files("moderatorim.ui") / "static"))


def ui_asset_tags(base_url: str = "/static/ui") -> Raw:
    """Emit the ``<link>``/``<script>`` tags for the shipped assets, rooted at ``base_url``.

    ``base_url`` is the URL the host mounted :func:`ui_asset_dir` at (no trailing slash). The host
    drops the returned markup into its document ``<head>`` — the component library's default look
    and behavior with no hardcoded filenames at the call site.
    """
    base = base_url.rstrip("/")
    parts: list[object] = [
        tag("link", href=f"{base}/{href}", rel="stylesheet") for href in STYLESHEETS
    ]
    parts += [tag("script", "", type="module", src=f"{base}/{src}") for src in MODULE_SCRIPTS]
    parts += [tag("script", "", src=f"{base}/{src}") for src in CLASSIC_SCRIPTS]
    return Raw("".join(str(p) for p in parts))
