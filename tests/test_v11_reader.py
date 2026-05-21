import pytest

import openioc
from openioc.constants import IndicatorOperator
from openioc.exceptions import ParseError
from openioc.v11.reader import IOCv11Reader


def test_read_minimal_from_file(v11_minimal_path):
    ioc = openioc.read(v11_minimal_path)
    assert ioc.id == "44444444-4444-4444-4444-444444444444"
    assert ioc.format_version == "1.1"


def test_read_minimal_metadata(v11_minimal_ioc):
    assert v11_minimal_ioc.metadata.short_description == "Minimal v1.1 IOC"
    assert v11_minimal_ioc.metadata.authored_by == "Test Author"


def test_read_minimal_definition(v11_minimal_ioc):
    defn = v11_minimal_ioc.definition
    assert defn is not None
    assert defn.operator == IndicatorOperator.OR
    assert len(defn.children) == 1
    item = defn.children[0]
    assert isinstance(item, openioc.IndicatorItem)
    assert item.id == "dddd0001-0000-0000-0000-000000000001"
    assert item.condition == "is"
    assert item.negate is False
    assert item.preserve_case is False


def test_read_full_nested(v11_full_ioc):
    root = v11_full_ioc.definition
    assert root.operator == IndicatorOperator.OR
    assert len(root.children) == 2

    and1, and2 = root.children
    assert and1.operator == IndicatorOperator.AND

    # negate and preserve-case
    item_negate = and1.children[1]
    assert item_negate.negate is True
    assert item_negate.preserve_case is True

    # 1.1 conditions
    and2_item1 = and2.children[0]
    assert and2_item1.condition == "matches"
    and2_item2 = and2.children[1]
    assert and2_item2.condition == "greater-than"


def test_read_full_dates(v11_full_ioc):
    assert v11_full_ioc.last_modified == "2013-06-01T00:00:00"
    assert v11_full_ioc.published_date == "2013-01-01T00:00:00"


def test_read_full_links(v11_full_ioc):
    links = v11_full_ioc.metadata.links
    assert len(links) == 1
    assert links[0].rel == "reference"
    assert links[0].href == "https://example.com"


def test_read_parameters(v11_full_ioc):
    params = v11_full_ioc.parameters
    assert len(params) == 2
    assert params[0].name == "confidence"
    assert params[0].value == "high"
    assert params[0].ref_id == "dddd0002-0000-0000-0000-000000000001"
    assert params[1].name == "data-marking"
    assert params[1].value == "TLP:AMBER"


def test_read_from_string(v11_minimal_path):
    xml = v11_minimal_path.read_bytes()
    reader = IOCv11Reader()
    ioc = reader.read_string(xml)
    assert ioc.id == "44444444-4444-4444-4444-444444444444"


def test_read_string_and_file_equivalent(v11_minimal_path):
    from_file = openioc.read(v11_minimal_path)
    from_string = openioc.read(v11_minimal_path.read_bytes(), version="1.1")
    assert from_file.id == from_string.id


def test_malformed_missing_criteria(v11_malformed_path):
    with pytest.raises(ParseError, match="criteria"):
        openioc.read(v11_malformed_path)


def test_version_detected_as_11(v11_minimal_path):
    ioc = openioc.read(v11_minimal_path)
    assert ioc.format_version == "1.1"


def test_wrong_root_raises_parse_error():
    reader = IOCv11Reader()
    with pytest.raises(ParseError):
        reader.read_string(b"<ioc/>")


def test_content_type_preserved(v11_full_ioc):
    root = v11_full_ioc.definition
    and1 = root.children[0]
    md5_item = and1.children[0]
    assert md5_item.content.content_type == "md5"
    assert md5_item.content.value == "d41d8cd98f00b204e9800998ecf8427e"
