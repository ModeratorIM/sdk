"""Generate Markdown reference for the ModeratorIM SDK's public API using ``griffe2md``.

``griffe`` parses the Python source statically (no execution) and ``griffe2md`` renders Markdown
from the signatures + docstrings. This walker drives it over the public packages —
``moderatorim.sdk`` (the contract API) and ``moderatorim.ui`` (the UI building blocks) — and writes
one page per package into the reference tree. The ``moderatorim`` CLI is documented separately by
:mod:`moderatorim.cli.docsgen` (its source of truth is the argparse parser, not docstrings).

Generated Markdown is a *build artifact*: each page carries a "generated — do not edit" header,
the index records the documented SDK version, and :func:`generate` fully rebuilds the tree each run
so a removed module leaves no orphan page.

Usage (from the SDK repo, with ``griffe2md`` installed)::

    python -m moderatorim.sdk_docsgen [OUTPUT_DIR]

``OUTPUT_DIR`` defaults to ``generated-docs/sdk/reference`` relative to the current directory.
``griffe2md`` is an optional dev/docs dependency; import errors carry an actionable message.
"""

from __future__ import annotations

import importlib.metadata
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from types import ModuleType

# The public packages to document, in reader order. The CLI is intentionally excluded — it is
# generated from its argparse parser by moderatorim.cli.docsgen.
PACKAGES: tuple[str, ...] = ("moderatorim.sdk", "moderatorim.ui")

DEFAULT_OUTPUT = Path("generated-docs/sdk/reference")

_DO_NOT_EDIT = (
    "<!-- GENERATED — DO NOT EDIT. Regenerate with `python -m moderatorim.sdk_docsgen`. -->"
)


def _require_griffe2md() -> ModuleType:
    """Import ``griffe2md`` or raise an actionable error if the docs extra is not installed."""
    try:
        import griffe2md  # noqa: PLC0415
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit(
            "griffe2md is not installed. Install the docs tooling with "
            "`pip install moderatorim-sdk[docs]` (or `pip install griffe2md`) and retry."
        ) from exc
    return cast("ModuleType", griffe2md)


def _sdk_version() -> str:
    try:
        return importlib.metadata.version("moderatorim-sdk")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


def _slug(package: str) -> str:
    """A filesystem-safe slug for a package, e.g. 'moderatorim.ui' -> 'moderatorim-ui'."""
    return package.replace(".", "-")


def render_page(package: str) -> str:
    """Render one public package to a Markdown page (header + griffe2md body)."""
    griffe2md = _require_griffe2md()
    body = griffe2md.render_package_docs(package, format_md=False)
    return f"{_DO_NOT_EDIT}\n\n# `{package}`\n\n{body.strip()}\n"


def render_index() -> str:
    """Render the reference index page, recording the documented SDK version."""
    lines = [
        _DO_NOT_EDIT,
        "",
        "# SDK API reference",
        "",
        f"Generated from **moderatorim-sdk {_sdk_version()}**. "
        "These pages are derived from the code — never hand-edited.",
        "",
    ]
    for package in PACKAGES:
        lines.append(f"- [`{package}`](./{_slug(package)}.md)")
    lines.append("")
    return "\n".join(lines)


def generate(output_dir: Path | str = DEFAULT_OUTPUT) -> list[Path]:
    """Fully (re)generate the SDK API reference Markdown tree under ``output_dir``.

    The directory is removed and rebuilt so a removed package leaves no orphan page. Returns the
    sorted list of written paths (index first).
    """
    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    index_path = out / "index.md"
    index_path.write_text(render_index(), encoding="utf-8")
    written.append(index_path)

    for package in PACKAGES:
        path = out / f"{_slug(package)}.md"
        path.write_text(render_page(package), encoding="utf-8")
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
