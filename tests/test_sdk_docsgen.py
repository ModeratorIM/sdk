"""Tests for the SDK API Markdown reference generator (``moderatorim.sdk_docsgen``).

The heavy rendering path needs the optional ``[docs]`` extra (griffe2md). CI's default ``[dev]``
env does not install it, so those tests skip cleanly when it is absent; the version/index/layout
logic is tested unconditionally.
"""

from __future__ import annotations

import importlib.util

import pytest

from moderatorim import sdk_docsgen

_HAS_GRIFFE2MD = importlib.util.find_spec("griffe2md") is not None
needs_griffe2md = pytest.mark.skipif(
    not _HAS_GRIFFE2MD, reason="requires the [docs] extra (griffe2md)"
)


def test_packages_cover_sdk_and_ui_not_cli() -> None:
    assert "moderatorim.sdk" in sdk_docsgen.PACKAGES
    assert "moderatorim.ui" in sdk_docsgen.PACKAGES
    # The CLI is documented by moderatorim.cli.docsgen, not here.
    assert "moderatorim.cli" not in sdk_docsgen.PACKAGES


def test_slug() -> None:
    assert sdk_docsgen._slug("moderatorim.ui") == "moderatorim-ui"
    assert sdk_docsgen._slug("moderatorim.sdk") == "moderatorim-sdk"


def test_index_records_version_and_links() -> None:
    index = sdk_docsgen.render_index()
    assert "GENERATED — DO NOT EDIT" in index
    assert "moderatorim-sdk" in index  # version line names the distribution
    assert "(./moderatorim-sdk.md)" in index
    assert "(./moderatorim-ui.md)" in index


@needs_griffe2md
def test_render_page_has_header_and_symbols() -> None:
    page = sdk_docsgen.render_page("moderatorim.sdk")
    assert page.startswith("<!-- GENERATED")
    assert "# `moderatorim.sdk`" in page
    # A known public symbol from the real surface must appear.
    assert "Ctx" in page


@needs_griffe2md
def test_generate_writes_index_and_pages_and_cleans(tmp_path) -> None:
    out = tmp_path / "sdk-ref"
    out.mkdir()
    orphan = out / "stale-module.md"
    orphan.write_text("old", encoding="utf-8")

    written = sdk_docsgen.generate(out)

    assert not orphan.exists()  # fully rebuilt, no orphans
    names = {p.name for p in written}
    assert "index.md" in names
    assert "moderatorim-sdk.md" in names
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
        sdk_docsgen.render_page("moderatorim.sdk")
    assert "griffe2md" in str(exc.value)
    assert "[docs]" in str(exc.value)
