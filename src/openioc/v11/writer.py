"""Serialiser for OpenIOC 1.1 documents.

The 1.1 writer is stricter than the 1.0 writer: every ``Indicator``,
``IndicatorItem``, and ``Parameter`` must have a non-empty ``id``, and
the root document must carry both ``last-modified`` and
``published-date`` (``IOC.created_date`` is accepted as a fallback for
both). Violations surface as :class:`WriteError` instead of producing
an XSD-invalid document.
"""

from __future__ import annotations

import os

from lxml import etree

from ..constants import NS_V11
from ..exceptions import WriteError
from ..models import IOC, Indicator, IndicatorItem, Link, Metadata, Parameter


class IOCv11Writer:
    """Serialiser for OpenIOC 1.1 documents (openioc.org namespace).

    Stateless; instances are cheap. Most callers should use
    :func:`openioc.write` rather than instantiating the writer
    directly.

    Attributes:
        NAMESPACE: The 1.1 namespace URI.
        NSMAP: Namespace map used on the root element. Declares only
            the default 1.1 namespace; unlike 1.0 there are no
            ``xsi`` / ``xsd`` declarations on the root.
    """

    NAMESPACE = NS_V11
    NSMAP: dict[str | None, str] = {None: NS_V11}

    def write_file(
        self,
        ioc: IOC,
        path: str | os.PathLike,
        *,
        pretty_print: bool = True,
    ) -> None:
        """Serialise ``ioc`` and write the XML to ``path``.

        Args:
            ioc: The IOC to serialise.
            path: Destination file path. Any existing file is
                overwritten.
            pretty_print: Indent the output for readability.

        Raises:
            WriteError: If a required field is missing (see
                :meth:`write_element` for the full list).
            OSError: If the file cannot be opened for writing.
        """
        data = self.write_string(ioc, pretty_print=pretty_print)
        with open(path, "wb") as fh:
            fh.write(data)

    def write_string(self, ioc: IOC, *, pretty_print: bool = True) -> bytes:
        """Serialise ``ioc`` to a UTF-8 bytes string.

        Args:
            ioc: The IOC to serialise.
            pretty_print: Indent the output for readability.

        Returns:
            UTF-8 XML bytes including the ``<?xml ... ?>`` declaration.

        Raises:
            WriteError: If a required field is missing.
        """
        root = self.write_element(ioc)
        return etree.tostring(
            root, pretty_print=pretty_print, xml_declaration=True, encoding="utf-8"
        )

    def write_element(self, ioc: IOC) -> etree._Element:
        """Build an :class:`lxml.etree._Element` for ``ioc``.

        Required fields (will raise :class:`WriteError` if missing):

        * ``ioc.id``
        * ``ioc.last_modified`` or ``ioc.created_date``
        * ``ioc.published_date`` or ``ioc.created_date``
        * ``ioc.definition``
        * ``id`` on every ``Indicator``, ``IndicatorItem``, and
          ``Parameter`` reachable from the document.

        Args:
            ioc: The IOC to serialise.

        Returns:
            Root ``<OpenIOC>`` element with the 1.1 namespace declared.

        Raises:
            WriteError: If any of the requirements above is not met.
        """
        root = etree.Element(self._tag("OpenIOC"), nsmap=self.NSMAP)  # type: ignore
        root.set("id", self._require_id(ioc.id, "IOC.id"))

        # OpenIOC 1.1 XSD declares last-modified/published-date as xs:dateTime,
        # so emitting empty strings produces a document that fails validation.
        # Prefer created_date as a fallback; raise if neither is populated.
        last_modified = ioc.last_modified or ioc.created_date
        if not last_modified:
            raise WriteError(
                "IOC.last_modified or IOC.created_date is required for v1.1 serialization"
            )
        published_date = ioc.published_date or ioc.created_date
        if not published_date:
            raise WriteError(
                "IOC.published_date or IOC.created_date is required for v1.1 serialization"
            )
        root.set("last-modified", last_modified)
        root.set("published-date", published_date)

        root.append(self._build_metadata(ioc.metadata))

        if ioc.definition is None:
            raise WriteError("IOC.definition must not be None for v1.1 serialization")
        criteria = etree.SubElement(root, self._tag("criteria"))
        criteria.append(self._build_indicator(ioc.definition))

        if ioc.parameters:
            root.append(self._build_parameters(ioc.parameters))

        return root

    def _tag(self, name: str) -> str:
        return f"{{{self.NAMESPACE}}}{name}"

    def _build_metadata(self, meta: Metadata) -> etree._Element:
        """Build the ``<metadata>`` wrapper element for v1.1.

        Unlike v1.0, all metadata fields live under a single
        ``<metadata>`` wrapper. ``<links>`` is emitted only when
        ``meta.links`` is non-empty.

        Args:
            meta: Metadata block to serialise.

        Returns:
            New ``<metadata>`` element. Not attached to a parent.
        """
        el = etree.Element(self._tag("metadata"))
        self._sub_text(el, "short_description", meta.short_description)
        self._sub_text(el, "description", meta.description)
        self._sub_text(el, "keywords", meta.keywords)
        self._sub_text(el, "authored_by", meta.authored_by)
        self._sub_text(el, "authored_date", meta.authored_date)
        if meta.links:
            links_el = etree.SubElement(el, self._tag("links"))
            for link in meta.links:
                self._build_link(links_el, link)
        return el

    def _build_link(self, parent: etree._Element, link: Link) -> None:
        """Append a ``<link>`` child to ``parent``.

        Args:
            parent: ``<links>`` container element.
            link: Link object to serialise.
        """
        el = etree.SubElement(parent, self._tag("link"))
        el.set("rel", link.rel)
        if link.href:
            el.set("href", link.href)
        if link.text:
            el.text = link.text

    def _build_indicator(self, indicator: Indicator) -> etree._Element:
        """Build an ``<Indicator>`` element, recursing into children.

        v1.1 requires every ``Indicator`` to have a non-empty ``id``.

        Args:
            indicator: Indicator node to serialise.

        Returns:
            New ``<Indicator>`` element. Not attached to a parent.

        Raises:
            WriteError: If ``indicator.id`` is empty.
        """
        el = etree.Element(self._tag("Indicator"))
        el.set("operator", indicator.operator.value)
        el.set("id", self._require_id(indicator.id, "Indicator.id"))
        if indicator.node_context is not None:
            el.set("node-context", indicator.node_context)
        for child in indicator.children:
            if isinstance(child, Indicator):
                el.append(self._build_indicator(child))
            elif isinstance(child, IndicatorItem):
                el.append(self._build_indicator_item(child))
        return el

    def _build_indicator_item(self, item: IndicatorItem) -> etree._Element:
        """Build an ``<IndicatorItem>`` element for v1.1.

        ``negate`` and ``preserve-case`` are always emitted (as
        ``"true"`` / ``"false"``) because the 1.1 XSD declares them
        as required attributes. The v1.0-only :attr:`IndicatorItem.comment`
        is silently dropped — 1.1 has no ``<Comment>`` element.

        Args:
            item: Indicator item to serialise.

        Returns:
            New ``<IndicatorItem>`` element. Not attached to a parent.

        Raises:
            WriteError: If ``item.id`` is empty.
        """
        el = etree.Element(self._tag("IndicatorItem"))
        el.set("id", self._require_id(item.id, "IndicatorItem.id"))
        el.set("condition", item.condition)
        el.set("preserve-case", "true" if item.preserve_case else "false")
        el.set("negate", "true" if item.negate else "false")

        ctx = etree.SubElement(el, self._tag("Context"))
        ctx.set("document", item.context.document)
        ctx.set("search", item.context.search)
        ctx.set("type", item.context.context_type)

        content = etree.SubElement(el, self._tag("Content"))
        content.set("type", item.content.content_type)
        content.text = item.content.value

        return el

    def _build_parameters(self, params: list[Parameter]) -> etree._Element:
        """Build the ``<parameters>`` block.

        Args:
            params: List of :class:`Parameter` to serialise.

        Returns:
            New ``<parameters>`` element. Not attached to a parent.

        Raises:
            WriteError: If any parameter has an empty ``id``.
        """
        el = etree.Element(self._tag("parameters"))
        for param in params:
            p = etree.SubElement(el, self._tag("param"))
            p.set("id", self._require_id(param.id, "Parameter.id"))
            p.set("ref-id", param.ref_id)
            p.set("name", param.name)
            v = etree.SubElement(p, self._tag("value"))
            v.set("type", param.value_type)
            v.text = param.value
        return el

    def _sub_text(self, parent: etree._Element, tag: str, text: str) -> None:
        el = etree.SubElement(parent, self._tag(tag))
        el.text = text

    def _require_id(self, value: str, context: str) -> str:
        if not value:
            raise WriteError(f"Missing required id for {context} in v1.1 serialization")
        return value
