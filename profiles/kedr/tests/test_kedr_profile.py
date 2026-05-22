"""Smoke test: the KEDR profile loads and passes schema validation."""

import pytest

from openioc.profiles import Profile


def test_profile_loads() -> None:
    pytest.importorskip("jsonschema")
    from openioc_profile_kedr import load

    profile = load()
    assert isinstance(profile, Profile)
    assert profile.name == "kedr"
    assert profile.target_product == "Kaspersky Anti Targeted Attack — KEDR"


def test_profile_has_file_terms() -> None:
    pytest.importorskip("jsonschema")
    from openioc_profile_kedr import load

    profile = load()
    assert "FileItem/FileName" in profile.terms
    assert "FileItem/Md5sum" in profile.terms
    assert "is" in profile.terms["FileItem/Md5sum"].operators
