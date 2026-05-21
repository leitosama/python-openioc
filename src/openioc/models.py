"""Dataclasses representing the OpenIOC object model.

The model is deliberately version-agnostic: the same dataclasses are used
to round-trip both OpenIOC 1.0 and 1.1 documents. Per-version concerns
(which fields are valid, which attributes are required) live in the
corresponding reader/writer modules under :mod:`openioc.v10` and
:mod:`openioc.v11`.

Convention:
    Optional string fields use an empty string (``""``) as their "not
    set" sentinel rather than ``None``. This keeps serialisation
    straightforward (writers emit attributes only when truthy) and
    matches how the underlying XML attributes are presented as empty
    strings by ``lxml`` when absent. Code that needs to distinguish
    "explicitly empty" from "not provided" should check truthiness
    rather than ``is None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import IndicatorOperator


@dataclass
class Context:
    """Location at which to evaluate an :class:`IndicatorItem`.

    Corresponds to the ``<Context>`` element inside an
    ``<IndicatorItem>``. Tells the host agent which document type to
    inspect and which field within that document to compare against the
    item's :class:`Content`.

    Attributes:
        document: Document type name (for example ``"FileItem"`` or
            ``"DnsEntryItem"``).
        search: XPath-like reference to the field being searched (for
            example ``"FileItem/FileName"``).
        context_type: Value of the XML ``type`` attribute. Renamed in
            Python because ``type`` is a builtin. Defaults to ``"mir"``
            (Mandiant Intelligent Response), the only common value in
            either schema.
    """

    document: str
    search: str
    context_type: str = "mir"  # XML attribute is named "type"


@dataclass
class Content:
    """Literal value an :class:`IndicatorItem` compares against.

    Corresponds to the ``<Content>`` element inside an
    ``<IndicatorItem>``.

    Attributes:
        value: The literal string the item matches against (for example
            a SHA-1 hash, a domain name, or a path fragment).
        content_type: Value of the XML ``type`` attribute (renamed in
            Python because ``type`` is a builtin). Common values are
            ``"string"``, ``"int"``, ``"md5"``, ``"sha1"``, ``"sha256"``.
    """

    value: str
    content_type: str = "string"  # XML attribute is named "type"


@dataclass
class IndicatorItem:
    """Leaf node in the indicator tree — an atomic match condition.

    An ``IndicatorItem`` says: *in document `context.document`, look at
    field `context.search`; if its value satisfies `condition` relative
    to `content.value`, the item matches.*

    Attributes:
        id: Unique identifier for the item. Required in v1.1; tolerated
            empty in v1.0 (writer omits the attribute in that case).
        context: Where to look.
        content: What to match against.
        condition: Comparison operator. Valid values depend on the
            target format — see :class:`openioc.constants.Condition10`
            and :class:`openioc.constants.Condition11`.
        negate: v1.1 only. ``True`` inverts the match result. Silently
            ignored by the v1.0 writer.
        preserve_case: v1.1 only. ``True`` makes the comparison
            case-sensitive. Silently ignored by the v1.0 writer.
        comment: v1.0 ``<Comment>`` child element text. Silently ignored
            by the v1.1 writer.
    """

    id: str
    context: Context
    content: Content
    condition: str = "is"
    negate: bool = False  # 1.1 only; v1.0 writer ignores this
    preserve_case: bool = False  # 1.1 only; v1.0 writer ignores this
    comment: str = ""  # v1.0 <Comment>; v1.1 writer ignores this


@dataclass
class Indicator:
    """Internal node in the indicator tree — a boolean combinator.

    An ``Indicator`` joins its children with the given
    :class:`~openioc.constants.IndicatorOperator` (``AND`` or ``OR``).
    Children can themselves be ``Indicator`` instances (nested logic)
    or :class:`IndicatorItem` leaves; the heterogeneous list mirrors
    the OpenIOC XML structure exactly.

    Attributes:
        id: Unique identifier for the node. Required in v1.1; tolerated
            empty in v1.0 (writer omits the attribute in that case).
        operator: ``AND`` or ``OR``. Defaults to ``AND``.
        node_context: v1.1 only. Optional ``node-context`` attribute
            that scopes the child evaluation to a particular host /
            agent context. ``None`` means the attribute is omitted.
        children: Mixed list of ``Indicator`` and ``IndicatorItem``
            objects. Order is preserved on round-trip.
    """

    id: str
    operator: IndicatorOperator = IndicatorOperator.AND
    node_context: str | None = None  # 1.1 only
    children: list[Indicator | IndicatorItem] = field(default_factory=list)


@dataclass
class Link:
    """External reference inside :class:`Metadata.links`.

    Maps to the ``<link>`` element in both 1.0 and 1.1.

    Attributes:
        rel: Relationship type (for example ``"report"`` or
            ``"category"``). Required.
        href: Optional URL. Emitted as the ``href`` attribute when
            non-empty.
        text: Optional human-readable label. Emitted as the element's
            text content when non-empty.
    """

    rel: str
    href: str = ""
    text: str = ""


@dataclass
class Metadata:
    """Bibliographic information about an :class:`IOC`.

    The 1.0 schema places these fields as direct children of the root
    ``<ioc>`` element; 1.1 wraps them in a ``<metadata>`` element. The
    in-memory model is identical for both.

    Attributes:
        short_description: One-line summary of the IOC.
        description: Free-form longer description.
        keywords: Comma- or space-separated tags.
        authored_by: Name of the author / organisation.
        authored_date: Authoring timestamp (typically ISO 8601).
        links: External references attached to the IOC.
    """

    short_description: str = ""
    description: str = ""
    keywords: str = ""
    authored_by: str = ""
    authored_date: str = ""
    links: list[Link] = field(default_factory=list)


@dataclass
class Parameter:
    """Named parameter attached to an indicator (OpenIOC 1.1 only).

    Parameters allow tooling-specific metadata to be hung off an
    ``Indicator`` or ``IndicatorItem`` by id. The schema does not
    constrain the meaning of individual parameters.

    Attributes:
        id: Unique identifier for the parameter element itself.
        ref_id: ``id`` of the ``Indicator`` or ``IndicatorItem`` this
            parameter applies to.
        name: Parameter name.
        value: Parameter value as a literal string.
        value_type: XSD-style type hint (``"string"``, ``"int"``,
            ``"bool"``, etc.). Stored as the ``type`` attribute on the
            nested ``<value>`` element.
    """

    id: str
    ref_id: str
    name: str
    value: str = ""
    value_type: str = "string"


@dataclass
class IOC:
    """Top-level OpenIOC document.

    The same dataclass represents both 1.0 and 1.1 documents; the
    ``format_version`` attribute selects which serialiser
    :func:`openioc.write` and the validator will use.

    Attributes:
        id: Document identifier. Required for serialisation in both
            versions; the v1.0 writer will fill in a UUID if empty.
        metadata: Bibliographic information.
        definition: Root :class:`Indicator` of the criteria tree. A
            document with ``definition is None`` cannot be serialised
            or validated.
        parameters: v1.1-only parameter list. Ignored by the v1.0
            writer.
        created_date: Authoring timestamp. Not in the v1.0 spec; used
            as a fallback for the v1.1 ``last-modified`` and
            ``published-date`` attributes when those are unset.
        last_modified: Last-modified timestamp. Present in both
            schemas as the ``last-modified`` attribute on the root
            element.
        published_date: v1.1-only ``published-date`` attribute.
        format_version: ``"1.0"`` or ``"1.1"``. Determines which
            serialiser :func:`openioc.write` and which validator
            :func:`openioc.validate` dispatch to.
    """

    id: str
    metadata: Metadata = field(default_factory=Metadata)
    definition: Indicator | None = None
    parameters: list[Parameter] = field(default_factory=list)
    created_date: str = ""  # not in v1.0 spec; used for v1.1 and conversion
    last_modified: str = ""  # 1.0/1.1: last-modified attribute
    published_date: str = ""  # 1.1: published-date
    format_version: str = "1.1"
