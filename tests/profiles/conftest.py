"""Shared fixtures for the profiles engine tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import openioc
from openioc.profiles import Profile

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def synthetic_profile_path() -> Path:
    return FIXTURES / "profiles" / "synthetic.json"


@pytest.fixture
def synthetic_profile(synthetic_profile_path) -> Profile:
    pytest.importorskip("jsonschema")
    return Profile.from_file(synthetic_profile_path)


def _make_item(
    search: str = "FileItem/FileName",
    document: str = "FileItem",
    condition: str = "is",
    content_type: str = "string",
    value: str = "evil.exe",
) -> openioc.IndicatorItem:
    return openioc.IndicatorItem(
        id=str(uuid.uuid4()),
        context=openioc.Context(document=document, search=search),
        content=openioc.Content(value=value, content_type=content_type),
        condition=condition,
    )


def _make_ioc(root_operator=openioc.IndicatorOperator.AND, children=None) -> openioc.IOC:
    return openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=root_operator,
            children=children or [],
        ),
        format_version="1.1",
    )


@pytest.fixture
def make_item():
    return _make_item


@pytest.fixture
def make_ioc():
    return _make_ioc


@pytest.fixture
def valid_ioc(make_item, make_ioc) -> openioc.IOC:
    """An IOC that is fully valid against the synthetic profile."""
    return make_ioc(children=[make_item("FileItem/FileName", condition="is")])


@pytest.fixture
def unsupported_term_ioc(make_item, make_ioc) -> openioc.IOC:
    """An IOC with a term not listed in the synthetic profile."""
    return make_ioc(
        children=[
            make_item("FileItem/FileName", condition="is"),
            make_item("DnsEntryItem/Host", document="DnsEntryItem", condition="is"),
        ]
    )
