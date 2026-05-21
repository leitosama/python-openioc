import uuid

import pytest
from lxml import etree

import openioc
from openioc.constants import NS_V11, IndicatorOperator
from openioc.exceptions import WriteError


def test_write_returns_bytes(simple_ioc):
    data = openioc.write(simple_ioc)
    assert isinstance(data, bytes)
    assert b"<?xml" in data


def test_write_root_tag_openioc(simple_ioc):
    data = openioc.write(simple_ioc)
    root = etree.fromstring(data)
    assert etree.QName(root.tag).localname == "OpenIOC"


def test_write_namespace_present(simple_ioc):
    data = openioc.write(simple_ioc)
    assert NS_V11.encode() in data


def test_write_id_attribute(simple_ioc):
    data = openioc.write(simple_ioc)
    root = etree.fromstring(data)
    assert root.get("id") == simple_ioc.id


def test_write_last_modified_and_published(simple_ioc):
    data = openioc.write(simple_ioc)
    root = etree.fromstring(data)
    assert root.get("last-modified") == "2024-01-01T00:00:00"
    assert root.get("published-date") == "2024-01-01T00:00:00"


def test_write_indicator_item_attributes(simple_ioc):
    data = openioc.write(simple_ioc)
    root = etree.fromstring(data)
    ns = NS_V11
    items = root.findall(f".//{{{ns}}}IndicatorItem")
    assert len(items) == 1
    item = items[0]
    assert item.get("negate") == "false"
    assert item.get("preserve-case") == "false"
    assert item.get("condition") == "is"


def test_write_context_and_content(simple_ioc):
    data = openioc.write(simple_ioc)
    root = etree.fromstring(data)
    ns = NS_V11
    ctx = root.find(f".//{{{ns}}}Context")
    assert ctx is not None
    assert ctx.get("document") == "FileItem"
    assert ctx.get("search") == "FileItem/FileName"

    content = root.find(f".//{{{ns}}}Content")
    assert content is not None
    assert content.text == "evil.exe"


def test_write_parameters(v11_full_ioc):
    data = openioc.write(v11_full_ioc)
    root = etree.fromstring(data)
    ns = NS_V11
    params = root.find(f"{{{ns}}}parameters")
    assert params is not None
    param_list = list(params)
    assert len(param_list) == 2


def test_missing_indicator_id_raises():
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id="",
            operator=IndicatorOperator.OR,
        ),
        last_modified="2024-01-01T00:00:00",
        published_date="2024-01-01T00:00:00",
    )
    with pytest.raises(WriteError):
        openioc.write(ioc)


def test_missing_item_id_raises():
    ioc = openioc.IOC(
        id=str(uuid.uuid4()),
        definition=openioc.Indicator(
            id=str(uuid.uuid4()),
            operator=IndicatorOperator.OR,
            children=[
                openioc.IndicatorItem(
                    id="",
                    context=openioc.Context("FileItem", "FileItem/FileName"),
                    content=openioc.Content("x"),
                )
            ],
        ),
        last_modified="2024-01-01T00:00:00",
        published_date="2024-01-01T00:00:00",
    )
    with pytest.raises(WriteError):
        openioc.write(ioc)


def test_round_trip_v11_minimal(v11_minimal_path):
    ioc = openioc.read(v11_minimal_path)
    xml_bytes = openioc.write(ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    assert ioc.id == ioc2.id
    assert ioc.metadata.short_description == ioc2.metadata.short_description
    item1 = ioc.definition.children[0]
    item2 = ioc2.definition.children[0]
    assert item1.content.value == item2.content.value
    assert item1.condition == item2.condition


def test_round_trip_v11_full(v11_full_path):
    ioc = openioc.read(v11_full_path)
    xml_bytes = openioc.write(ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    assert ioc.id == ioc2.id
    assert len(ioc.parameters) == len(ioc2.parameters)
    assert ioc.parameters[0].value == ioc2.parameters[0].value


def test_write_to_file(tmp_path, simple_ioc):
    out = tmp_path / "test.ioc"
    result = openioc.write(simple_ioc, out)
    assert result is None
    assert out.exists()
    ioc2 = openioc.read(out, version="1.1")
    assert ioc2.id == simple_ioc.id


def test_write_none_definition_raises():
    ioc = openioc.IOC(id=str(uuid.uuid4()), format_version="1.1")
    with pytest.raises(WriteError):
        openioc.write(ioc)
