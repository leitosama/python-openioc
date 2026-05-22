"""Integration test: openioc-profile-example discovered via entry points.

Requires ``pip install -e profiles/example`` before running.
Skip gracefully if the package is not installed.
"""

from __future__ import annotations

import importlib.util

import pytest

from openioc.profiles.registry import _reset


@pytest.fixture(autouse=True)
def clean_registry():
    _reset()
    yield
    _reset()


@pytest.fixture(scope="module")
def example_installed():
    if importlib.util.find_spec("openioc_profile_example") is None:
        pytest.skip(
            "openioc-profile-example is not installed; run: pip install -e profiles/example"
        )


def test_example_profile_discovered(example_installed):
    pytest.importorskip("jsonschema")
    from openioc.profiles import get_profile, list_profiles

    names = list_profiles()
    assert "example" in names

    profile = get_profile("example")
    assert profile.name == "example"
    assert "FileItem/FileName" in profile.terms


def test_example_profile_validates_ioc(example_installed):
    pytest.importorskip("jsonschema")
    import uuid

    import openioc
    from openioc.profiles import ProfileValidator, get_profile

    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[
                openioc.IndicatorItem(
                    id=str(uuid.uuid4()),
                    context=openioc.Context(document="FileItem", search="FileItem/FileName"),
                    content=openioc.Content(value="evil.exe", content_type="string"),
                    condition="is",
                )
            ],
        ),
        format_version="1.1",
    )
    profile = get_profile("example")
    report = ProfileValidator(profile).validate(ioc)
    assert not report.has_errors()
