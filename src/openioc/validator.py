"""Structural and XSD-schema validation for IOC models.

Validation has two layers:

* Structural pre-check — confirms required Python-side invariants
  (``IOC.id`` set, ``IOC.definition`` present) so the caller gets a
  helpful error before the schema validator is invoked.
* XSD validation — serialises the IOC with the appropriate writer and
  runs it through the embedded OpenIOC XSD (1.0 or 1.1) shipped under
  :mod:`openioc.v10.schema` and :mod:`openioc.v11.schema`.

The v1.0 XSD declares the ``condition`` attribute as ``xs:string``
rather than an enumeration, so the validator additionally checks that
each ``IndicatorItem.condition`` is one of the four 1.0 values.
"""

from __future__ import annotations

import functools
import importlib.resources

from lxml import etree

from .exceptions import ValidationError
from .models import IOC, Indicator, IndicatorItem


def validate(ioc: IOC) -> None:
    """Validate an IOC against its declared format.

    Dispatches to :func:`validate_10` or :func:`validate_11` based on
    ``ioc.format_version``. Any value other than ``"1.0"`` is treated
    as 1.1.

    Args:
        ioc: The IOC to validate.

    Raises:
        ValidationError: If structural or XSD validation fails.
    """
    if ioc.format_version == "1.0":
        validate_10(ioc)
    else:
        validate_11(ioc)


def validate_10(ioc: IOC) -> None:
    """Validate an IOC against the OpenIOC 1.0 schema.

    The check runs in three stages, and stops at the first failing
    stage (errors are not accumulated across stages):

    1. Structural: ``IOC.id`` and ``IOC.definition`` must be set.
    2. Programmatic: every ``IndicatorItem.condition`` must be one of
       the values in :data:`openioc.constants.CONDITION10_VALUES`
       (because the 1.0 XSD declares the attribute as ``xs:string``).
    3. XSD: the IOC is serialised via :class:`openioc.v10.writer.IOCv10Writer`
       and validated against the bundled ``ioc.xsd``.

    Args:
        ioc: The IOC to validate.

    Raises:
        ValidationError: If any stage fails. ``ValidationError.errors``
            holds the human-readable findings and
            ``ValidationError.source_format`` is ``"1.0"``.
    """
    from .exceptions import WriteError
    from .v10.writer import IOCv10Writer

    errors: list[str] = []

    if not ioc.id:
        errors.append("IOC.id is required")
    if ioc.definition is None:
        errors.append("IOC.definition (root Indicator) is required")

    if errors:
        raise ValidationError(errors, source_format="1.0")

    # narrowed: pre-check above guarantees definition is not None
    assert ioc.definition is not None

    # XSD leaves condition as xs:string; check v1.0 values programmatically
    condition_errors: list[str] = []
    _check_conditions_10(ioc.definition, condition_errors)
    if condition_errors:
        raise ValidationError(condition_errors, source_format="1.0")

    try:
        element = IOCv10Writer().write_element(ioc)
    except WriteError as exc:
        raise ValidationError([str(exc)], source_format="1.0") from exc

    schema = _load_schema_10()
    if not schema.validate(element):
        raise ValidationError([str(schema.error_log)], source_format="1.0")


def validate_11(ioc: IOC) -> None:
    """Validate an IOC against the OpenIOC 1.1 schema.

    Runs the structural pre-check, then serialises with
    :class:`openioc.v11.writer.IOCv11Writer` and validates against the
    bundled 1.1 XSD. Unlike :func:`validate_10` there is no separate
    condition pre-check — the 1.1 XSD enumerates valid conditions
    itself.

    Args:
        ioc: The IOC to validate.

    Raises:
        ValidationError: If structural or XSD validation fails.
            ``source_format`` is ``"1.1"``.
    """
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
    """Load the bundled OpenIOC 1.0 XSD.

    Cached so the schema document is parsed only once per process.

    Returns:
        Compiled :class:`lxml.etree.XMLSchema` for OpenIOC 1.0.
    """
    pkg = importlib.resources.files("openioc.v10.schema")
    xsd_path = pkg.joinpath("ioc.xsd")
    with importlib.resources.as_file(xsd_path) as p:
        schema_doc = etree.parse(str(p))
    return etree.XMLSchema(schema_doc)


def _check_conditions_10(node: Indicator, errors: list[str]) -> None:
    """Recursively check that all conditions are valid 1.0 conditions.

    Walks the indicator tree rooted at ``node``. For every
    :class:`~openioc.models.IndicatorItem` whose ``condition`` is not
    one of the 1.0 vocabulary entries, appends a descriptive message
    to ``errors`` (the function does not raise — the caller decides
    when to raise once all errors are collected).

    Args:
        node: Root indicator of the subtree to inspect.
        errors: Accumulator list; new findings are appended in place.
    """
    from .constants import CONDITION10_VALUES

    for child in node.children:
        if isinstance(child, Indicator):
            _check_conditions_10(child, errors)
        elif isinstance(child, IndicatorItem) and child.condition not in CONDITION10_VALUES:
            errors.append(
                f"IndicatorItem {child.id!r}: condition {child.condition!r} "
                f"is not valid for v1.0; expected one of {sorted(CONDITION10_VALUES)}"
            )


@functools.lru_cache(maxsize=1)
def _load_schema_11() -> etree.XMLSchema:
    """Load the bundled OpenIOC 1.1 XSD.

    Cached so the schema document is parsed only once per process.

    Returns:
        Compiled :class:`lxml.etree.XMLSchema` for OpenIOC 1.1.
    """
    pkg = importlib.resources.files("openioc.v11.schema")
    xsd_path = pkg.joinpath("ioc.xsd")
    with importlib.resources.as_file(xsd_path) as p:
        schema_doc = etree.parse(str(p))
    return etree.XMLSchema(schema_doc)
