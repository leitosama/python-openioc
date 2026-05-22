"""Golden tests: real fixture IOCs validated against the KEDR profile.

These tests require ``openioc-profile-kedr`` to be installed:

    pip install -e profiles/kedr

They are skipped gracefully if the package (or jsonschema) is absent.
"""

from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path

import pytest

import openioc
from openioc.profiles import AdapterPolicy, ProfileAdapter, ProfileValidator
from openioc.profiles.exceptions import AdaptationFailed
from openioc.profiles.registry import _reset
from openioc.profiles.report import ViolationCode

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def clean_registry():
    _reset()
    yield
    _reset()


@pytest.fixture(scope="module")
def kedr_installed():
    if importlib.util.find_spec("openioc_profile_kedr") is None:
        pytest.skip("openioc-profile-kedr is not installed; run: pip install -e profiles/kedr")


@pytest.fixture(scope="module")
def kedr_profile(kedr_installed):
    pytest.importorskip("jsonschema")
    from openioc.profiles import get_profile

    return get_profile("kedr")


class TestSharpstompVsKedr:
    def test_sharpstomp_has_unsupported_terms(self, kedr_profile):
        """SHARPSTOMP uses HX-specific terms not in the KEDR profile stub."""
        ioc = openioc.read(FIXTURES / "v11" / "sharpstomp.ioc")
        report = ProfileValidator(kedr_profile).validate(ioc)
        # The fixture uses fileWriteEvent/... and processEvent/... terms which
        # are not in the current KEDR stub — expect UNSUPPORTED_TERM violations.
        assert report.has_errors()
        unsupported = report.by_code(ViolationCode.UNSUPPORTED_TERM)
        assert len(unsupported) > 0

    def test_sharpstomp_adapt_drops_unsupported(self, kedr_profile):
        """Adapter with drop policy either produces a cleaned IOC or raises."""
        ioc = openioc.read(FIXTURES / "v11" / "sharpstomp.ioc")
        from openioc.profiles.exceptions import AdaptationFailed

        try:
            result = ProfileAdapter(kedr_profile, AdapterPolicy(drop_unsupported_items=True)).adapt(
                ioc
            )
            # All changes are DROPPED_ITEM.
            actions = {c.action for c in result.changes}
            assert actions <= {"DROPPED_ITEM"}
        except AdaptationFailed:
            # All items unsupported — valid outcome for a stub profile.
            pass

    def test_sharpstomp_original_not_mutated(self, kedr_profile):
        ioc = openioc.read(FIXTURES / "v11" / "sharpstomp.ioc")
        original_children = list(ioc.definition.children)  # type: ignore[union-attr]
        with contextlib.suppress(AdaptationFailed):
            ProfileAdapter(kedr_profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
        # Regardless of outcome, the original IOC must not be mutated.
        assert ioc.definition.children == original_children  # type: ignore[union-attr]


class TestWindigoVsKedr:
    def test_windigo_has_unsupported_terms(self, kedr_profile):
        """Operation Windigo uses Network/ and Snort/ terms not in the KEDR stub."""
        ioc = openioc.read(FIXTURES / "v10" / "windigo.ioc")
        ioc = openioc.convert_10_to_11(ioc)
        report = ProfileValidator(kedr_profile).validate(ioc)
        assert report.has_errors()
        unsupported = report.by_code(ViolationCode.UNSUPPORTED_TERM)
        assert len(unsupported) > 0
        # All violation terms should be Network/ or Snort/ or FileItem/Sha1sum
        terms = {v.details.get("term", "") for v in unsupported}
        assert all(t.startswith(("Network/", "Snort/", "FileItem/Sha1sum")) for t in terms)

    def test_report_to_dict_is_serialisable(self, kedr_profile):
        import json

        ioc = openioc.read(FIXTURES / "v11" / "sharpstomp.ioc")
        report = ProfileValidator(kedr_profile).validate(ioc)
        # Should not raise.
        as_dict = report.to_dict()
        json.dumps(as_dict)
        assert "violations" in as_dict
