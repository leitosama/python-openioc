"""Tests for ProfileAdapter."""

from __future__ import annotations

import uuid

import pytest

import openioc
from openioc.profiles import AdapterPolicy, Profile, ProfileAdapter
from openioc.profiles.exceptions import AdaptationFailed
from openioc.profiles.profile import StructureSpec, TermSpec
from openioc.profiles.report import ViolationCode


def _make_profile(**kwargs) -> Profile:
    defaults: dict = {
        "schema_version": "1.0.0",
        "name": "test",
        "terms": {
            "FileItem/FileName": TermSpec(operators=("is", "contains"), content_types=("string",)),
            "FileItem/Md5sum": TermSpec(operators=("is",), content_types=("md5",)),
        },
        "structure": StructureSpec(max_nesting=3),
    }
    defaults.update(kwargs)
    return Profile(**defaults)


def _item(
    search="FileItem/FileName",
    document="FileItem",
    condition="is",
    content_type="string",
    value="test",
) -> openioc.IndicatorItem:
    return openioc.IndicatorItem(
        id=str(uuid.uuid4()),
        context=openioc.Context(document=document, search=search),
        content=openioc.Content(value=value, content_type=content_type),
        condition=condition,
    )


def _ioc(root_op=openioc.IndicatorOperator.AND, children=None) -> openioc.IOC:
    return openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=root_op,
            children=children or [],
        ),
        format_version="1.1",
    )


class TestDefaultPolicyNoop:
    def test_no_policy_returns_copy_with_violations(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("Unknown/Term", document="Unknown")])
        result = ProfileAdapter(profile).adapt(ioc)
        # IOC is a copy, not mutated.
        assert result.ioc is not ioc
        # Violations still present in residual.
        assert result.residual.has_errors()
        # No changes made.
        assert result.changes == []
        # Original IOC unchanged.
        assert len(ioc.definition.children) == 1  # type: ignore[union-attr]

    def test_valid_ioc_empty_changes_and_residual(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("FileItem/FileName")])
        result = ProfileAdapter(profile).adapt(ioc)
        assert result.changes == []
        assert not result.residual.has_errors()


class TestDropUnsupportedItems:
    def test_drops_unsupported_term(self):
        profile = _make_profile()
        good = _item("FileItem/FileName")
        bad = _item("DnsEntryItem/Host", document="DnsEntryItem")
        ioc = _ioc(children=[good, bad])

        result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
        assert len(result.changes) == 1
        assert result.changes[0].action == "DROPPED_ITEM"
        assert result.changes[0].details["term"] == "DnsEntryItem/Host"
        # Residual should be clean (only supported item remains).
        assert not result.residual.has_errors()
        # Original IOC not mutated.
        assert len(ioc.definition.children) == 2  # type: ignore[union-attr]

    def test_drops_invalid_operator(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("FileItem/FileName", condition="matches")])
        # The item has an invalid operator — dropped; tree becomes empty -> AdaptationFailed.
        with pytest.raises(AdaptationFailed):
            ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)

    def test_drops_invalid_content_type(self):
        profile = _make_profile()
        # Md5sum allows "md5" content_type only; using "string" should be dropped.
        ioc = _ioc(
            children=[
                _item("FileItem/FileName"),
                _item("FileItem/Md5sum", condition="is", content_type="string", value="abc"),
            ]
        )
        result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
        dropped = [c for c in result.changes if c.action == "DROPPED_ITEM"]
        assert len(dropped) == 1
        assert dropped[0].details["term"] == "FileItem/Md5sum"


class TestCollapseEmpty:
    def test_empty_sub_indicator_removed(self):
        profile = _make_profile()
        # Child indicator contains only an unsupported item.
        sub = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[_item("Unknown/Term", document="Unknown")],
        )
        ioc = _ioc(children=[_item("FileItem/FileName"), sub])

        result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
        # The sub-indicator should be collapsed away; one supported item remains.
        assert len(result.ioc.definition.children) == 1  # type: ignore[union-attr]
        assert not result.residual.has_errors()

    def test_entire_tree_unsupported_raises(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("Unknown/A", document="Unknown")])
        with pytest.raises(AdaptationFailed, match="nothing remains"):
            ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)


class TestStructuralViolationsNotFixed:
    def test_structural_violations_remain_in_residual(self):
        profile = _make_profile(
            structure=StructureSpec(
                max_nesting=1,
                allow_or_at_top_level=True,
                allow_or_inside_and=True,
                allow_and_inside_or=True,
            )
        )
        child_ind = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[_item("FileItem/FileName")],
        )
        ioc = _ioc(children=[child_ind])
        result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
        # Structural violation is still present; adapter does not fix it.
        assert result.residual.by_code(ViolationCode.MAX_NESTING_EXCEEDED)
