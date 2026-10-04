"""Tests for the i18n declaration descriptors (SDK contract, Stage 1)."""

from __future__ import annotations

import json

import pytest

from moderatorim.sdk import Locale, Translation, TranslationSet


def test_locale_requires_code() -> None:
    assert Locale("en").code == "en"
    assert Locale("fr-FR").code == "fr-FR"
    with pytest.raises(ValueError, match="code must be non-empty"):
        Locale("")


def test_translation_requires_key_and_language() -> None:
    t = Translation(key="app.admin.title", language="en", value="Admin")
    assert (t.key, t.language, t.value) == ("app.admin.title", "en", "Admin")
    with pytest.raises(ValueError, match="key must be non-empty"):
        Translation(key="", language="en", value="x")
    with pytest.raises(ValueError, match="non-empty language"):
        Translation(key="k", language="", value="x")


def test_translation_set_requires_dir_xor_entries() -> None:
    # entries-only is valid
    ts = TranslationSet(entries=(Translation("k", "en", "v"),))
    assert ts.load("/nonexistent") == (Translation("k", "en", "v"),)
    # dir-only is valid
    assert TranslationSet(dir="languages").dir == "languages"
    # neither -> error
    with pytest.raises(ValueError, match="either `dir` or `entries`"):
        TranslationSet()
    # both -> error
    with pytest.raises(ValueError, match="cannot set both"):
        TranslationSet(dir="languages", entries=(Translation("k", "en", "v"),))


def test_translation_set_loads_json_catalogs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    langs = tmp_path / "languages"
    langs.mkdir()
    (langs / "en.json").write_text(
        json.dumps({"greeting": "Hello", "bye": "Bye"}), encoding="utf-8"
    )
    (langs / "fr-FR.json").write_text(json.dumps({"greeting": "Bonjour"}), encoding="utf-8")
    rows = TranslationSet(dir="languages").load(tmp_path)
    # filename stem == locale code, verbatim (BCP-47 hyphenated preserved)
    by = {(r.language, r.key): r.value for r in rows}
    assert by[("en", "greeting")] == "Hello"
    assert by[("en", "bye")] == "Bye"
    assert by[("fr-FR", "greeting")] == "Bonjour"
    assert len(rows) == 3


def test_translation_set_source_defaults_empty() -> None:
    # source is populated by CORE at register, never by the declaring unit
    assert TranslationSet(dir="languages").source == ""
