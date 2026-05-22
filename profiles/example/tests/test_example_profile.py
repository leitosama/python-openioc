"""Smoke test: the example profile loads and passes schema validation."""

import pytest

from openioc.profiles import Profile


def test_profile_loads() -> None:
    jsonschema = pytest.importorskip("jsonschema")  # noqa: F841
    from openioc_profile_example import load

    profile = load()
    assert isinstance(profile, Profile)
    assert profile.name == "example"
    assert "FileItem/FileName" in profile.terms


def test_profile_has_expected_terms() -> None:
    pytest.importorskip("jsonschema")
    from openioc_profile_example import load

    profile = load()
    assert set(profile.terms.keys()) == {
        "FileItem/FileName",
        "FileItem/Md5sum",
        "RegistryItem/Path",
    }
