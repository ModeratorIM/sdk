"""i18n declaration contract (i18n spec §10b) — the declarative descriptors a unit ships.

A unit DECLARES translatable strings; core RENDERS them (the same declare-vs-render seam as nav
and styles). These are pure data descriptors — the translation ENGINE (``t()``, the catalog, the
cache, locale resolution) lives in core, not here. A unit hands core a :class:`TranslationSet`
through ``app.translations(...)`` in its ``register(app)`` hook; core seeds it INSERT-IF-MISSING
into the ``core_translation`` catalog, stamping the owning unit as the ``source``.

Format is JSON: a ``TranslationSet(dir="languages")`` names a ``translations/languages/`` folder of
``{code}.json`` files (``{key: value}`` maps, filename stem == the BCP-47 locale code). The ``t()``
API is deliberately storage-agnostic so a ``.po`` backend can replace the JSON reader later without
touching call sites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Locale:
    """An enabled/declared language. ``code`` is a BCP-47 hyphenated code (``en``, ``en-US``,
    ``fr-FR``) — stored verbatim as the ``core_translation.language`` value, the JSON filename
    stem, and the ``<html lang>`` value. The endonym + flag come from core's own map, not here
    (languages are universal, not unit-specific)."""

    code: str

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Locale.code must be non-empty")


@dataclass(frozen=True, slots=True)
class Translation:
    """One message: ``(key, language) -> value`` — the atom seeded into ``core_translation``.
    ``value`` may carry ``{param}`` placeholders interpolated by ``t()`` at render."""

    key: str
    language: str  # the locale code (BCP-47), stored as-is
    value: str

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("Translation.key must be non-empty")
        if not self.language:
            raise ValueError(f"Translation {self.key!r} requires a non-empty language")


@dataclass(frozen=True, slots=True)
class TranslationSet:
    """A unit's declared translations. Either explicit ``entries``, OR a ``dir`` naming a
    ``languages/`` folder of ``{code}.json`` files core reads. ``source`` (the owning unit, as
    ``{type}.{name}``) is populated by CORE from the declaring unit — a unit never sets it."""

    source: str = ""  # owning unit ({type}.{name}); populated by core at register
    dir: str = ""  # e.g. "languages", relative to base_dir
    entries: tuple[Translation, ...] = ()

    def __post_init__(self) -> None:
        if not self.dir and not self.entries:
            raise ValueError("TranslationSet requires either `dir` or `entries`")
        if self.dir and self.entries:
            raise ValueError("TranslationSet cannot set both `dir` and `entries`")

    def load(self, base_dir: str | Path) -> tuple[Translation, ...]:
        """Resolve this set's declared entries. For an ``entries`` set, returns them as-is. For a
        ``dir`` set, reads every ``{code}.json`` ({key: value}) under ``base_dir/{dir}`` and
        flattens it into ``Translation`` rows (filename stem == the locale code). ``base_dir`` is
        the declaring unit's package directory (core passes it at register)."""
        if self.entries:
            return self.entries
        folder = Path(base_dir) / self.dir
        out: list[Translation] = []
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                code = path.stem
                data = json.loads(path.read_text(encoding="utf-8"))
                for key, value in data.items():
                    out.append(Translation(key=key, language=code, value=str(value)))
        return tuple(out)
