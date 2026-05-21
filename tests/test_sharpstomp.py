"""Tests for the real-world SHARPSTOMP (UTILITY) OpenIOC 1.1 fixture."""

import openioc
from openioc.constants import IndicatorOperator, NS_V11
from lxml import etree


def _all_items(node):
    """Recursively collect all IndicatorItem leaves from the indicator tree."""
    result = []
    for child in node.children:
        if isinstance(child, openioc.Indicator):
            result.extend(_all_items(child))
        elif isinstance(child, openioc.IndicatorItem):
            result.append(child)
    return result


# ---------------------------------------------------------------------------
# Reading — metadata
# ---------------------------------------------------------------------------

def test_sharpstomp_id(sharpstomp_ioc):
    assert sharpstomp_ioc.id == "7631f336-9f6d-4ca5-ad6a-def36d3ed327"


def test_sharpstomp_format_version(sharpstomp_ioc):
    assert sharpstomp_ioc.format_version == "1.1"


def test_sharpstomp_short_description(sharpstomp_ioc):
    assert sharpstomp_ioc.metadata.short_description == "SHARPSTOMP (UTILITY)"


def test_sharpstomp_authored_by(sharpstomp_ioc):
    assert sharpstomp_ioc.metadata.authored_by == "FireEye"


def test_sharpstomp_last_modified(sharpstomp_ioc):
    assert sharpstomp_ioc.last_modified == "2020-12-01T21:24:49Z"


def test_sharpstomp_published_date(sharpstomp_ioc):
    assert sharpstomp_ioc.published_date == "0001-01-01T00:00:00"


def test_sharpstomp_empty_parameters(sharpstomp_ioc):
    assert sharpstomp_ioc.parameters == []


def test_sharpstomp_empty_links(sharpstomp_ioc):
    assert sharpstomp_ioc.metadata.links == []


# ---------------------------------------------------------------------------
# Reading — indicator tree structure (exact positions known from source XML)
# ---------------------------------------------------------------------------

def test_sharpstomp_root_operator_or(sharpstomp_ioc):
    assert sharpstomp_ioc.definition.operator == IndicatorOperator.OR


def test_sharpstomp_root_id(sharpstomp_ioc):
    assert sharpstomp_ioc.definition.id == "9a6a8b2c-e975-4d48-92eb-8add55a98082"


def test_sharpstomp_root_has_four_children(sharpstomp_ioc):
    assert len(sharpstomp_ioc.definition.children) == 4


def test_sharpstomp_total_item_count(sharpstomp_ioc):
    assert len(_all_items(sharpstomp_ioc.definition)) == 6


def test_sharpstomp_top_level_children_types(sharpstomp_ioc):
    children = sharpstomp_ioc.definition.children
    assert isinstance(children[0], openioc.IndicatorItem)
    assert isinstance(children[1], openioc.IndicatorItem)
    assert isinstance(children[2], openioc.Indicator)
    assert isinstance(children[3], openioc.Indicator)


def test_sharpstomp_md5_items(sharpstomp_ioc):
    item0 = sharpstomp_ioc.definition.children[0]
    item1 = sharpstomp_ioc.definition.children[1]
    for item in (item0, item1):
        assert item.condition == "is"
        assert item.negate is False
        assert item.preserve_case is False
        assert item.content.value == "83ed748cd94576700268d35666bf3e01"
        assert item.content.content_type == "md5"
    assert item0.context.document == "fileWriteEvent"
    assert item0.context.search == "fileWriteEvent/md5"
    assert item1.context.document == "processEvent"
    assert item1.context.search == "processEvent/md5"


def test_sharpstomp_and_sub_indicator_fileevent(sharpstomp_ioc):
    and1 = sharpstomp_ioc.definition.children[2]
    assert isinstance(and1, openioc.Indicator)
    assert and1.operator == IndicatorOperator.AND
    assert len(and1.children) == 2

    fname_item = and1.children[0]
    assert fname_item.condition == "is"
    assert fname_item.content.value == "SharpStomp.exe"
    assert fname_item.context.search == "fileWriteEvent/fileName"
    assert fname_item.preserve_case is False

    mz_item = and1.children[1]
    assert mz_item.condition == "starts-with"
    assert mz_item.preserve_case is True
    assert mz_item.negate is False
    assert mz_item.content.value == "MZ"
    assert mz_item.context.search == "fileWriteEvent/textAtLowestOffset"


def test_sharpstomp_and_sub_indicator_processevent(sharpstomp_ioc):
    and2 = sharpstomp_ioc.definition.children[3]
    assert isinstance(and2, openioc.Indicator)
    assert and2.operator == IndicatorOperator.AND
    assert len(and2.children) == 2

    evt_item = and2.children[0]
    assert evt_item.condition == "is"
    assert evt_item.content.value == "Start"
    assert evt_item.context.search == "processEvent/eventType"

    proc_item = and2.children[1]
    assert proc_item.condition == "is"
    assert proc_item.content.value == "SharpStomp.exe"
    assert proc_item.context.search == "processEvent/process"


def test_sharpstomp_all_negate_false(sharpstomp_ioc):
    for item in _all_items(sharpstomp_ioc.definition):
        assert item.negate is False


def test_sharpstomp_starts_with_preserve_case(sharpstomp_ioc):
    mz_items = [i for i in _all_items(sharpstomp_ioc.definition) if i.condition == "starts-with"]
    assert len(mz_items) == 1
    assert mz_items[0].preserve_case is True
    assert mz_items[0].content.value == "MZ"


def test_sharpstomp_nested_and_operators(sharpstomp_ioc):
    and_nodes = [
        c for c in sharpstomp_ioc.definition.children
        if isinstance(c, openioc.Indicator) and c.operator == IndicatorOperator.AND
    ]
    assert len(and_nodes) == 2


# ---------------------------------------------------------------------------
# Modifying
# ---------------------------------------------------------------------------

def test_sharpstomp_modify_description(sharpstomp_ioc):
    sharpstomp_ioc.metadata.short_description = "Modified"
    assert sharpstomp_ioc.metadata.short_description == "Modified"


def test_sharpstomp_modify_md5_value(sharpstomp_ioc):
    item = sharpstomp_ioc.definition.children[0]
    assert isinstance(item, openioc.IndicatorItem)
    item.content.value = "deadbeefdeadbeefdeadbeefdeadbeef"
    assert item.content.value == "deadbeefdeadbeefdeadbeefdeadbeef"


def test_sharpstomp_add_indicator_item(sharpstomp_ioc):
    sharpstomp_ioc.definition.children.append(
        openioc.IndicatorItem(
            id="aaaaaaaa-0000-0000-0000-000000000001",
            context=openioc.Context("fileWriteEvent", "fileWriteEvent/fileName", "event"),
            content=openioc.Content("evil.exe"),
            condition="is",
        )
    )
    assert len(sharpstomp_ioc.definition.children) == 5


# ---------------------------------------------------------------------------
# Writing to v1.1
# ---------------------------------------------------------------------------

def test_sharpstomp_write_v11_returns_bytes(sharpstomp_ioc):
    data = openioc.write(sharpstomp_ioc)
    assert isinstance(data, bytes)
    assert b"<?xml" in data


def test_sharpstomp_write_root_tag_openioc(sharpstomp_ioc):
    data = openioc.write(sharpstomp_ioc)
    root = etree.fromstring(data)
    assert etree.QName(root.tag).localname == "OpenIOC"


def test_sharpstomp_write_v11_namespace(sharpstomp_ioc):
    data = openioc.write(sharpstomp_ioc)
    assert NS_V11.encode() in data


def test_sharpstomp_write_v11_id_attribute(sharpstomp_ioc):
    data = openioc.write(sharpstomp_ioc)
    root = etree.fromstring(data)
    assert root.get("id") == "7631f336-9f6d-4ca5-ad6a-def36d3ed327"


def test_sharpstomp_round_trip_v11(sharpstomp_ioc):
    xml_bytes = openioc.write(sharpstomp_ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    assert ioc2.id == sharpstomp_ioc.id
    assert ioc2.metadata.short_description == "SHARPSTOMP (UTILITY)"
    assert len(ioc2.definition.children) == 4
    assert len(_all_items(ioc2.definition)) == 6
    assert ioc2.parameters == []


def test_sharpstomp_round_trip_preserves_negate(sharpstomp_ioc):
    xml_bytes = openioc.write(sharpstomp_ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    for item in _all_items(ioc2.definition):
        assert item.negate is False


def test_sharpstomp_round_trip_preserve_case_true(sharpstomp_ioc):
    xml_bytes = openioc.write(sharpstomp_ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    mz_items = [i for i in _all_items(ioc2.definition) if i.condition == "starts-with"]
    assert len(mz_items) == 1
    assert mz_items[0].preserve_case is True


def test_sharpstomp_modified_round_trip_v11(sharpstomp_ioc):
    sharpstomp_ioc.metadata.short_description = "SHARPSTOMP MODIFIED"
    xml_bytes = openioc.write(sharpstomp_ioc)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    assert ioc2.metadata.short_description == "SHARPSTOMP MODIFIED"
    assert ioc2.id == sharpstomp_ioc.id


def test_sharpstomp_write_to_file(tmp_path, sharpstomp_ioc):
    out = tmp_path / "sharpstomp_out.ioc"
    result = openioc.write(sharpstomp_ioc, out)
    assert result is None
    assert out.exists()
    ioc2 = openioc.read(out, version="1.1")
    assert ioc2.id == sharpstomp_ioc.id
    assert len(_all_items(ioc2.definition)) == 6


def test_sharpstomp_xml_preserve_case_attribute(sharpstomp_ioc):
    data = openioc.write(sharpstomp_ioc)
    root = etree.fromstring(data)
    ns = NS_V11
    items = root.findall(f".//{{{ns}}}IndicatorItem")
    assert len(items) == 6
    sw_items = [el for el in items if el.get("condition") == "starts-with"]
    assert len(sw_items) == 1
    assert sw_items[0].get("preserve-case") == "true"
    non_sw_items = [el for el in items if el.get("condition") != "starts-with"]
    for el in non_sw_items:
        assert el.get("preserve-case") == "false"
