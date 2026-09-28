"""Unit context detection for operate-in-app commands (`generate …`).

A `generate` command operates on the unit whose root IS the current working directory: it requires
`./manifest.py` to exist there (NO ancestor walk-up — apps sit flat under a grouping dir, so the
unit is exactly cwd). From that manifest the CLI reads two things:

* the unit NAME — gives the `{app}_` table prefix and the manifest to register into;
* the unit KIND (`UnitType.APP` / `BACKEND` / `PLATFORM`) — gates which artifacts may be generated.

The kind is read static-parse-first (find ``type=UnitType.<KIND>`` in the source) so a half-set-up
manifest is not executed; an import is the authoritative fallback when the static read is
inconclusive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MANIFEST = "manifest.py"

# Which `generate` artifacts each unit kind may produce (design §3a).
_ALLOWED_BY_KIND: dict[str, frozenset[str]] = {
    "APP": frozenset({"model", "service", "routes", "view", "test"}),
    "BACKEND": frozenset({"service", "test"}),
    "PLATFORM": frozenset({"service", "test"}),
}

_TYPE_RE = re.compile(r"type\s*=\s*UnitType\.([A-Z]+)")
_NAME_RE = re.compile(r"""name\s*=\s*['"]([a-z][a-z0-9_]*)['"]""")


class ContextError(Exception):
    """Raised when the CLI is not in a unit directory, or the artifact is invalid for the kind."""


@dataclass(frozen=True)
class UnitContext:
    """The unit rooted at cwd: its name, kind, and manifest path."""

    name: str
    kind: str  # "APP" | "BACKEND" | "PLATFORM"
    manifest_path: Path

    def require_artifact(self, artifact: str) -> None:
        """Raise :class:`ContextError` if ``artifact`` is not valid for this unit's kind."""
        allowed = _ALLOWED_BY_KIND.get(self.kind, frozenset())
        if artifact not in allowed:
            raise ContextError(
                f"'{artifact}' is not valid in a {self.kind.lower()} unit "
                f"(allowed here: {', '.join(sorted(allowed)) or 'none'})"
            )


def _read_kind(source: str) -> str | None:
    m = _TYPE_RE.search(source)
    return m.group(1) if m else None


def _read_name(source: str) -> str | None:
    m = _NAME_RE.search(source)
    return m.group(1) if m else None


def _kind_via_import(manifest_path: Path) -> tuple[str, str] | None:
    """Authoritative fallback: import the manifest module and read manifest.type/name.
    Returns (name, KIND) or None if it cannot be loaded."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_mim_manifest_probe", manifest_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    manifest = getattr(module, "manifest", None)
    if manifest is None:
        return None
    kind = getattr(getattr(manifest, "type", None), "name", None)
    name = getattr(manifest, "name", None)
    if not kind or not name:
        return None
    return str(name), str(kind)


def detect_unit(cwd: Path | None = None) -> UnitContext:
    """Detect the unit rooted at ``cwd`` (default: the process cwd).

    Raises :class:`ContextError` if there is no ``manifest.py`` in cwd, or its kind cannot be
    determined. Reads static-parse-first, then falls back to importing the manifest.
    """
    root = cwd or Path.cwd()
    manifest_path = root / _MANIFEST
    if not manifest_path.is_file():
        raise ContextError(
            f"no {_MANIFEST} in {root} — run this from inside a unit directory (cwd IS the unit)."
        )
    source = manifest_path.read_text(encoding="utf-8")
    kind = _read_kind(source)
    name = _read_name(source)
    if kind is None or name is None:
        probed = _kind_via_import(manifest_path)
        if probed is None:
            raise ContextError(
                f"could not determine the unit name/kind from {manifest_path} "
                "(expected a Manifest with name=… and type=UnitType.…)."
            )
        name, kind = probed
    if kind not in _ALLOWED_BY_KIND:
        raise ContextError(f"unknown unit kind {kind!r} in {manifest_path}.")
    return UnitContext(name=name, kind=kind, manifest_path=manifest_path)
