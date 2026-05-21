"""Serialiser for OpenIOC 1.0 documents.

Mirrors :mod:`openioc.v10.reader`. The writer is intentionally lenient
where the 1.0 schema is lenient: missing ``IOC.id`` is filled with a
fresh UUID, ``Indicator.id`` / ``IndicatorItem.id`` are emitted only when
non-empty, and 1.1-only fields (``negate``, ``preserve_case``,
``created_date``, ``published_date``, ``parameters``) are silently
ignored.
"""

from __future__ import annotations

import os
import uuid

from lxml import etree

from ..constants import NS_V10
from ..exceptions import WriteError
from ..models import IOC, Indicator, IndicatorItem, Link, Metadata


class IOCv10Writer:
    """Serialiser for OpenIOC 1.0 documents (Mandiant namespace).

    Stateless; instances are cheap. Most callers should use
    :func:`openioc.write` rather than instantiating the writer
    directly.

    Attributes:
        NAMESPACE: The Mandiant 1.0 namespace URI.
        NSMAP: Namespace map used on the root element. Declares the
            default 1.0 namespace plus the ``xsi`` and ``xsd``
            prefixes, mirroring what real-world 1.0 documents emit.
    """

    NAMESPACE = NS_V10
    NSMAP: dict[str | None, str] = {
        None: NS_V10,
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }

    def write_file(
        self,
        ioc: IOC,
        path: str | os.PathLike,
        *,
        pretty_print: bool = True,
    ) -> None:
        """Serialise ``ioc`` and write the XML to ``path``.

        Args:
            ioc: The IOC to serialise. Must have ``definition`` set.
            path: Destination file path. Any existing file is
                overwritten.
            pretty_print: Indent the output for readability.

        Raises:
            WriteError: If ``ioc.definition is None``.
            OSError: If the file cannot be opened for writing.
        """
        data = self.write_string(ioc, pretty_print=pretty_print)
        with open(path, "wb") as fh:
            fh.write(data)

    def write_string(self, ioc: IOC, *, pretty_print: bool = True) -> bytes:
        """Serialise ``ioc`` to a UTF-8 bytes string.

        Args:
            ioc: The IOC to serialise. Must have ``definition`` set.
            pretty_print: Indent the output for readability.

        Returns:
            UTF-8 XML bytes including the ``<?xml ... ?>`` declaration.

        Raises:
            WriteError: If ``ioc.definition is None``.
        """
        root = self.write_element(ioc)
        return etree.tostring(
            root, pretty_print=pretty_print, xml_declaration=True, encoding="utf-8"
        )

    def write_element(self, ioc: IOC) -> etree._Element:
        """Build an :class:`lxml.etree._Element` for ``ioc``.

        Useful when the caller wants to embed the IOC in a larger XML
        document or perform additional post-processing before
        serialising.

        Args:
            ioc: The IOC to serialise.

        Returns:
            Root ``<ioc>`` element with the 1.0 namespace declared.

        Raises:
            WriteError: If ``ioc.definition is None``.
        """
        root = etree.Element(self._tag("ioc"), nsmap=self.NSMAP)  # type: ignore[arg-type]
        root.set("id", self._ensure_id(ioc.id))
        if ioc.last_modified:
            root.set("last-modified", ioc.last_modified)

        self._write_metadata(root, ioc.metadata)

        if ioc.definition is None:
            raise WriteError("IOC.definition must not be None for v1.0 serialization")
        defn = etree.SubElement(root, self._tag("definition"))
        defn.append(self._build_indicator(ioc.definition))

        return root

    def _tag(self, name: str) -> str:
        return f"{{{self.NAMESPACE}}}{name}"

    def _write_metadata(self, root: etree._Element, meta: Metadata) -> None:
        """Append metadata fields as direct children of ``root``.

        Unlike v1.1, OpenIOC 1.0 has no ``<metadata>`` wrapper — the
        fields hang off the root ``<ioc>`` element directly.

        Args:
            root: Root ``<ioc>`` element to append children to.
            meta: Metadata block to serialise.
        """
        # Metadata fields are direct children of <ioc> — no <metadata> wrapper
        self._sub_text(root, "short_description", meta.short_description)
        self._sub_text(root, "description", meta.description)
        self._sub_text(root, "keywords", meta.keywords)
        self._sub_text(root, "authored_by", meta.authored_by)
        self._sub_text(root, "authored_date", meta.authored_date)
        links_el = etree.SubElement(root, self._tag("links"))
        for link in meta.links:
            self._build_link(links_el, link)

    def _build_link(self, parent: etree._Element, link: Link) -> None:
        """Append a ``<link>`` child to ``parent``.

        Emits ``href`` and text content only when non-empty so the
        output matches what real 1.0 documents look like.

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

        The ``id`` attribute is emitted only when non-empty; v1.0
        tolerates anonymous indicators.

        Args:
            indicator: Indicator node to serialise.

        Returns:
            New ``<Indicator>`` element. Not attached to a parent;
            the caller appends.
        """
        el = etree.Element(self._tag("Indicator"))
        el.set("operator", indicator.operator.value)
        if indicator.id:
            el.set("id", indicator.id)
        for child in indicator.children:
            if isinstance(child, Indicator):
                el.append(self._build_indicator(child))
            elif isinstance(child, IndicatorItem):
                el.append(self._build_indicator_item(child))
        return el

    def _build_indicator_item(self, item: IndicatorItem) -> etree._Element:
        """Build an ``<IndicatorItem>`` element for v1.0.

        The 1.1-only :attr:`IndicatorItem.negate` and
        :attr:`IndicatorItem.preserve_case` attributes are silently
        ignored. The :attr:`IndicatorItem.comment` field is emitted as
        a ``<Comment>`` child when non-empty.

        Args:
            item: Indicator item to serialise.

        Returns:
            New ``<IndicatorItem>`` element. Not attached to a parent.
        """
        el = etree.Element(self._tag("IndicatorItem"))
        if item.id:
            el.set("id", item.id)
        el.set("condition", item.condition)

        ctx = etree.SubElement(el, self._tag("Context"))
        ctx.set("document", item.context.document)
        ctx.set("search", item.context.search)
        ctx.set("type", item.context.context_type)

        content = etree.SubElement(el, self._tag("Content"))
        content.set("type", item.content.content_type)
        content.text = item.content.value

        if item.comment:
            comment_el = etree.SubElement(el, self._tag("Comment"))
            comment_el.text = item.comment

        return el

    def _sub_text(self, parent: etree._Element, tag: str, text: str) -> None:
        el = etree.SubElement(parent, self._tag(tag))
        el.text = text

    def _ensure_id(self, value: str) -> str:
        return value if value else str(uuid.uuid4())
