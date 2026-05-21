"""python-openioc: Full CRUD support for OpenIOC 1.0 and 1.1.

This module re-exports the public API of the library:

* Data model: :class:`IOC`, :class:`Indicator`, :class:`IndicatorItem`,
  :class:`Context`, :class:`Content`, :class:`Metadata`, :class:`Link`,
  :class:`Parameter`.
* Enums: :class:`IndicatorOperator`, :class:`Condition10`, :class:`Condition11`.
* Exceptions: :class:`OpenIOCError` (base), :class:`ParseError`,
  :class:`ValidationError`, :class:`ConversionError`, :class:`WriteError`.
* Functions: :func:`read`, :func:`write`, :func:`convert_10_to_11`,
  :func:`validate`, :func:`validate_10`, :func:`validate_11`.
"""

from __future__ import annotations

import io
import os

from lxml import etree

from .constants import Condition10, Condition11, IndicatorOperator
from .convert import convert_10_to_11
from .exceptions import ConversionError, OpenIOCError, ParseError, ValidationError, WriteError
from .models import (
    IOC,
    Content,
    Context,
    Indicator,
    IndicatorItem,
    Link,
    Metadata,
    Parameter,
)
from .validator import validate, validate_10, validate_11

__all__ = [
    # core types
    "IOC",
    "Indicator",
    "IndicatorItem",
    "Context",
    "Content",
    "Metadata",
    "Link",
    "Parameter",
    # enums / constants
    "IndicatorOperator",
    "Condition10",
    "Condition11",
    # exceptions
    "OpenIOCError",
    "ParseError",
    "ValidationError",
    "ConversionError",
    "WriteError",
    # functions
    "read",
    "write",
    "convert_10_to_11",
    "validate",
    "validate_10",
    "validate_11",
]


def read(
    source: str | bytes | os.PathLike,
    *,
    version: str | None = None,
) -> IOC:
    """Parse an OpenIOC document into an :class:`IOC` object.

    When ``version`` is left as ``None``, the format is auto-detected by
    peeking at the root element of the document: a ``<OpenIOC>`` root
    is parsed as 1.1, anything else is parsed as 1.0.

    Args:
        source: Path to a file, an XML string (must start with ``<``
            after leading whitespace), or raw XML bytes. ``os.PathLike``
            instances are always treated as file paths.
        version: ``"1.0"`` or ``"1.1"`` to force a parser; ``None`` to
            auto-detect.

    Returns:
        Parsed :class:`IOC`. The returned object's ``format_version``
        attribute reflects which parser actually ran.

    Raises:
        ParseError: If the XML is malformed, the root element is
            unexpected for the chosen version, or a required element is
            missing.
        OSError: If ``source`` is a file path that cannot be opened.
    """
    if version == "1.0":
        return _read_v10(source)
    if version == "1.1":
        return _read_v11(source)

    # auto-detect by peeking at the root tag
    detected = _detect_version(source)
    if detected == "1.0":
        return _read_v10(source)
    return _read_v11(source)


def write(
    ioc: IOC,
    dest: str | os.PathLike | None = None,
    *,
    version: str | None = None,
    pretty_print: bool = True,
) -> bytes | None:
    """Serialise an :class:`IOC` to OpenIOC XML.

    Args:
        ioc: The IOC to serialise. Must have ``definition`` set.
        dest: Output file path, or ``None`` to return the XML as bytes.
        version: ``"1.0"`` or ``"1.1"`` to override ``ioc.format_version``.
            Any other value behaves like ``"1.1"``.
        pretty_print: If ``True``, the output is indented for human
            readability.

    Returns:
        UTF-8 XML bytes (including the XML declaration) when ``dest is
        None``; otherwise ``None`` after the file has been written.

    Raises:
        WriteError: If the IOC lacks required fields for the target
            format (for example a missing ``id`` on an ``Indicator`` in
            1.1, or a missing date on the root document in 1.1).
        OSError: If ``dest`` cannot be written.
    """
    target = version or ioc.format_version
    if dest is None:
        if target == "1.0":
            from .v10.writer import IOCv10Writer

            return IOCv10Writer().write_string(ioc, pretty_print=pretty_print)
        from .v11.writer import IOCv11Writer

        return IOCv11Writer().write_string(ioc, pretty_print=pretty_print)
    if target == "1.0":
        from .v10.writer import IOCv10Writer

        IOCv10Writer().write_file(ioc, dest, pretty_print=pretty_print)
    else:
        from .v11.writer import IOCv11Writer

        IOCv11Writer().write_file(ioc, dest, pretty_print=pretty_print)
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_version(source: str | bytes | os.PathLike) -> str:
    """Detect the OpenIOC format version of ``source``.

    Uses :func:`lxml.etree.iterparse` so only the root element is
    consumed; the rest of the document is not loaded. The detection
    rule is simple:

    * ``<OpenIOC>`` root -> ``"1.1"``
    * any other root (in practice ``<ioc>``) -> ``"1.0"``

    Args:
        source: Same shape as for :func:`read`.

    Returns:
        ``"1.0"`` or ``"1.1"``. Defaults to ``"1.1"`` for an empty
        document (no root element seen).
    """
    if isinstance(source, os.PathLike) or (
        isinstance(source, str) and not source.lstrip().startswith("<")
    ):
        # treat as file path
        ctx = etree.iterparse(str(source), events=("start",), resolve_entities=False)
    else:
        raw = source if isinstance(source, bytes) else source.encode()
        ctx = etree.iterparse(io.BytesIO(raw), events=("start",), resolve_entities=False)

    for _event, elem in ctx:
        local = etree.QName(elem.tag).localname
        if local == "OpenIOC":
            return "1.1"
        return "1.0"

    return "1.1"


def _read_v10(source: str | bytes | os.PathLike) -> IOC:
    from .v10.reader import IOCv10Reader

    reader = IOCv10Reader()
    if _is_file(source):
        return reader.read_file(source)  # type: ignore[arg-type]
    return reader.read_string(source)  # type: ignore[arg-type]


def _read_v11(source: str | bytes | os.PathLike) -> IOC:
    from .v11.reader import IOCv11Reader

    reader = IOCv11Reader()
    if _is_file(source):
        return reader.read_file(source)  # type: ignore[arg-type]
    return reader.read_string(source)  # type: ignore[arg-type]


def _is_file(source: str | bytes | os.PathLike) -> bool:
    if isinstance(source, bytes):
        return False
    s = str(source)
    return not s.lstrip().startswith("<")
