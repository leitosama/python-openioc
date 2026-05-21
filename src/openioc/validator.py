from __future__ import annotations

import functools
import importlib.resources

from lxml import etree

from .exceptions import ValidationError
from .models import IOC


def validate(ioc: IOC) -> None:
    """Validate an IOC. Raises ValidationError on failure."""
    if ioc.format_version == "1.0":
        validate_10(ioc)
    else:
        validate_11(ioc)


def validate_10(ioc: IOC) -> None:
    from .exceptions import WriteError
    from .v10.writer import IOCv10Writer

    errors: list[str] = []

    if not ioc.id:
        errors.append("IOC.id is required")
    if ioc.definition is None:
        errors.append("IOC.definition (root Indicator) is required")

    if errors:
        raise ValidationError(errors, source_format="1.0")

    try:
        element = IOCv10Writer().write_element(ioc)
    except WriteError as exc:
        raise ValidationError([str(exc)], source_format="1.0") from exc

    schema = _load_schema_10()
    if not schema.validate(element):
        raise ValidationError([str(schema.error_log)], source_format="1.0")


def validate_11(ioc: IOC) -> None:
    from .exceptions import WriteError
    from .v11.writer import IOCv11Writer

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
        raise ValidationError([str(schema.error_log)], source_format="1.1")


@functools.lru_cache(maxsize=1)
def _load_schema_10() -> etree.XMLSchema:
    pkg = importlib.resources.files("openioc.v10.schema")
    xsd_path = pkg.joinpath("ioc.xsd")
    with importlib.resources.as_file(xsd_path) as p:
        schema_doc = etree.parse(str(p))
    return etree.XMLSchema(schema_doc)


@functools.lru_cache(maxsize=1)
def _load_schema_11() -> etree.XMLSchema:
    pkg = importlib.resources.files("openioc.v11.schema")
    xsd_path = pkg.joinpath("ioc.xsd")
    with importlib.resources.as_file(xsd_path) as p:
        schema_doc = etree.parse(str(p))
    return etree.XMLSchema(schema_doc)
