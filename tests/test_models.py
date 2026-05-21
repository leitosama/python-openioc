import dataclasses
import uuid

import openioc
from openioc.constants import Condition10, Condition11, IndicatorOperator


def test_indicator_operator_values():
    assert IndicatorOperator.AND.value == "AND"
    assert IndicatorOperator.OR.value == "OR"


def test_condition10_values():
    values = {c.value for c in Condition10}
    assert values == {"is", "isnot", "contains", "containsnot"}


def test_condition11_values():
    values = {c.value for c in Condition11}
    assert "matches" in values
    assert "starts-with" in values
    assert "ends-with" in values
    assert "greater-than" in values
    assert "less-than" in values


def test_context_defaults():
    ctx = openioc.Context(document="FileItem", search="FileItem/FileName")
    assert ctx.context_type == "mir"


def test_content_defaults():
    c = openioc.Content(value="hello")
    assert c.content_type == "string"


def test_indicator_item_defaults():
    item = openioc.IndicatorItem(
        id=str(uuid.uuid4()),
        context=openioc.Context("FileItem", "FileItem/FileName"),
        content=openioc.Content("evil.exe"),
    )
    assert item.condition == "is"
    assert item.negate is False
    assert item.preserve_case is False


def test_indicator_defaults():
    ind = openioc.Indicator(id=str(uuid.uuid4()))
    assert ind.operator == IndicatorOperator.AND
    assert ind.children == []
    assert ind.node_context is None


def test_metadata_defaults():
    meta = openioc.Metadata()
    assert meta.short_description == ""
    assert meta.links == []


def test_ioc_defaults():
    ioc = openioc.IOC(id=str(uuid.uuid4()))
    assert ioc.format_version == "1.1"
    assert ioc.definition is None
    assert ioc.parameters == []


def test_ioc_is_mutable():
    ioc = openioc.IOC(id="x")
    ioc.format_version = "1.0"
    assert ioc.format_version == "1.0"


def test_dataclass_asdict():
    ioc = openioc.IOC(id="x", metadata=openioc.Metadata(short_description="test"))
    d = dataclasses.asdict(ioc)
    assert d["id"] == "x"
    assert d["metadata"]["short_description"] == "test"
