"""Tests for ProfileValidator — one test per ViolationCode plus happy path."""

from __future__ import annotations

import uuid

import openioc
from openioc.profiles import Profile, ProfileValidator
from openioc.profiles.profile import StructureSpec, TermSpec
from openioc.profiles.report import Severity, ViolationCode


def _make_profile(**kwargs) -> Profile:
    defaults: dict = {
        "schema_version": "1.0.0",
        "name": "test",
        "terms": {
            "FileItem/FileName": TermSpec(operators=("is", "contains"), content_types=("string",)),
            "FileItem/Md5sum": TermSpec(operators=("is",), content_types=("md5",)),
        },
        "structure": StructureSpec(
            max_nesting=2,
            allow_or_at_top_level=False,
            allow_or_inside_and=False,
            allow_and_inside_or=True,
        ),
    }
    defaults.update(kwargs)
    return Profile(**defaults)


def _item(
    search="FileItem/FileName",
    document="FileItem",
    condition="is",
    content_type="string",
    value="evil.exe",
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


class TestHappyPath:
    def test_valid_ioc_empty_report(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("FileItem/FileName", condition="is")])
        report = ProfileValidator(profile).validate(ioc)
        assert not report.violations
        assert not report.has_errors()

    def test_empty_terms_allows_everything(self):
        profile = _make_profile(terms={})
        ioc = _ioc(children=[_item("Whatever/Term", condition="matches")])
        report = ProfileValidator(profile).validate(ioc)
        assert not report.violations

    def test_no_definition_gives_empty_report(self):
        profile = _make_profile()
        ioc = openioc.IOC(id=str(uuid.uuid4()), format_version="1.1")
        report = ProfileValidator(profile).validate(ioc)
        assert not report.violations


class TestUnsupportedTerm:
    def test_unknown_term_flagged(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("DnsEntryItem/Host", document="DnsEntryItem")])
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.UNSUPPORTED_TERM in codes

    def test_violation_has_term_in_details(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("DnsEntryItem/Host", document="DnsEntryItem")])
        report = ProfileValidator(profile).validate(ioc)
        v = report.by_code(ViolationCode.UNSUPPORTED_TERM)[0]
        assert v.details["term"] == "DnsEntryItem/Host"
        assert v.severity == Severity.ERROR


class TestInvalidOperator:
    def test_disallowed_condition_flagged(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("FileItem/FileName", condition="matches")])
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.INVALID_OPERATOR in codes

    def test_violation_details(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("FileItem/FileName", condition="matches")])
        report = ProfileValidator(profile).validate(ioc)
        v = report.by_code(ViolationCode.INVALID_OPERATOR)[0]
        assert v.details["operator"] == "matches"
        assert "is" in v.details["allowed_operators"]


class TestInvalidContentType:
    def test_disallowed_content_type_flagged(self):
        profile = _make_profile()
        # Md5sum only allows "md5"; "string" should fail.
        ioc = _ioc(
            children=[_item("FileItem/Md5sum", condition="is", content_type="string", value="abc")]
        )
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.INVALID_CONTENT_TYPE in codes

    def test_no_content_type_restriction_passes(self):
        profile = _make_profile(
            terms={"FileItem/FileName": TermSpec(operators=("is",), content_types=())}
        )
        ioc = _ioc(children=[_item("FileItem/FileName", content_type="anything")])
        report = ProfileValidator(profile).validate(ioc)
        assert not report.by_code(ViolationCode.INVALID_CONTENT_TYPE)


class TestMaxNesting:
    def test_exceeding_max_nesting(self):
        profile = _make_profile()  # max_nesting=2
        # depth=1: root, depth=2: child indicator, depth=3: grandchild indicator -> EXCEEDS
        grandchild_ind = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[_item()],
        )
        child_ind = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[grandchild_ind],
        )
        ioc = _ioc(children=[child_ind])
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.MAX_NESTING_EXCEEDED in codes

    def test_at_max_nesting_is_ok(self):
        profile = _make_profile()  # max_nesting=2
        child_ind = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[_item()],
        )
        ioc = _ioc(children=[child_ind])
        report = ProfileValidator(profile).validate(ioc)
        assert not report.by_code(ViolationCode.MAX_NESTING_EXCEEDED)


class TestOrAtTopLevel:
    def test_or_root_when_not_allowed(self):
        profile = _make_profile()  # allow_or_at_top_level=False
        ioc = _ioc(root_op=openioc.IndicatorOperator.OR, children=[_item()])
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.OR_NOT_ALLOWED_AT_TOP_LEVEL in codes

    def test_and_root_always_allowed(self):
        profile = _make_profile()
        ioc = _ioc(root_op=openioc.IndicatorOperator.AND, children=[_item()])
        report = ProfileValidator(profile).validate(ioc)
        assert not report.by_code(ViolationCode.OR_NOT_ALLOWED_AT_TOP_LEVEL)


class TestMixedOperators:
    def test_or_inside_and_when_not_allowed(self):
        profile = _make_profile()  # allow_or_inside_and=False
        or_child = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.OR,
            children=[_item()],
        )
        ioc = _ioc(root_op=openioc.IndicatorOperator.AND, children=[or_child])
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.MIXED_OPERATORS_NOT_ALLOWED in codes

    def test_and_inside_or_when_allowed(self):
        profile = _make_profile()  # allow_and_inside_or=True
        and_child = openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[_item()],
        )
        ioc = _ioc(root_op=openioc.IndicatorOperator.OR, children=[and_child])
        report = ProfileValidator(profile).validate(ioc)
        # OR at root is not allowed but AND inside OR is — only one violation
        assert not report.by_code(ViolationCode.MIXED_OPERATORS_NOT_ALLOWED)


class TestMultipleViolations:
    def test_all_violations_collected(self):
        profile = _make_profile()
        ioc = _ioc(
            children=[
                _item("FileItem/FileName", condition="matches"),  # INVALID_OPERATOR
                _item("DnsEntryItem/Host", document="DnsEntryItem"),  # UNSUPPORTED_TERM
            ]
        )
        report = ProfileValidator(profile).validate(ioc)
        codes = {v.code for v in report.violations}
        assert ViolationCode.INVALID_OPERATOR in codes
        assert ViolationCode.UNSUPPORTED_TERM in codes

    def test_report_to_dict(self):
        profile = _make_profile()
        ioc = _ioc(children=[_item("Unknown/Term", document="Unknown")])
        report = ProfileValidator(profile).validate(ioc)
        d = report.to_dict()
        assert isinstance(d["violations"], list)
        assert d["violations"][0]["code"] == "UNSUPPORTED_TERM"
