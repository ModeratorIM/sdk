"""Generate Markdown reference for the ``moderatorim`` CLI from its ``argparse`` parser.

The parser built by :func:`moderatorim.cli.build_parser` is the single source of truth: this
walker introspects it (top-level parser plus every subparser) and renders one Markdown page per
command, so the reference can never contradict ``moderatorim --help``. It adds no third-party
dependency — ``argparse`` already exposes everything needed.

Generated Markdown is a *build artifact*: every page carries a "generated — do not edit" header
naming the command that reproduces it, and :func:`generate` fully rebuilds the output tree on each
run (removing orphan pages) so a removed command leaves no stale page behind.

Usage (from the SDK repo)::

    python -m moderatorim.cli.docsgen [OUTPUT_DIR]

``OUTPUT_DIR`` defaults to ``generated-docs/cli/reference`` relative to the current directory.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import build_parser

_DO_NOT_EDIT = (
    "<!-- GENERATED — DO NOT EDIT. Regenerate with `python -m moderatorim.cli.docsgen`. -->"
)

# The default output tree, relative to the caller's working directory.
DEFAULT_OUTPUT = Path("generated-docs/cli/reference")


def _iter_subparsers(
    parser: argparse.ArgumentParser,
) -> list[argparse._SubParsersAction[argparse.ArgumentParser]]:
    """Return the ``_SubParsersAction`` objects registered on ``parser`` (usually zero or one)."""
    return [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]


def _visible_options(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    """Actions worth documenting: skip the auto ``-h/--help`` and the subparser dispatch action."""
    out: list[argparse.Action] = []
    for action in parser._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        out.append(action)
    return out


def _render_options(parser: argparse.ArgumentParser) -> list[str]:
    """Render a Markdown table of a command's positional args and options."""
    actions = _visible_options(parser)
    if not actions:
        return []
    lines = ["", "| Argument | Description |", "| -------- | ----------- |"]
    for action in actions:
        if action.option_strings:
            name = ", ".join(f"`{opt}`" for opt in action.option_strings)
            if action.metavar:
                name += f" `{action.metavar}`"
        else:
            name = f"`{action.metavar or action.dest}`"
        help_text = (action.help or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {name} | {help_text} |")
    return lines


def _render_command(name: str, parser: argparse.ArgumentParser, help_text: str) -> str:
    """Render one command page: title, description, usage block, options, and subcommand list."""
    title = name.replace("moderatorim ", "").strip() or "moderatorim"
    lines = [_DO_NOT_EDIT, "", f"# `{name}`", ""]
    description = (parser.description or help_text or "").strip()
    if description:
        lines += [description, ""]
    usage = parser.format_usage().strip()
    # argparse prefixes usage with "usage: "; drop it for a clean fenced block.
    usage = usage[len("usage: ") :] if usage.lower().startswith("usage: ") else usage
    lines += ["## Usage", "", "```", usage, "```"]
    lines += _render_options(parser)

    subs = _iter_subparsers(parser)
    child_names = sorted({n for sub in subs for n in sub.choices})
    if child_names:
        lines += ["", "## Subcommands", ""]
        for child in child_names:
            lines.append(f"- [`{name} {child}`](./{_slug(f'{title} {child}')}.md)")
    lines.append("")
    return "\n".join(lines)


def _slug(name: str) -> str:
    """A filesystem-safe slug for a (sub)command name, e.g. 'create app' -> 'create-app'."""
    return name.strip().replace(" ", "-") or "index"


def _walk(
    prefix: str,
    parser: argparse.ArgumentParser,
    help_text: str,
    pages: dict[str, str],
) -> None:
    """Recursively render ``parser`` and each of its subparsers into ``pages`` keyed by slug."""
    slug = _slug(prefix.replace("moderatorim", "").strip()) if prefix != "moderatorim" else "index"
    pages[slug] = _render_command(prefix, parser, help_text)
    for sub in _iter_subparsers(parser):
        # Map each choice to its help text (from the subparser action's _choices_actions).
        help_by_choice = {a.dest: (a.help or "") for a in sub._choices_actions}
        for child_name, child_parser in sub.choices.items():
            # Skip alias duplicates: argparse registers aliases pointing at the same parser.
            if any(
                child_parser is other and child_name != canonical
                for canonical, other in sub.choices.items()
                if canonical in help_by_choice
            ):
                continue
            _walk(
                f"{prefix} {child_name}",
                child_parser,
                help_by_choice.get(child_name, ""),
                pages,
            )


def render_pages(parser: argparse.ArgumentParser | None = None) -> dict[str, str]:
    """Render the whole CLI to a ``{slug: markdown}`` mapping without touching the filesystem."""
    parser = parser or build_parser()
    pages: dict[str, str] = {}
    _walk("moderatorim", parser, "", pages)
    return pages


def generate(output_dir: Path | str = DEFAULT_OUTPUT) -> list[Path]:
    """Fully (re)generate the CLI reference Markdown tree under ``output_dir``.

    The directory is removed and rebuilt so a removed command leaves no orphan page. Returns the
    sorted list of written paths.
    """
    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug, body in render_pages().items():
        path = out / f"{slug}.md"
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return sorted(written)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    output = Path(args[0]) if args else DEFAULT_OUTPUT
    written = generate(output)
    for path in written:
        print(f"  wrote {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
