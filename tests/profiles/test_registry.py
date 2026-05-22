"""Tests for the profile registry (register/unregister/get/list + entry-point mock)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openioc.profiles import (
    Profile,
    get_profile,
    list_profiles,
    register_profile,
    unregister_profile,
)
from openioc.profiles.exceptions import ProfileError, UnknownProfileError
from openioc.profiles.registry import _reset


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the registry and suppress installed entry points for isolation."""
    _reset()
    # Suppress any installed profile packages so tests are hermetic.
    with patch("importlib.metadata.entry_points", return_value=[]):
        yield
    _reset()


def _make_profile(name: str) -> Profile:
    # Bypass jsonschema so these tests work without the optional extra.
    return Profile._from_validated_dict(
        {
            "schema_version": "1.0.0",
            "name": name,
            "terms": {
                "FileItem/FileName": {"operators": ["is"]},
            },
        }
    )


class TestRegisterAndGet:
    def test_register_then_get(self):
        p = _make_profile("myproduct")
        register_profile(p)
        assert get_profile("myproduct") is p

    def test_list_after_register(self):
        register_profile(_make_profile("a"))
        register_profile(_make_profile("b"))
        assert list_profiles() == ["a", "b"]

    def test_list_is_sorted(self):
        register_profile(_make_profile("zz"))
        register_profile(_make_profile("aa"))
        assert list_profiles() == ["aa", "zz"]

    def test_duplicate_name_raises(self):
        register_profile(_make_profile("dup"))
        with pytest.raises(ProfileError, match="dup"):
            register_profile(_make_profile("dup"))

    def test_unknown_name_raises(self):
        with pytest.raises(UnknownProfileError, match="nope"):
            get_profile("nope")


class TestUnregister:
    def test_unregister_removes(self):
        register_profile(_make_profile("gone"))
        unregister_profile("gone")
        with pytest.raises(UnknownProfileError):
            get_profile("gone")

    def test_unregister_unknown_raises(self):
        with pytest.raises(UnknownProfileError):
            unregister_profile("ghost")

    def test_re_register_after_unregister(self):
        p = _make_profile("reuse")
        register_profile(p)
        unregister_profile("reuse")
        register_profile(p)
        assert get_profile("reuse") is p


class TestEntryPointDiscovery:
    def test_entry_point_profile_is_discovered(self):
        mock_profile = _make_profile("ep-test")
        mock_ep = MagicMock()
        mock_ep.name = "ep-test"
        mock_ep.load.return_value = lambda: mock_profile

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            _reset()
            assert "ep-test" in list_profiles()
            assert get_profile("ep-test") is mock_profile

    def test_broken_entry_point_raises_profile_error(self):
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("missing dep")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            _reset()
            with pytest.raises(ProfileError, match="broken"):
                list_profiles()

    def test_entry_point_duplicate_raises(self):
        mock_profile = _make_profile("clash")
        mock_ep = MagicMock()
        mock_ep.name = "clash"
        mock_ep.load.return_value = lambda: mock_profile

        with patch("importlib.metadata.entry_points", return_value=[mock_ep, mock_ep]):
            _reset()
            with pytest.raises(ProfileError, match="clash"):
                list_profiles()
