from __future__ import annotations

import copy
import uuid

from .models import IOC, Indicator, IndicatorItem
from .exceptions import ConversionError


def convert_10_to_11(ioc: IOC) -> IOC:
    """Return a new IOC in 1.1 format. The input is not mutated."""
    if ioc.format_version not in ("1.0", "1.1"):
        raise ConversionError(f"Unknown format_version: {ioc.format_version!r}")

    result = copy.deepcopy(ioc)
    result.format_version = "1.1"

    # map 1.0 date fields to 1.1 fields
    if not result.published_date:
        result.published_date = result.created_date
    if not result.last_modified:
        result.last_modified = result.created_date

    # ensure IOC-level id
    if not result.id:
        result.id = str(uuid.uuid4())

    # walk the indicator tree
    if result.definition is not None:
        result.definition = _convert_indicator(result.definition)

    return result


def _convert_indicator(indicator: Indicator) -> Indicator:
    if not indicator.id:
        indicator.id = str(uuid.uuid4())

    new_children = []
    for child in indicator.children:
        if isinstance(child, Indicator):
            new_children.append(_convert_indicator(child))
        elif isinstance(child, IndicatorItem):
            new_children.append(_convert_indicator_item(child))
        else:
            new_children.append(child)
    indicator.children = new_children
    return indicator


def _convert_indicator_item(item: IndicatorItem) -> IndicatorItem:
    if not item.id:
        item.id = str(uuid.uuid4())

    condition, negate = _convert_condition(item.condition)
    item.condition = condition
    item.negate = negate
    item.preserve_case = False
    return item


def _convert_condition(condition: str) -> tuple[str, bool]:
    """Map 1.0 condition strings to (1.1 condition, negate) pairs."""
    mapping = {
        "is": ("is", False),
        "isnot": ("is", True),
        "contains": ("contains", False),
        "containsnot": ("contains", True),
    }
    if condition in mapping:
        return mapping[condition]
    # 1.1-native conditions pass through unchanged
    return (condition, False)
