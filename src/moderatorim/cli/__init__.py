"""The ``moderatorim`` command-line tool — scaffolds ModeratorIM units and their components.

This module lives at ``moderatorim.cli`` (a sibling of ``moderatorim.sdk``, SDK-owned by
convention) and is exposed as the ``moderatorim`` console script. It is a thin ``argparse``
dispatcher; the templating work lives in :mod:`moderatorim.cli.render`.

v1 implements ``create app`` (a create-container action that runs in ANY directory). The
domain-first ``generate`` family (operate-in-app) is a fast-follow.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from moderatorim.cli.context import ContextError, detect_unit
from moderatorim.cli.manifest_edit import ManifestEditError, register_model
from moderatorim.cli.render import RenderError, render_kind

# A unit module name: lowercase, starts with a letter, letters/digits/underscore — matches the
# Manifest.name rule (lowercase, no spaces) and is import-safe as a package name.
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _title_from(name: str) -> str:
    """A default human title from a module name: 'my_product' -> 'My Product'."""
    return " ".join(part.capitalize() for part in name.split("_"))


def _create_app(args: argparse.Namespace) -> int:
    name: str = args.name
    if not _NAME_RE.match(name):
        print(
            f"error: {name!r} is not a valid module name — use lowercase letters, digits and "
            "underscores, starting with a letter (e.g. 'my_product').",
            file=sys.stderr,
        )
        return 2

    dest = Path.cwd() / name
    if dest.exists():
        print(f"error: {dest} already exists — refusing to overwrite.", file=sys.stderr)
        return 2

    display_name = args.display_name or _title_from(name)
    description = args.description or f"The {display_name} ModeratorIM app."
    variables = {
        "name": name,
        "Name": name[:1].upper() + name[1:],
        "display_name": display_name,
        "description": description,
        "version": args.version,
    }
    try:
        written = render_kind("app", dest, variables)
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Created app {name!r} at {dest} ({len(written)} files).")
    print(f"  Next: cd {name} && moderatorim generate model <domain>")
    return 0


_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _parse_fields(raw: list[str] | None) -> str:
    """Render --field name:type args into the model columns body. Defaults to one TEXT column."""
    _TYPE_MAP = {
        "str": "TEXT",
        "text": "TEXT",
        "textarea": "TEXTAREA",
        "int": "INTEGER",
        "integer": "INTEGER",
        "bool": "BOOLEAN",
        "boolean": "BOOLEAN",
        "float": "FLOAT",
        "date": "DATE",
        "datetime": "DATETIME",
        "object": "OBJECT",
    }
    entries: list[tuple[str, str]] = []
    for spec in raw or []:
        fname, _, ftype = spec.partition(":")
        ft = _TYPE_MAP.get(ftype.lower().strip(), "TEXT")
        entries.append((fname.strip(), ft))
    if not entries:
        entries = [("name", "TEXT")]
    return "\n".join(f'        TableColumn(name="{n}", type=FieldType.{t}),' for n, t in entries)


def _generate(args: argparse.Namespace) -> int:
    artifact: str = args.artifact
    domain: str = args.domain
    if not _DOMAIN_RE.match(domain):
        print(
            f"error: {domain!r} is not a valid domain name — lowercase letters, digits and "
            "underscores, starting with a letter.",
            file=sys.stderr,
        )
        return 2

    try:
        unit = detect_unit()
        unit.require_artifact(artifact)
    except ContextError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root = unit.manifest_path.parent
    Domain = domain[:1].upper() + domain[1:]
    variables = {
        "name": domain,
        "Name": Domain,
        "domain": domain,
        "Domain": Domain,
        "app": unit.name,
        "fields": _parse_fields(getattr(args, "field", None)),
    }
    # test renders into tests/; every other artifact renders into the <domain>/ package.
    dest = (root / "tests") if artifact == "test" else (root / domain)
    try:
        written = render_kind(artifact, dest, variables)
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if artifact == "model":
        try:
            register_model(unit.manifest_path, unit.name, domain, Domain)
        except ManifestEditError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    for path in written:
        print(f"  created {path.relative_to(root.parent)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moderatorim", description="ModeratorIM app scaffolding CLI."
    )
    sub = parser.add_subparsers(dest="verb", metavar="<verb>")

    create = sub.add_parser("create", help="Create a new unit (app / backend / platform).")
    create_sub = create.add_subparsers(dest="kind", metavar="<kind>")

    app = create_sub.add_parser("app", help="Scaffold a new app in the current directory.")
    app.add_argument("name", help="Module name (lowercase, e.g. 'my_product').")
    app.add_argument(
        "--display-name",
        "--name",
        dest="display_name",
        default="",
        help="Human-facing title (Manifest.display_name). Defaults to a title-cased module name.",
    )
    app.add_argument(
        "--description",
        default="",
        help="One-line description (goes in the generated README, not the manifest).",
    )
    app.add_argument("--version", default="0.0.0", help="Initial Manifest.version (default 0.0.0).")
    app.set_defaults(func=_create_app)

    gen = sub.add_parser(
        "generate",
        aliases=["g"],
        help="Generate a domain artifact in the current unit (model/service/route/view/test).",
    )
    gen_sub = gen.add_subparsers(dest="artifact", metavar="<artifact>")
    for artifact in ("model", "service", "route", "view", "test"):
        p = gen_sub.add_parser(artifact, help=f"Generate a {artifact} for a domain.")
        p.add_argument("domain", help="Domain name (lowercase, e.g. 'users').")
        if artifact == "model":
            p.add_argument(
                "--field",
                action="append",
                metavar="NAME:TYPE",
                help="Repeatable field, e.g. --field title:str (str/int/bool/float/text/datetime).",
            )
        p.set_defaults(func=_generate, artifact=artifact)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 2
    return int(func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
