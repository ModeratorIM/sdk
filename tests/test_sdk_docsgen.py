"""Tests for the module-first SDK API reference generator (``moderatorim.sdk_docsgen``).

The heavy rendering path needs the optional ``[docs]`` extra (griffe2md). CI's default ``[dev]``
env does not install it, so those tests skip cleanly when it is absent; the module-discovery,
slug and index logic is tested unconditionally.
"""

from __future__ import annotations

import importlib.util

import pytest

from moderatorim import sdk_docsgen

_HAS_GRIFFE2MD = importlib.util.find_spec("griffe2md") is not None
needs_griffe2md = pytest.mark.skipif(
    not _HAS_GRIFFE2MD, reason="requires the [docs] extra (griffe2md)"
)


def test_public_modules_are_module_first_and_include_ui() -> None:
    mods = sdk_docsgen.public_modules()
    # Discovered SDK submodules (module-first), plus the UI facet.
    assert "moderatorim.sdk.bus" in mods
    assert "moderatorim.sdk.models" in mods
    assert "moderatorim.sdk.web" in mods
    assert "moderatorim.ui" in mods
    # The CLI is documented elsewhere (moderatorim.cli.docsgen), never here.
    assert "moderatorim.cli" not in mods
    # No private/underscore modules leak in.
    assert not any("._" in m or m.rsplit(".", 1)[-1].startswith("_") for m in mods)


def test_slug() -> None:
    assert sdk_docsgen._slug("moderatorim.sdk.bus") == "bus"
    assert sdk_docsgen._slug("moderatorim.sdk.datastore") == "datastore"
    assert sdk_docsgen._slug("moderatorim.ui") == "moderatorim-ui"


def test_index_records_version_and_links_each_module() -> None:
    mods = sdk_docsgen.public_modules()
    index = sdk_docsgen.render_index(mods)
    assert "GENERATED — DO NOT EDIT" in index
    assert "moderatorim-sdk" in index  # version line names the distribution
    assert "organized by module" in index
    assert "(./bus.md)" in index
    assert "(./moderatorim-ui.md)" in index


@needs_griffe2md
def test_render_page_has_header_and_symbols() -> None:
    page = sdk_docsgen.render_page("moderatorim.sdk.bus")
    assert page.startswith("<!-- GENERATED")
    assert "# `moderatorim.sdk.bus`" in page
    # A known public symbol from the bus module must appear.
    assert "Action" in page


@needs_griffe2md
def test_generate_writes_index_and_one_page_per_module_and_cleans(tmp_path) -> None:
    out = tmp_path / "sdk-ref"
    out.mkdir()
    orphan = out / "stale-module.md"
    orphan.write_text("old", encoding="utf-8")

    written = sdk_docsgen.generate(out)

    assert not orphan.exists()  # fully rebuilt, no orphans
    names = {p.name for p in written}
    assert "index.md" in names
    assert "bus.md" in names
    assert "models.md" in names
    assert "moderatorim-ui.md" in names


@needs_griffe2md
def test_generated_output_has_no_leaks(tmp_path) -> None:
    written = sdk_docsgen.generate(tmp_path / "sdk-ref")
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
