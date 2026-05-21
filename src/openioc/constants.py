"""Namespace URIs and condition/operator enums shared across v1.0 and v1.1.

This module centralises the small set of literal values that appear in both
schema versions of OpenIOC so readers, writers, and the validator can refer
to them by name rather than by ad-hoc string literals.
"""

from enum import Enum

NS_V10 = "http://schemas.mandiant.com/2010/ioc"
"""XML namespace URI used by OpenIOC 1.0 documents (Mandiant)."""

NS_V11 = "http://openioc.org/schemas/OpenIOC_1.1"
"""XML namespace URI used by OpenIOC 1.1 documents (openioc.org)."""


class IndicatorOperator(str, Enum):
    """Boolean operator joining the children of an ``Indicator`` node.

    Both OpenIOC 1.0 and 1.1 use the same two-value vocabulary on the
    ``operator`` attribute of an ``Indicator`` element. Inherits from
    ``str`` so members serialise transparently as their string values.
    """

    AND = "AND"
    OR = "OR"


class Condition10(str, Enum):
    """Comparison conditions defined by the OpenIOC 1.0 specification.

    Used on ``IndicatorItem`` elements. The 1.0 schema declares the
    ``condition`` attribute as ``xs:string`` (it does not enforce a
    closed set), so this enum is used by
    :func:`openioc.validator.validate_10` to perform a programmatic
    check on top of XSD validation.
    """

    IS = "is"
    ISNOT = "isnot"
    CONTAINS = "contains"
    CONTAINSNOT = "containsnot"


class Condition11(str, Enum):
    """Comparison conditions defined by the OpenIOC 1.1 specification.

    Used on ``IndicatorItem`` elements. ``isnot`` and ``containsnot``
    were dropped in 1.1 and replaced by combining the positive
    condition with ``negate="true"`` on the item.
    """

    IS = "is"
    CONTAINS = "contains"
    MATCHES = "matches"
    STARTS_WITH = "starts-with"
    ENDS_WITH = "ends-with"
    GREATER_THAN = "greater-than"
    LESS_THAN = "less-than"


CONDITION10_VALUES = {c.value for c in Condition10}
"""Precomputed set of v1.0 condition strings, used by the validator."""

CONDITION11_VALUES = {c.value for c in Condition11}
"""Precomputed set of v1.1 condition strings, used by the validator."""
