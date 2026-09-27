"""Generate Markdown reference for the ModeratorIM SDK's public API using ``griffe2md``.

``griffe`` parses the Python source statically (no execution) and ``griffe2md`` renders Markdown
from the signatures + docstrings. The reference is **module-first** (the convention used by the
Python standard library, Django, Rust and Flutter docs): one page per public module, each page
sub-sectioned by kind (classes, functions, attributes) by griffe2md itself — rather than one giant
page or a flat alphabetical symbol list. A developer navigates to the module they are working with
(``bus``, ``datastore``, ``views``, …) and sees everything it exposes.

Documented surfaces:

* ``moderatorim.sdk`` — the contract API, one page per public submodule (bus, cachestore,
  datastore, models, registry, validation, views, web — discovered dynamically);
* ``moderatorim.ui`` — the UI building blocks, one page.

The ``moderatorim`` CLI is documented separately by :mod:`moderatorim.cli.docsgen` (its source of
truth is the argparse parser, not docstrings).

Generated Markdown is a *build artifact*: each page carries a "generated — do not edit" header,
the index records the documented SDK version, and :func:`generate` fully rebuilds the tree each run
so a removed module leaves no orphan page.

Usage (from the SDK repo, with ``griffe2md`` installed)::

    python -m moderatorim.sdk_docsgen [OUTPUT_DIR]

``OUTPUT_DIR`` defaults to ``generated-docs/sdk/reference`` relative to the current directory.
``griffe2md`` is an optional dev/docs dependency; import errors carry an actionable message.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import pkgutil
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from types import ModuleType

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


def public_modules() -> list[str]:
    """The public modules to document, module-first, in reader order.

    The ``moderatorim.sdk`` public submodules are discovered dynamically (any non-underscore
    package under it), so a new subsystem is documented automatically. ``moderatorim.ui`` is a
    top-level peer facet documented as one page.
    """
    sdk = importlib.import_module("moderatorim.sdk")
    subs = sorted(m.name for m in pkgutil.iter_modules(sdk.__path__) if not m.name.startswith("_"))
    mods = [f"moderatorim.sdk.{name}" for name in subs]
    mods.append("moderatorim.ui")
    return mods


def _slug(module: str) -> str:
    """A filesystem-safe slug for a module, e.g. 'moderatorim.sdk.bus' -> 'bus';
    'moderatorim.ui' -> 'moderatorim-ui'."""
    if module.startswith("moderatorim.sdk."):
        return module[len("moderatorim.sdk.") :].replace(".", "-")
    return module.replace(".", "-")


def render_page(module: str) -> str:
    """Render one public module to a Markdown page (header + griffe2md body).

    Uses griffe2md's object renderer so the page is sub-sectioned by kind (classes, functions,
    attributes) within the module.
    """
    griffe2md = _require_griffe2md()
    import griffe  # noqa: PLC0415

    obj = griffe.load(module, submodules=True, allow_inspection=True)
    body = griffe2md.render_object_docs(obj)
    return f"{_DO_NOT_EDIT}\n\n# `{module}`\n\n{body.strip()}\n"


def render_index(modules: list[str]) -> str:
    """Render the reference index page, recording the documented SDK version."""
    lines = [
        _DO_NOT_EDIT,
        "",
        "# SDK API reference",
        "",
        f"Generated from **moderatorim-sdk {_sdk_version()}**. "
        "These pages are derived from the code — never hand-edited. "
        "Reference is organized by module.",
        "",
    ]
    for module in modules:
        lines.append(f"- [`{module}`](./{_slug(module)}.md)")
    lines.append("")
    return "\n".join(lines)


def generate(output_dir: Path | str = DEFAULT_OUTPUT) -> list[Path]:
    """Fully (re)generate the module-first SDK API reference tree under ``output_dir``.

    The directory is removed and rebuilt so a removed module leaves no orphan page. Returns the
    sorted list of written paths.
    """
    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    modules = public_modules()
    written: list[Path] = []
    index_path = out / "index.md"
    index_path.write_text(render_index(modules), encoding="utf-8")
    written.append(index_path)

    for module in modules:
        path = out / f"{_slug(module)}.md"
        path.write_text(render_page(module), encoding="utf-8")
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
