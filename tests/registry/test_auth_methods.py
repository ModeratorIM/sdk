"""Tests for the AuthMethod sign-in contribution contract (auth-methods P1)."""

from __future__ import annotations

import pytest

from moderatorim.sdk import AuthMethod, Manifest, UnitType


def test_form_method_valid() -> None:
    m = AuthMethod(
        id="core.password",
        label="Email / Password",
        icon="mail",
        order=0,
        form=lambda: "<form></form>",
    )
    assert m.form is not None and m.redirect_url == ""


def test_redirect_method_valid() -> None:
    m = AuthMethod(id="sso.okta", label="Sign in with Okta", redirect_url="/sso/okta/start")
    assert m.redirect_url == "/sso/okta/start" and m.form is None


def test_requires_exactly_one_of_form_or_redirect() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        AuthMethod(id="bad.none", label="Neither")
    with pytest.raises(ValueError, match="exactly one"):
        AuthMethod(id="bad.both", label="Both", form=lambda: "x", redirect_url="/y")


def test_manifest_carries_auth_methods() -> None:
    method = AuthMethod(id="sso.okta", label="Okta", redirect_url="/sso/okta/start")
    m = Manifest(
        name="sso",
        type=UnitType.APP,
        register=lambda core: None,
        auth_methods=(method,),
    )
    assert m.auth_methods == (method,)


def test_manifest_auth_methods_defaults_empty() -> None:
    m = Manifest(name="plain", type=UnitType.APP, register=lambda core: None)
    assert m.auth_methods == ()
