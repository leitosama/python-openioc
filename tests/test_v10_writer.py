import uuid

import pytest
from lxml import etree

import openioc
from openioc.constants import IndicatorOperator
from openioc.exceptions import WriteError

NS = "http://schemas.mandiant.com/2010/ioc"


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def test_write_returns_bytes(simple_ioc):
    simple_ioc.format_version = "1.0"
    data = openioc.write(simple_ioc, version="1.0")
    assert isinstance(data, bytes)
    assert b"<?xml" in data


def test_write_root_tag_is_ioc(simple_ioc):
    data = openioc.write(simple_ioc, version="1.0")
    root = etree.fromstring(data)
    assert etree.QName(root.tag).localname == "ioc"


def test_write_mandiant_namespace(simple_ioc):
    data = openioc.write(simple_ioc, version="1.0")
    assert b"schemas.mandiant.com/2010/ioc" in data
    assert b"openioc.org" not in data


def test_write_id_attribute(simple_ioc):
    data = openioc.write(simple_ioc, version="1.0")
    root = etree.fromstring(data)
    assert root.get("id") == simple_ioc.id


def test_write_last_modified_attribute(v10_full_ioc):
    data = openioc.write(v10_full_ioc, version="1.0")
    root = etree.fromstring(data)
    assert root.get("last-modified") == "2011-06-01T00:00:00"


def test_write_no_created_date(simple_ioc):
    simple_ioc.format_version = "1.0"
    data = openioc.write(simple_ioc, version="1.0")
    root = etree.fromstring(data)
    assert root.get("created-date") is None


def test_missing_id_auto_generated():
    item = openioc.IndicatorItem(
        id="",
        context=openioc.Context("FileItem", "FileItem/FileName"),
        content=openioc.Content("evil.exe"),
    )
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=IndicatorOperator.OR,
            children=[item],
        ),
        format_version="1.0",
    )
    data = openioc.write(ioc, version="1.0")
    root = etree.fromstring(data)
    ii = root.find(f".//{_tag('IndicatorItem')}")
    assert ii is not None
    gen_id = ii.get("id")
    assert gen_id and gen_id != ""


def test_round_trip_v10(v10_minimal_path):
    ioc = openioc.read(v10_minimal_path)
    xml_bytes = openioc.write(ioc, version="1.0")
    ioc2 = openioc.read(xml_bytes, version="1.0")
    assert ioc.id == ioc2.id
    assert ioc.metadata.short_description == ioc2.metadata.short_description
    item1 = ioc.definition.children[0]
    item2 = ioc2.definition.children[0]
    assert item1.content.value == item2.content.value
    assert item1.condition == item2.condition


def test_round_trip_full_v10(v10_full_path):
    ioc = openioc.read(v10_full_path)
    xml_bytes = openioc.write(ioc, version="1.0")
    ioc2 = openioc.read(xml_bytes, version="1.0")
    assert ioc.id == ioc2.id
    assert len(ioc.definition.children) == len(ioc2.definition.children)


def test_write_to_file(tmp_path, simple_ioc):
    out = tmp_path / "test.ioc"
    simple_ioc.format_version = "1.0"
    result = openioc.write(simple_ioc, out, version="1.0")
    assert result is None
    assert out.exists()
    ioc2 = openioc.read(out, version="1.0")
    assert ioc2.id == simple_ioc.id


def test_write_none_definition_raises():
    ioc = openioc.IOC(id=str(uuid.uuid4()), format_version="1.0")
    with pytest.raises(WriteError):
        openioc.write(ioc, version="1.0")


def test_write_metadata_fields(v10_full_ioc):
    xml_bytes = openioc.write(v10_full_ioc, version="1.0")
    root = etree.fromstring(xml_bytes)
    # Metadata fields are direct children of root — no <metadata> wrapper
    sd = root.find(_tag("short_description"))
    assert sd is not None and sd.text == "Full v1.0 IOC"
    desc = root.find(_tag("description"))
    assert desc is not None and desc.text == "Tests all conditions and nested AND/OR logic"


def test_write_comment_in_indicator_item(v10_full_ioc):
    xml_bytes = openioc.write(v10_full_ioc, version="1.0")
    root = etree.fromstring(xml_bytes)
    comment = root.find(f".//{_tag('Comment')}")
    assert comment is not None and comment.text == "Process name check"
