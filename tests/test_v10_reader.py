import pytest

import openioc
from openioc.constants import IndicatorOperator
from openioc.exceptions import ParseError
from openioc.v10.reader import IOCv10Reader


def test_read_minimal_from_file(v10_minimal_path):
    ioc = openioc.read(v10_minimal_path)
    assert ioc.id == "11111111-1111-1111-1111-111111111111"
    assert ioc.format_version == "1.0"
    assert ioc.metadata.short_description == "Minimal v1.0 IOC"
    assert ioc.metadata.authored_by == "Test Author"


def test_read_minimal_definition(v10_minimal_ioc):
    defn = v10_minimal_ioc.definition
    assert defn is not None
    assert defn.operator == IndicatorOperator.OR
    assert len(defn.children) == 1
    item = defn.children[0]
    assert isinstance(item, openioc.IndicatorItem)
    assert item.condition == "is"
    assert item.context.document == "FileItem"
    assert item.context.search == "FileItem/FileName"
    assert item.content.value == "evil.exe"


def test_read_full_nested_structure(v10_full_ioc):
    assert v10_full_ioc.id == "22222222-2222-2222-2222-222222222222"
    root = v10_full_ioc.definition
    assert root.operator == IndicatorOperator.OR
    assert len(root.children) == 2

    and1, and2 = root.children
    assert isinstance(and1, openioc.Indicator)
    assert and1.operator == IndicatorOperator.AND
    assert len(and1.children) == 2

    item1 = and1.children[0]
    assert item1.condition == "is"
    item2 = and1.children[1]
    assert item2.condition == "contains"

    and2_item1 = and2.children[0]
    assert and2_item1.condition == "isnot"
    and2_item2 = and2.children[1]
    assert and2_item2.condition == "containsnot"


def test_read_full_dates(v10_full_ioc):
    # v1.0 only carries last-modified; no created-date in the spec
    assert v10_full_ioc.last_modified == "2011-06-01T00:00:00"
    assert v10_full_ioc.created_date == ""


def test_read_full_links(v10_full_ioc):
    links = v10_full_ioc.metadata.links
    assert len(links) == 2
    assert links[0].rel == "reference"
    assert links[0].href == "https://example.com"
    assert links[1].rel == "case-id"


def test_read_from_string(v10_minimal_path):
    xml = v10_minimal_path.read_bytes()
    reader = IOCv10Reader()
    ioc = reader.read_string(xml)
    assert ioc.id == "11111111-1111-1111-1111-111111111111"


def test_read_string_and_file_equivalent(v10_minimal_path):
    from_file = openioc.read(v10_minimal_path)
    xml = v10_minimal_path.read_bytes()
    from_string = openioc.read(xml, version="1.0")
    assert from_file.id == from_string.id
    assert from_file.metadata.short_description == from_string.metadata.short_description


def test_malformed_raises_parse_error(v10_malformed_path):
    with pytest.raises(ParseError, match="definition"):
        openioc.read(v10_malformed_path)


def test_version_detected_as_10(v10_minimal_path):
    ioc = openioc.read(v10_minimal_path)
    assert ioc.format_version == "1.0"


def test_read_comment_in_indicator_item(v10_full_ioc):
    root = v10_full_ioc.definition
    and1 = root.children[0]
    assert isinstance(and1, openioc.Indicator)
    item_with_comment = and1.children[0]
    assert isinstance(item_with_comment, openioc.IndicatorItem)
    assert item_with_comment.comment == "Process name check"


def test_wrong_root_raises_parse_error():
    reader = IOCv10Reader()
    with pytest.raises(ParseError):
        reader.read_string(b"<notanioc/>")
