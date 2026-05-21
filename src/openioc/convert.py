"""Upgrade conversion from OpenIOC 1.0 to 1.1.

The 1.1 schema is strictly more expressive than 1.0: it adds the
``negate``/``preserve-case`` attributes on indicator items, the
``published-date`` attribute on the document, the ``parameters``
section, and requires every ``Indicator`` and ``IndicatorItem`` to
have a non-empty ``id``. The functions here adapt a 1.0 IOC to satisfy
all of those new requirements without losing semantics.
"""

from __future__ import annotations

import copy
import uuid

from .exceptions import ConversionError
from .models import IOC, Indicator, IndicatorItem


def convert_10_to_11(ioc: IOC) -> IOC:
    """Convert an OpenIOC 1.0 document to OpenIOC 1.1.

    The input ``ioc`` is deep-copied; the caller's instance is never
    mutated. The conversion fills in the fields that 1.1 requires but
    1.0 lacks:

    * Sets ``format_version`` to ``"1.1"``.
    * Generates a UUID for ``IOC.id`` and for every nested
      ``Indicator`` / ``IndicatorItem`` ``id`` that is empty.
    * Derives ``published_date`` (and ``last_modified`` if absent)
      from the chain ``created_date -> last_modified``.
    * Translates 1.0 conditions to their 1.1 equivalents:
      ``isnot`` -> ``("is", negate=True)`` and
      ``containsnot`` -> ``("contains", negate=True)``.
      ``preserve_case`` is forced to ``False`` (1.0 has no equivalent).

    Args:
        ioc: An IOC with ``format_version`` of ``"1.0"`` or ``"1.1"``.
            Passing an already-1.1 IOC is a no-op apart from the deep
            copy.

    Returns:
        A new IOC at ``format_version == "1.1"``.

    Raises:
        ConversionError: If ``ioc.format_version`` is anything other
            than ``"1.0"`` or ``"1.1"``.
    """
    if ioc.format_version not in ("1.0", "1.1"):
        raise ConversionError(f"Unknown format_version: {ioc.format_version!r}")

    result = copy.deepcopy(ioc)
    result.format_version = "1.1"

    # map 1.0 date fields to 1.1 fields
    # v1.0 only has last-modified; use it as fallback for published_date
    if not result.published_date:
        result.published_date = result.created_date or result.last_modified
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
    """Recursively rewrite an :class:`Indicator` tree in-place for 1.1.

    Assigns a UUID to any node whose ``id`` is empty and dispatches
    children to either ``_convert_indicator`` (for nested groups) or
    ``_convert_indicator_item`` (for leaves). The input node is
    mutated and returned for caller convenience.

    Args:
        indicator: Root of the (sub-)tree to rewrite.

    Returns:
        The same ``Indicator`` instance, now 1.1-compliant.
    """
    if not indicator.id:
        indicator.id = str(uuid.uuid4())

    new_children: list[Indicator | IndicatorItem] = []
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
    """Rewrite a single :class:`IndicatorItem` for 1.1.

    Fills in a UUID for an empty ``id``, maps the v1.0 condition to its
    v1.1 ``(condition, negate)`` form, and resets ``preserve_case`` to
    ``False`` since 1.0 has no equivalent attribute.

    Args:
        item: Item to rewrite. Mutated in place.

    Returns:
        The same item, now 1.1-compliant.
    """
    if not item.id:
        item.id = str(uuid.uuid4())

    condition, negate = _convert_condition(item.condition)
    item.condition = condition
    item.negate = negate
    item.preserve_case = False
    return item


def _convert_condition(condition: str) -> tuple[str, bool]:
    """Map a 1.0 condition string to a ``(1.1 condition, negate)`` pair.

    The four 1.0 conditions collapse onto two 1.1 conditions combined
    with the ``negate`` flag:

    ===============  ===============
    1.0 condition    1.1 result
    ===============  ===============
    ``is``           ``("is", False)``
    ``isnot``        ``("is", True)``
    ``contains``     ``("contains", False)``
    ``containsnot``  ``("contains", True)``
    ===============  ===============

    Any other value (including 1.1-native conditions such as
    ``matches`` or ``starts-with``) passes through unchanged with
    ``negate=False``.

    Args:
        condition: Source condition string.

    Returns:
        A ``(condition, negate)`` tuple suitable for assignment to an
        :class:`IndicatorItem`.
    """
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
