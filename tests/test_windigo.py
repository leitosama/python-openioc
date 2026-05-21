"""Tests for the real-world Operation Windigo OpenIOC 1.0 fixture."""

from lxml import etree

import openioc
from openioc.constants import IndicatorOperator


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

def test_windigo_id(windigo_ioc):
    assert windigo_ioc.id == "ec3b97c8-5de7-444d-9bd9-8f868ca04748"


def test_windigo_format_version(windigo_ioc):
    assert windigo_ioc.format_version == "1.0"


def test_windigo_short_description(windigo_ioc):
    assert windigo_ioc.metadata.short_description == "Operation Windigo"


def test_windigo_authored_by(windigo_ioc):
    assert windigo_ioc.metadata.authored_by == "David Westcott"


def test_windigo_last_modified(windigo_ioc):
    assert windigo_ioc.last_modified == "2014-03-21T15:58:14"


def test_windigo_authored_date(windigo_ioc):
    assert windigo_ioc.metadata.authored_date == "2014-03-18T20:23:23"


def test_windigo_description_contains_report_url(windigo_ioc):
    assert "welivesecurity.com" in windigo_ioc.metadata.description


# ---------------------------------------------------------------------------
# Reading — indicator tree
# ---------------------------------------------------------------------------

def test_windigo_definition_not_none(windigo_ioc):
    assert windigo_ioc.definition is not None


def test_windigo_root_operator(windigo_ioc):
    assert windigo_ioc.definition.operator == IndicatorOperator.OR


def test_windigo_many_indicator_items(windigo_ioc):
    assert len(_all_items(windigo_ioc.definition)) >= 100


def test_windigo_all_conditions_are_v10_valid(windigo_ioc):
    valid = {"is", "isnot", "contains", "containsnot"}
    for item in _all_items(windigo_ioc.definition):
        assert item.condition in valid


def test_windigo_has_ip_indicator(windigo_ioc):
    values = {i.content.value for i in _all_items(windigo_ioc.definition)}
    assert "77.67.80.31" in values


def test_windigo_has_sha1_indicator(windigo_ioc):
    values = {i.content.value for i in _all_items(windigo_ioc.definition)}
    assert "98cdbf1e0d202f5948552cebaa9f0315b7a3731d" in values


def test_windigo_has_domain_indicator(windigo_ioc):
    values = {i.content.value for i in _all_items(windigo_ioc.definition)}
    assert "k2l8z1yeodm.info" in values


# ---------------------------------------------------------------------------
# Modifying
# ---------------------------------------------------------------------------

def test_windigo_modify_description(windigo_ioc):
    original_count = len(_all_items(windigo_ioc.definition))
    windigo_ioc.metadata.short_description = "Updated"
    assert windigo_ioc.metadata.short_description == "Updated"
    assert len(_all_items(windigo_ioc.definition)) == original_count


def test_windigo_add_indicator_item(windigo_ioc):
    before = len(windigo_ioc.definition.children)
    windigo_ioc.definition.children.append(
        openioc.IndicatorItem(
            id="aaaaaaaa-0000-0000-0000-000000000001",
            context=openioc.Context("Network", "Network/DNS"),
            content=openioc.Content("evil.example.com"),
            condition="is",
        )
    )
    assert len(windigo_ioc.definition.children) == before + 1


# ---------------------------------------------------------------------------
# Writing to v1.0
# ---------------------------------------------------------------------------

def test_windigo_write_v10_returns_bytes(windigo_ioc):
    data = openioc.write(windigo_ioc, version="1.0")
    assert isinstance(data, bytes)
    assert b"<?xml" in data


def test_windigo_write_v10_root_tag(windigo_ioc):
    data = openioc.write(windigo_ioc, version="1.0")
    root = etree.fromstring(data)
    assert etree.QName(root.tag).localname == "ioc"


def test_windigo_write_v10_namespace(windigo_ioc):
    data = openioc.write(windigo_ioc, version="1.0")
    assert b"schemas.mandiant.com/2010/ioc" in data
    assert b"openioc.org" not in data


def test_windigo_write_v10_id_attribute(windigo_ioc):
    data = openioc.write(windigo_ioc, version="1.0")
    root = etree.fromstring(data)
    assert root.get("id") == "ec3b97c8-5de7-444d-9bd9-8f868ca04748"


def test_windigo_round_trip_v10(windigo_ioc):
    xml_bytes = openioc.write(windigo_ioc, version="1.0")
    ioc2 = openioc.read(xml_bytes, version="1.0")
    assert ioc2.id == windigo_ioc.id
    assert ioc2.metadata.short_description == windigo_ioc.metadata.short_description
    assert ioc2.metadata.authored_by == windigo_ioc.metadata.authored_by


def test_windigo_round_trip_preserves_item_count(windigo_ioc):
    original_count = len(_all_items(windigo_ioc.definition))
    xml_bytes = openioc.write(windigo_ioc, version="1.0")
    ioc2 = openioc.read(xml_bytes, version="1.0")
    assert len(_all_items(ioc2.definition)) == original_count


def test_windigo_modified_round_trip_v10(windigo_ioc):
    windigo_ioc.metadata.short_description = "Modified Windigo"
    xml_bytes = openioc.write(windigo_ioc, version="1.0")
    ioc2 = openioc.read(xml_bytes, version="1.0")
    assert ioc2.metadata.short_description == "Modified Windigo"
    assert ioc2.id == windigo_ioc.id


# ---------------------------------------------------------------------------
# Converting to v1.1
# ---------------------------------------------------------------------------

def test_windigo_convert_format_version(windigo_ioc):
    result = openioc.convert_10_to_11(windigo_ioc)
    assert result.format_version == "1.1"


def test_windigo_convert_preserves_id(windigo_ioc):
    result = openioc.convert_10_to_11(windigo_ioc)
    assert result.id == windigo_ioc.id


def test_windigo_convert_preserves_metadata(windigo_ioc):
    result = openioc.convert_10_to_11(windigo_ioc)
    assert result.metadata.short_description == windigo_ioc.metadata.short_description
    assert result.metadata.authored_by == windigo_ioc.metadata.authored_by


def test_windigo_convert_preserves_item_count(windigo_ioc):
    original_count = len(_all_items(windigo_ioc.definition))
    result = openioc.convert_10_to_11(windigo_ioc)
    assert len(_all_items(result.definition)) == original_count


def test_windigo_convert_does_not_mutate_input(windigo_ioc):
    original_version = windigo_ioc.format_version
    openioc.convert_10_to_11(windigo_ioc)
    assert windigo_ioc.format_version == original_version


def test_windigo_convert_result_validatable(windigo_ioc):
    result = openioc.convert_10_to_11(windigo_ioc)
    openioc.validate(result)


def test_windigo_convert_result_writable_as_v11(windigo_ioc):
    result = openioc.convert_10_to_11(windigo_ioc)
    data = openioc.write(result)
    assert isinstance(data, bytes)
    root = etree.fromstring(data)
    assert etree.QName(root.tag).localname == "OpenIOC"


def test_windigo_convert_round_trip_v11(windigo_ioc):
    original_count = len(_all_items(windigo_ioc.definition))
    converted = openioc.convert_10_to_11(windigo_ioc)
    xml_bytes = openioc.write(converted)
    ioc2 = openioc.read(xml_bytes, version="1.1")
    assert ioc2.id == windigo_ioc.id
    assert len(_all_items(ioc2.definition)) == original_count


def test_windigo_convert_all_conditions_v11_valid(windigo_ioc):
    valid = {"is", "contains", "matches", "starts-with", "ends-with", "greater-than", "less-than"}
    result = openioc.convert_10_to_11(windigo_ioc)
    for item in _all_items(result.definition):
        assert item.condition in valid
