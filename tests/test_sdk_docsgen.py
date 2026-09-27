"""Tests for the module-first SDK API reference generator (``moderatorim.sdk_docsgen``).

The heavy rendering path needs the optional ``[docs]`` extra (griffe2md). CI's default ``[dev]``
env does not install it, so those tests skip cleanly when it is absent; the module-discovery,
slug and facet logic is tested unconditionally.
"""

from __future__ import annotations

import importlib.util

import pytest

from moderatorim import sdk_docsgen

_HAS_GRIFFE2MD = importlib.util.find_spec("griffe2md") is not None
needs_griffe2md = pytest.mark.skipif(
    not _HAS_GRIFFE2MD, reason="requires the [docs] extra (griffe2md)"
)


def test_sdk_modules_are_discovered_module_first() -> None:
    mods = sdk_docsgen.sdk_modules()
    assert "moderatorim.sdk.bus" in mods
    assert "moderatorim.sdk.models" in mods
    assert "moderatorim.sdk.web" in mods
    # UI is a separate facet, not mixed into the SDK modules.
    assert "moderatorim.ui" not in mods
    # The CLI is documented elsewhere (moderatorim.cli.docsgen), never here.
    assert "moderatorim.cli" not in mods
    # No private/underscore modules leak in.
    assert not any(m.rsplit(".", 1)[-1].startswith("_") for m in mods)


def test_ui_symbols_are_per_type() -> None:
    syms = sdk_docsgen.ui_symbols()
    # Components are documented individually.
    for expected in ("Alert", "Avatar", "Button", "Card"):
        assert expected in syms


def test_short_name_and_slug() -> None:
    assert sdk_docsgen._short_name("moderatorim.sdk.bus") == "bus"
    assert sdk_docsgen._short_name("moderatorim.ui") == "ui"
    assert sdk_docsgen._slug("moderatorim.sdk.datastore") == "datastore"


@needs_griffe2md
def test_render_page_titles_by_short_name() -> None:
    page = sdk_docsgen.render_page("moderatorim.sdk.bus")
    assert page.startswith("<!-- GENERATED")
    # The H1 title is the short name, NOT the dotted path. (Symbol sub-headings inside the
    # griffe2md body legitimately use dotted paths — only the page title is checked here.)
    h1 = next(line for line in page.splitlines() if line.startswith("# "))
    assert h1 == "# `bus`"
    assert "Action" in page  # a known public symbol from the module


@needs_griffe2md
def test_generate_sdk_facet_writes_short_named_pages_no_index(tmp_path) -> None:
    out = tmp_path / "sdk-ref"
    out.mkdir()
    orphan = out / "stale-module.md"
    orphan.write_text("old", encoding="utf-8")

    written = sdk_docsgen.generate(out, facet="sdk")

    assert not orphan.exists()  # fully rebuilt, no orphans
    names = {p.name for p in written}
    assert "bus.md" in names
    assert "models.md" in names
    # No index page, and UI is not in the SDK facet.
    assert "index.md" not in names
    assert "moderatorim-ui.md" not in names
    assert "ui.md" not in names


@needs_griffe2md
def test_generate_ui_facet_writes_one_page_per_symbol(tmp_path) -> None:
    written = sdk_docsgen.generate(tmp_path / "ui-ref", facet="ui")
    names = {p.name for p in written}
    # One page per public UI component/type.
    assert "Alert.md" in names
    assert "Avatar.md" in names
    assert "Button.md" in names
    # Not one monolithic ui.md page.
    assert "ui.md" not in names


@needs_griffe2md
def test_generated_output_has_no_leaks(tmp_path) -> None:
    written = sdk_docsgen.generate(tmp_path / "sdk-ref", facet="sdk")
    written += sdk_docsgen.generate(tmp_path / "ui-ref", facet="ui")
    blob = "\n".join(p.read_text(encoding="utf-8") for p in written).lower()
    for needle in (".kiro", "crew", "appwrite", "supabase", "firebase", "whatsapp", "telegram"):
        assert needle not in blob


def test_missing_griffe2md_raises_actionable_error(monkeypatch) -> None:
    """When griffe2md is absent, the error names the install command."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "griffe2md":
            raise ModuleNotFoundError("No module named 'griffe2md'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as exc:
        sdk_docsgen.render_page("moderatorim.sdk.bus")
    assert "griffe2md" in str(exc.value)
    assert "[docs]" in str(exc.value)
