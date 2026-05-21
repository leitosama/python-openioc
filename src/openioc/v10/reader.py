"""Parser for OpenIOC 1.0 documents.

OpenIOC 1.0 places metadata fields as direct children of the root
``<ioc>`` element (no ``<metadata>`` wrapper) and uses a ``<definition>``
element to introduce the criteria tree. Both differences are handled
here so the parsed :class:`~openioc.models.IOC` looks the same in
memory as one parsed from 1.1.
"""

from __future__ import annotations

import os
import uuid

from lxml import etree

from ..constants import IndicatorOperator
from ..exceptions import ParseError
from ..models import IOC, Content, Context, Indicator, IndicatorItem, Link, Metadata

# Hardened parser: disable external-entity resolution, network access, and huge-tree
# expansion to mitigate XXE and billion-laughs attacks against untrusted OpenIOC input.
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)


class IOCv10Reader:
    """Parser for OpenIOC 1.0 documents (Mandiant namespace).

    Stateless aside from the shared module-level hardened parser, so
    instances are cheap to create. Most callers should use
    :func:`openioc.read` rather than instantiating the reader
    directly.
    """

    def read_file(self, path: str | os.PathLike) -> IOC:
        """Parse an OpenIOC 1.0 document from a file path.

        Args:
            path: Path to the XML file.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.0"``.

        Raises:
            ParseError: If the file's contents are not valid 1.0 XML.
            OSError: If the file cannot be opened.
        """
        try:
            tree = etree.parse(str(path), _PARSER)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML in {path}: {exc}") from exc
        return self.read_element(tree.getroot())

    def read_string(self, src: str | bytes) -> IOC:
        """Parse an OpenIOC 1.0 document from an in-memory string.

        Args:
            src: XML content as ``str`` (encoded to UTF-8 internally)
                or raw ``bytes``.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.0"``.

        Raises:
            ParseError: If the content is not valid 1.0 XML.
        """
        if isinstance(src, str):
            src = src.encode()
        try:
            root = etree.fromstring(src, _PARSER)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML: {exc}") from exc
        return self.read_element(root)

    def read_element(self, root: etree._Element) -> IOC:
        """Parse an already-parsed XML element.

        Useful when the caller already has an :class:`lxml.etree._Element`
        in hand (for example after running their own custom parsing
        pipeline).

        Args:
            root: Element expected to be an OpenIOC 1.0 ``<ioc>`` root.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.0"``.

        Raises:
            ParseError: If ``root`` is not a ``<ioc>`` element or the
                document is missing required structure.
        """
        tag = etree.QName(root.tag).localname.lower()
        if tag != "ioc":
            raise ParseError(f"Expected root element <ioc>, got <{root.tag}>")
        return self._parse_ioc(root)

    def _parse_ioc(self, el: etree._Element) -> IOC:
        """Build an :class:`IOC` from the root ``<ioc>`` element.

        Metadata fields are direct children of ``<ioc>`` in v1.0 (no
        wrapper element), so this method walks ``el``'s children and
        populates the :class:`~openioc.models.Metadata` and indicator
        tree inline.

        Args:
            el: The root ``<ioc>`` element.

        Returns:
            Populated :class:`IOC` at ``format_version == "1.0"``.

        Raises:
            ParseError: If the document has no ``<definition>``.
        """
        ioc_id = el.get("id", "")
        # Real OpenIOC 1.0 uses "last-modified"; no created-date or published-date
        last_modified = el.get("last-modified", "")

        meta = Metadata()
        definition = None

        for child in el:
            if not isinstance(child.tag, str):  # skip XML comments / PIs
                continue
            local = etree.QName(child.tag).localname.lower()
            text = (child.text or "").strip()
            if local == "short_description":
                meta.short_description = text
            elif local == "description":
                meta.description = text
            elif local == "keywords":
                meta.keywords = text
            elif local == "authored_by":
                meta.authored_by = text
            elif local == "authored_date":
                meta.authored_date = text
            elif local == "links":
                meta.links = self._parse_links(child)
            elif local == "definition":
                definition = self._parse_definition(child)

        if definition is None:
            raise ParseError("Missing required <definition> element in IOC 1.0 document")

        return IOC(
            id=ioc_id,
            metadata=meta,
            definition=definition,
            last_modified=last_modified,
            format_version="1.0",
        )

    def _parse_links(self, el: etree._Element) -> list[Link]:
        """Parse a ``<links>`` container into a list of :class:`Link`.

        Args:
            el: ``<links>`` element.

        Returns:
            List of :class:`Link` objects in document order.
        """
        links = []
        for child in el:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child.tag).localname.lower()
            if local == "link":
                links.append(
                    Link(
                        rel=child.get("rel", ""),
                        href=child.get("href", ""),
                        text=(child.text or "").strip(),
                    )
                )
        return links

    def _parse_definition(self, el: etree._Element) -> Indicator:
        """Parse a ``<definition>`` into a single root :class:`Indicator`.

        OpenIOC 1.0 allows multiple ``<Indicator>`` children of a
        ``<definition>``. To present a single root in the in-memory
        model, multiple top-level Indicators are wrapped in a synthetic
        ``OR`` Indicator with a generated UUID. A definition with
        exactly one Indicator is returned unwrapped.

        Args:
            el: The ``<definition>`` element.

        Returns:
            Root :class:`Indicator` for the criteria tree.

        Raises:
            ParseError: If the ``<definition>`` contains no
                ``<Indicator>`` children.
        """
        indicators = []
        for child in el:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child.tag).localname.lower()
            if local == "indicator":
                indicators.append(self._parse_indicator(child))

        if not indicators:
            raise ParseError("Empty <definition>: must contain at least one <Indicator>")

        if len(indicators) == 1:
            return indicators[0]

        # wrap multiple top-level Indicators in a synthetic OR node
        return Indicator(
            id=str(uuid.uuid4()),
            operator=IndicatorOperator.OR,
            children=list(indicators),
        )

    def _parse_indicator(self, el: etree._Element) -> Indicator:
        """Parse an ``<Indicator>`` element into an :class:`Indicator`.

        Comparisons on the ``operator`` attribute are case-insensitive
        and any unrecognised value falls back to ``OR``. Children are
        recursed into via this method or :meth:`_parse_indicator_item`.

        Args:
            el: The ``<Indicator>`` element.

        Returns:
            Populated :class:`Indicator`.
        """
        op_str = el.get("operator", "OR").upper()
        try:
            operator = IndicatorOperator(op_str)
        except ValueError:
            operator = IndicatorOperator.OR

        indicator = Indicator(
            id=el.get("id", ""),
            operator=operator,
        )

        for child in el:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child.tag).localname.lower()
            if local == "indicator":
                indicator.children.append(self._parse_indicator(child))
            elif local == "indicatoritem":
                indicator.children.append(self._parse_indicator_item(child))

        return indicator

    def _parse_indicator_item(self, el: etree._Element) -> IndicatorItem:
        """Parse an ``<IndicatorItem>`` into an :class:`IndicatorItem`.

        Applies the following defaults when attributes are absent:
        ``condition="is"``, ``Context.context_type="mir"``,
        ``Content.content_type="string"``. An optional ``<Comment>``
        child is captured into :attr:`IndicatorItem.comment`.

        Args:
            el: The ``<IndicatorItem>`` element.

        Returns:
            Populated :class:`IndicatorItem`.
        """
        item_id = el.get("id", "")
        condition = el.get("condition", "is")

        context = Context(document="", search="")
        content = Content(value="")
        comment = ""

        for child in el:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child.tag).localname.lower()
            if local == "context":
                context = Context(
                    document=child.get("document", ""),
                    search=child.get("search", ""),
                    context_type=child.get("type", "mir"),
                )
            elif local == "content":
                content = Content(
                    value=(child.text or "").strip(),
                    content_type=child.get("type", "string"),
                )
            elif local == "comment":
                comment = (child.text or "").strip()

        return IndicatorItem(
            id=item_id,
            context=context,
            content=content,
            condition=condition,
            comment=comment,
        )
