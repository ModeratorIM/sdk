"""Tests for the CLI Markdown reference generator (``moderatorim.cli.docsgen``)."""

from __future__ import annotations

import argparse

from moderatorim.cli import build_parser, docsgen


def test_renders_top_level_and_known_verbs() -> None:
    pages = docsgen.render_pages()
    # Top-level index plus a page per (sub)command.
    assert "index" in pages
    assert "create" in pages
    assert "create-app" in pages
    assert "generate-model" in pages


def test_create_app_page_lists_its_flags() -> None:
    page = docsgen.render_pages()["create-app"]
    # Titled by the command name without the `moderatorim ` prefix.
    assert "# `create app`" in page
    assert "# `moderatorim create app`" not in page
    # The positional and the real options must appear.
    assert "`name`" in page
    assert "--display-name" in page
    assert "--description" in page
    assert "--version" in page
    # Every generated page is marked as a build artifact.
    assert "GENERATED — DO NOT EDIT" in page


def test_usage_block_is_present() -> None:
    page = docsgen.render_pages()["create-app"]
    assert "## Usage" in page
    assert "moderatorim create app" in page


def test_removed_verb_disappears() -> None:
    """A parser without the 'generate' verb produces no generate pages (no orphans)."""
    parser = argparse.ArgumentParser(prog="moderatorim", description="test")
    sub = parser.add_subparsers(dest="verb", metavar="<verb>")
    create = sub.add_parser("create", help="Create.")
    create_sub = create.add_subparsers(dest="kind")
    app = create_sub.add_parser("app", help="Scaffold an app.")
    app.add_argument("name")

    pages = docsgen.render_pages(parser)
    assert "create-app" in pages
    assert not any(slug.startswith("generate") for slug in pages)


def test_generate_writes_and_cleans(tmp_path) -> None:
    out = tmp_path / "cli-ref"
    # Pre-seed a stale orphan file to prove the tree is fully rebuilt.
    out.mkdir()
    orphan = out / "stale-command.md"
    orphan.write_text("old", encoding="utf-8")

    written = docsgen.generate(out)

    assert orphan not in written
    assert not orphan.exists()  # removed on regeneration
    assert (out / "create-app.md").exists()
    assert all(p.suffix == ".md" for p in written)


def test_generate_is_idempotent(tmp_path) -> None:
    out = tmp_path / "cli-ref"
    first = {p.name: p.read_text(encoding="utf-8") for p in docsgen.generate(out)}
    second = {p.name: p.read_text(encoding="utf-8") for p in docsgen.generate(out)}
    assert first == second


def test_real_parser_has_no_leaks() -> None:
    """Generated CLI reference must carry no maintainer-internal paths (docs leak scan)."""
    blob = "\n".join(docsgen.render_pages().values()).lower()
    for needle in (".kiro", "crew", "appwrite", "supabase", "firebase", "whatsapp", "telegram"):
        assert needle not in blob


def test_parser_from_package_is_importable() -> None:
    """T0.3 sanity: build_parser is importable and returns an ArgumentParser."""
    assert isinstance(build_parser(), argparse.ArgumentParser)
