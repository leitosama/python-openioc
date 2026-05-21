import uuid

import pytest

import openioc
from openioc.exceptions import ValidationError


# ── v1.0 validation ───────────────────────────────────────────────────────────

def test_validate_10_passes_on_valid(v10_full_ioc):
    openioc.validate_10(v10_full_ioc)  # should not raise


def test_validate_10_passes_minimal(v10_minimal_ioc):
    openioc.validate_10(v10_minimal_ioc)


def test_validate_10_missing_definition():
    ioc = openioc.IOC(id=str(uuid.uuid4()), format_version="1.0")
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert any("definition" in e.lower() for e in exc_info.value.errors)


def test_validate_10_missing_id():
    ioc = openioc.IOC(
        id="",
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
        ),
        format_version="1.0",
    )
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert any("id" in e.lower() for e in exc_info.value.errors)


def test_validate_10_invalid_condition():
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.OR,
            children=[
                openioc.IndicatorItem(
                    id=str(uuid.uuid4()),
                    context=openioc.Context("FileItem", "FileItem/FileName"),
                    content=openioc.Content("evil.exe"),
                    condition="matches",  # v1.1 only — invalid for v1.0
                )
            ],
        ),
        format_version="1.0",
    )
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert any("condition" in e.lower() for e in exc_info.value.errors)


def test_validate_10_missing_context_document():
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[
                openioc.IndicatorItem(
                    id=str(uuid.uuid4()),
                    context=openioc.Context(document="", search="FileItem/FileName"),
                    content=openioc.Content("evil.exe"),
                )
            ],
        ),
        format_version="1.0",
    )
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert any("document" in e.lower() for e in exc_info.value.errors)


def test_validate_10_accumulates_multiple_errors():
    ioc = openioc.IOC(
        id="",
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=openioc.IndicatorOperator.AND,
            children=[
                openioc.IndicatorItem(
                    id=str(uuid.uuid4()),
                    context=openioc.Context(document="", search=""),
                    content=openioc.Content(""),
                    condition="bad-condition",
                )
            ],
        ),
        format_version="1.0",
    )
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert len(exc_info.value.errors) > 1


def test_validate_10_source_format():
    ioc = openioc.IOC(id="", format_version="1.0")
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_10(ioc)
    assert exc_info.value.source_format == "1.0"


# ── v1.1 validation ───────────────────────────────────────────────────────────

def test_validate_11_passes_on_valid(simple_ioc):
    openioc.validate_11(simple_ioc)


def test_validate_11_passes_full(v11_full_ioc):
    openioc.validate_11(v11_full_ioc)


def test_validate_11_missing_definition():
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        format_version="1.1",
        last_modified="2024-01-01T00:00:00",
        published_date="2024-01-01T00:00:00",
    )
    with pytest.raises(ValidationError):
        openioc.validate_11(ioc)


def test_validate_11_source_format(simple_ioc):
    simple_ioc.id = ""
    with pytest.raises(ValidationError) as exc_info:
        openioc.validate_11(simple_ioc)
    assert exc_info.value.source_format == "1.1"


# ── dispatch ──────────────────────────────────────────────────────────────────

def test_validate_dispatches_10(v10_full_ioc):
    openioc.validate(v10_full_ioc)  # should not raise


def test_validate_dispatches_11(simple_ioc):
    openioc.validate(simple_ioc)  # should not raise
