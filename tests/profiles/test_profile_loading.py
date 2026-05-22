"""Tests for Profile loading and JSON Schema validation."""

from __future__ import annotations

import json

import pytest

from openioc.profiles import Profile
from openioc.profiles.exceptions import ProfileSchemaError


@pytest.fixture(autouse=True)
def require_jsonschema():
    pytest.importorskip("jsonschema")


class TestFromDict:
    def test_minimal_valid(self):
        profile = Profile.from_dict({"schema_version": "1.0.0", "name": "test"})
        assert profile.name == "test"
        assert profile.schema_version == "1.0.0"

    def test_full_valid(self):
        data = {
            "schema_version": "1.0.0",
            "name": "full-test",
            "profile_version": "1.2.3",
            "target_product": "Acme SIEM",
            "target_versions": ["3.x", "4.x"],
            "description": "A full profile",
            "source": "https://example.com/docs",
            "terms": {
                "FileItem/FileName": {
                    "operators": ["is", "contains"],
                    "content_types": ["string"],
                    "description": "file name",
                }
            },
            "structure": {
                "max_nesting": 3,
                "allow_or_at_top_level": False,
                "allow_or_inside_and": True,
                "allow_and_inside_or": True,
            },
            "mappings": {"OldItem/Field": "NewItem/Field"},
        }
        p = Profile.from_dict(data)
        assert p.profile_version == "1.2.3"
        assert p.target_versions == ("3.x", "4.x")
        assert p.terms["FileItem/FileName"].operators == ("is", "contains")
        assert p.terms["FileItem/FileName"].content_types == ("string",)
        assert p.structure.max_nesting == 3
        assert p.structure.allow_or_at_top_level is False
        assert p.mappings == {"OldItem/Field": "NewItem/Field"}

    def test_target_versions_string(self):
        p = Profile.from_dict({"schema_version": "1.0.0", "name": "t", "target_versions": "2.x"})
        assert p.target_versions == ("2.x",)

    def test_missing_required_name_raises(self):
        with pytest.raises(ProfileSchemaError) as exc_info:
            Profile.from_dict({"schema_version": "1.0.0"})
        assert "name" in str(exc_info.value)

    def test_missing_schema_version_raises(self):
        with pytest.raises(ProfileSchemaError):
            Profile.from_dict({"name": "x"})

    def test_invalid_name_pattern_raises(self):
        with pytest.raises(ProfileSchemaError):
            Profile.from_dict({"schema_version": "1.0.0", "name": "Has Spaces"})

    def test_term_missing_operators_raises(self):
        with pytest.raises(ProfileSchemaError):
            Profile.from_dict(
                {
                    "schema_version": "1.0.0",
                    "name": "bad",
                    "terms": {"FileItem/FileName": {}},
                }
            )

    def test_extra_top_level_field_raises(self):
        with pytest.raises(ProfileSchemaError):
            Profile.from_dict({"schema_version": "1.0.0", "name": "x", "unknown_field": True})


class TestSchemaVersion:
    def test_unsupported_major_raises(self):
        with pytest.raises(ProfileSchemaError, match="major=99"):
            Profile.from_dict({"schema_version": "99.0.0", "name": "x"})

    def test_minor_patch_ignored(self):
        p = Profile.from_dict({"schema_version": "1.5.3", "name": "x"})
        assert p.schema_version == "1.5.3"

    def test_invalid_semver_raises(self):
        with pytest.raises(ProfileSchemaError):
            Profile.from_dict({"schema_version": "not-a-version", "name": "x"})


class TestFromJson:
    def test_valid_json(self):
        text = json.dumps({"schema_version": "1.0.0", "name": "json-test"})
        p = Profile.from_json(text)
        assert p.name == "json-test"

    def test_malformed_json_raises(self):
        with pytest.raises(ProfileSchemaError, match="Invalid JSON"):
            Profile.from_json("{not valid json")


class TestFromFile:
    def test_loads_fixture(self, synthetic_profile_path):
        p = Profile.from_file(synthetic_profile_path)
        assert p.name == "synthetic"
        assert "FileItem/FileName" in p.terms

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(OSError):
            Profile.from_file(tmp_path / "nonexistent.json")
