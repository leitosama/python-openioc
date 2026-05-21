"""python-openioc: Full CRUD support for OpenIOC 1.0 and 1.1."""

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
    """Parse an OpenIOC document.

    Auto-detects the version from the root element unless *version* is given.
    Accepts a file path, an XML string, or raw bytes.
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
    """Serialise an IOC to XML.

    If *dest* is None, returns bytes.
    If *dest* is a path, writes to file and returns None.
    *version* overrides ``ioc.format_version``.
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
    """Return '1.0' or '1.1' by peeking at the root element."""
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
