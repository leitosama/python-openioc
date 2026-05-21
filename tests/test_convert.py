import openioc
from openioc.convert import _convert_condition


def test_condition_mapping_is():
    cond, negate = _convert_condition("is")
    assert cond == "is"
    assert negate is False


def test_condition_mapping_isnot():
    cond, negate = _convert_condition("isnot")
    assert cond == "is"
    assert negate is True


def test_condition_mapping_contains():
    cond, negate = _convert_condition("contains")
    assert cond == "contains"
    assert negate is False


def test_condition_mapping_containsnot():
    cond, negate = _convert_condition("containsnot")
    assert cond == "contains"
    assert negate is True


def test_condition_passthrough_11_native():
    cond, negate = _convert_condition("matches")
    assert cond == "matches"
    assert negate is False


def test_convert_sets_format_version(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    assert result.format_version == "1.1"


def test_convert_does_not_mutate_input(v10_full_ioc):
    original_id = v10_full_ioc.id
    original_children_count = len(v10_full_ioc.definition.children)
    openioc.convert_10_to_11(v10_full_ioc)
    assert v10_full_ioc.format_version == "1.0"
    assert v10_full_ioc.id == original_id
    assert len(v10_full_ioc.definition.children) == original_children_count


def test_convert_maps_dates(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    # published_date should come from created_date (or existing published_date)
    assert result.published_date != ""
    assert result.last_modified != ""


def test_convert_minimal_dates(v10_minimal_ioc):
    result = openioc.convert_10_to_11(v10_minimal_ioc)
    # minimal fixture has created-date but no published-date
    assert result.published_date == v10_minimal_ioc.created_date


def test_convert_isnot_to_negate(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    root = result.definition
    and2 = root.children[1]
    item_isnot = and2.children[0]
    assert item_isnot.condition == "is"
    assert item_isnot.negate is True


def test_convert_containsnot_to_negate(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    root = result.definition
    and2 = root.children[1]
    item_containsnot = and2.children[1]
    assert item_containsnot.condition == "contains"
    assert item_containsnot.negate is True


def test_convert_adds_preserve_case(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    root = result.definition
    for child in root.children:
        if isinstance(child, openioc.Indicator):
            for item in child.children:
                if isinstance(item, openioc.IndicatorItem):
                    assert item.preserve_case is False


def test_convert_generates_missing_ids():
    ioc = openioc.IOC(
        id="",
        definition=openioc.Indicator(
            id="",
            operator=openioc.IndicatorOperator.OR,
            children=[
                openioc.IndicatorItem(
                    id="",
                    context=openioc.Context("FileItem", "FileItem/FileName"),
                    content=openioc.Content("evil.exe"),
                    condition="is",
                )
            ],
        ),
        format_version="1.0",
    )
    result = openioc.convert_10_to_11(ioc)
    assert result.id != ""
    assert result.definition.id != ""
    assert result.definition.children[0].id != ""


def test_convert_result_is_writable(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    xml = openioc.write(result)
    assert isinstance(xml, bytes)


def test_convert_result_is_validatable(v10_full_ioc):
    result = openioc.convert_10_to_11(v10_full_ioc)
    # should not raise
    openioc.validate(result)
