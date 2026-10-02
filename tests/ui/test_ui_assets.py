"""Tests for the shipped ``moderatorim.ui`` assets and the host-facing accessors."""

from __future__ import annotations

from moderatorim.ui import ui_asset_dir, ui_asset_tags

# The library assets that MUST ship with the wheel (default design + behavior). The brand/theme
# token sheets moved to the host (core); the SDK ships the framework + the component stylesheet.
_EXPECTED_FILES = (
    "styles/beer.min.css",
    "styles/ui.css",
    "scripts/beer.min.js",
    "scripts/material-dynamic-colors.min.js",
    "scripts/htmx.min.js",
    "scripts/theme-toggle.js",
    "scripts/nav-collapse.js",
)


def test_shipped_asset_dir_has_the_library_files() -> None:
    root = ui_asset_dir()
    assert root.is_dir()
    for rel in _EXPECTED_FILES:
        assert (root / rel).is_file(), f"missing shipped asset: {rel}"


def test_asset_tags_reference_the_host_base_url() -> None:
    html = ui_asset_tags("/static/ui")
    # Stylesheet link + module/classic scripts rooted at the given base.
    assert '<link href="/static/ui/styles/beer.min.css" rel="stylesheet">' in html
    assert '<script type="module" src="/static/ui/scripts/beer.min.js"></script>' in html
    assert '<script src="/static/ui/scripts/htmx.min.js"></script>' in html


def test_asset_tags_base_url_trailing_slash_normalized() -> None:
    html = ui_asset_tags("/assets/")
    assert "/assets/styles/beer.min.css" in html
    assert "/assets//styles" not in html  # no double slash
