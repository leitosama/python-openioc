from __future__ import annotations

import functools
import importlib.resources

from lxml import etree

from .constants import CONDITION10_VALUES, CONDITION11_VALUES
from .exceptions import ValidationError
from .models import IOC, Indicator, IndicatorItem


def validate(ioc: IOC) -> None:
    """Validate an IOC. Raises ValidationError on failure."""
    if ioc.format_version == "1.0":
        validate_10(ioc)
    else:
        validate_11(ioc)


def validate_10(ioc: IOC) -> None:
    errors: list[str] = []

    if not ioc.id:
        errors.append("IOC.id is required")
    if ioc.definition is None:
        errors.append("IOC.definition (root Indicator) is required")
    else:
        _check_indicator_10(ioc.definition, errors)

    if errors:
        raise ValidationError(errors, source_format="1.0")


def validate_11(ioc: IOC) -> None:
    from .v11.writer import IOCv11Writer
    from .exceptions import WriteError

    errors: list[str] = []

    if not ioc.id:
        errors.append("IOC.id is required")
    if ioc.definition is None:
        errors.append("IOC.definition (root Indicator) is required")

    if errors:
        raise ValidationError(errors, source_format="1.1")

    try:
        writer = IOCv11Writer()
        element = writer.write_element(ioc)
    except WriteError as exc:
        raise ValidationError([str(exc)], source_format="1.1") from exc

    schema = _load_schema_11()
    if not schema.validate(element):
        schema_errors = [str(e) for e in schema.error_log.filter_from_errors()]
        raise ValidationError(schema_errors, source_format="1.1")


@functools.lru_cache(maxsize=1)
def _load_schema_11() -> etree.XMLSchema:
    pkg = importlib.resources.files("openioc.v11.schema")
    xsd_path = pkg.joinpath("ioc.xsd")
    with importlib.resources.as_file(xsd_path) as p:
        schema_doc = etree.parse(str(p))
    return etree.XMLSchema(schema_doc)


def _check_indicator_10(indicator: Indicator, errors: list[str]) -> None:
    if indicator.operator.value not in ("AND", "OR"):
        errors.append(f"Indicator {indicator.id!r}: invalid operator {indicator.operator!r}")

    for child in indicator.children:
        if isinstance(child, Indicator):
            _check_indicator_10(child, errors)
        elif isinstance(child, IndicatorItem):
            _check_indicator_item_10(child, errors)


def _check_indicator_item_10(item: IndicatorItem, errors: list[str]) -> None:
    if not item.context.document:
        errors.append(f"IndicatorItem {item.id!r}: Context.document is required")
    if not item.context.search:
        errors.append(f"IndicatorItem {item.id!r}: Context.search is required")
    if not item.content.value:
        errors.append(f"IndicatorItem {item.id!r}: Content.value is required")
    if item.condition not in CONDITION10_VALUES:
        errors.append(
            f"IndicatorItem {item.id!r}: condition {item.condition!r} is not valid for v1.0; "
            f"expected one of {sorted(CONDITION10_VALUES)}"
        )
