"""Parser for OpenIOC 1.1 documents.

OpenIOC 1.1 introduces a number of structural changes over 1.0:

* The root element is renamed ``<ioc>`` -> ``<OpenIOC>``.
* Metadata fields are wrapped in a ``<metadata>`` element.
* The criteria tree lives under ``<criteria>`` instead of ``<definition>``.
* ``IndicatorItem`` gains ``negate`` and ``preserve-case`` boolean
  attributes; ``isnot`` / ``containsnot`` are removed.
* A new ``<parameters>`` section may carry tooling-specific metadata.
* Both ``Indicator`` and ``IndicatorItem`` require a non-empty ``id``.
"""

from __future__ import annotations

import os
import uuid

from lxml import etree

from ..constants import NS_V11, IndicatorOperator
from ..exceptions import ParseError
from ..models import IOC, Content, Context, Indicator, IndicatorItem, Link, Metadata, Parameter

# Hardened parser: disable external-entity resolution, network access, and huge-tree
# expansion to mitigate XXE and billion-laughs attacks against untrusted OpenIOC input.
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)


class IOCv11Reader:
    """Parser for OpenIOC 1.1 documents (openioc.org namespace).

    Stateless aside from the shared module-level hardened parser, so
    instances are cheap to create. Most callers should use
    :func:`openioc.read` rather than instantiating the reader
    directly.

    Attributes:
        NAMESPACE: The 1.1 namespace URI.
    """

    NAMESPACE = NS_V11

    def read_file(self, path: str | os.PathLike) -> IOC:
        """Parse an OpenIOC 1.1 document from a file path.

        Args:
            path: Path to the XML file.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.1"``.

        Raises:
            ParseError: If the file's contents are not valid 1.1 XML.
            OSError: If the file cannot be opened.
        """
        try:
            tree = etree.parse(str(path), _PARSER)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML in {path}: {exc}") from exc
        return self.read_element(tree.getroot())

    def read_string(self, src: str | bytes) -> IOC:
        """Parse an OpenIOC 1.1 document from an in-memory string.

        Args:
            src: XML content as ``str`` or ``bytes``.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.1"``.

        Raises:
            ParseError: If the content is not valid 1.1 XML.
        """
        if isinstance(src, str):
            src = src.encode()
        try:
            root = etree.fromstring(src, _PARSER)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML: {exc}") from exc
        return self.read_element(root)

    def read_element(self, root: etree._Element) -> IOC:
        """Parse an already-parsed XML element as a 1.1 document.

        Args:
            root: Element expected to be an OpenIOC 1.1 ``<OpenIOC>``
                root.

        Returns:
            Parsed :class:`IOC` with ``format_version == "1.1"``.

        Raises:
            ParseError: If ``root`` is not an ``<OpenIOC>`` element or
                the document is missing required structure.
        """
        local = etree.QName(root.tag).localname
        if local != "OpenIOC":
            raise ParseError(f"Expected root element <OpenIOC>, got <{root.tag}>")
        return self._parse_ioc(root)

    def _ns(self, tag: str) -> str:
        return f"{{{self.NAMESPACE}}}{tag}"

    def _parse_ioc(self, el: etree._Element) -> IOC:
        """Build an :class:`IOC` from the root ``<OpenIOC>`` element.

        Walks ``el``'s children, looking for the ``<metadata>``,
        ``<criteria>``, and ``<parameters>`` sections that 1.1
        documents are organised into.

        Args:
            el: The root ``<OpenIOC>`` element.

        Returns:
            Populated :class:`IOC` at ``format_version == "1.1"``.

        Raises:
            ParseError: If the document has no ``<criteria>``.
        """
        ioc_id = el.get("id", "")
        last_modified = el.get("last-modified", "")
        published_date = el.get("published-date", "")

        metadata = Metadata()
        definition = None
        parameters: list[Parameter] = []

        for child in el:
            local = etree.QName(child.tag).localname
            if local == "metadata":
                metadata = self._parse_metadata(child)
            elif local == "criteria":
                definition = self._parse_criteria(child)
            elif local == "parameters":
                parameters = self._parse_parameters(child)

        if definition is None:
            raise ParseError("Missing required <criteria> element in OpenIOC 1.1 document")

        return IOC(
            id=ioc_id,
            metadata=metadata,
            definition=definition,
            parameters=parameters,
            last_modified=last_modified,
            published_date=published_date,
            format_version="1.1",
        )

    def _parse_metadata(self, el: etree._Element) -> Metadata:
        """Parse a ``<metadata>`` block into a :class:`Metadata`.

        Args:
            el: The ``<metadata>`` element.

        Returns:
            Populated :class:`Metadata`.
        """
        meta = Metadata()
        for child in el:
            local = etree.QName(child.tag).localname
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
        return meta

    def _parse_links(self, el: etree._Element) -> list[Link]:
        """Parse a ``<links>`` container into a list of :class:`Link`.

        Args:
            el: ``<links>`` element.

        Returns:
            List of :class:`Link` objects in document order.
        """
        links = []
        for child in el:
            local = etree.QName(child.tag).localname
            if local == "link":
                links.append(
                    Link(
                        rel=child.get("rel", ""),
                        href=child.get("href", ""),
                        text=(child.text or "").strip(),
                    )
                )
        return links

    def _parse_criteria(self, el: etree._Element) -> Indicator:
        """Parse a ``<criteria>`` into a single root :class:`Indicator`.

        OpenIOC 1.1 allows multiple top-level ``<Indicator>`` children
        of a ``<criteria>``. To present a single root in the in-memory
        model, multiple top-level Indicators are wrapped in a
        synthetic ``OR`` Indicator with a generated UUID. A criteria
        with exactly one Indicator is returned unwrapped.

        Args:
            el: The ``<criteria>`` element.

        Returns:
            Root :class:`Indicator` for the criteria tree.

        Raises:
            ParseError: If the ``<criteria>`` contains no
                ``<Indicator>`` children.
        """
        indicators = [
            self._parse_indicator(child)
            for child in el
            if etree.QName(child.tag).localname == "Indicator"
        ]
        if not indicators:
            raise ParseError("Empty <criteria>: must contain at least one <Indicator>")
        if len(indicators) == 1:
            return indicators[0]
        return Indicator(
            id=str(uuid.uuid4()),
            operator=IndicatorOperator.OR,
            children=list(indicators),
        )

    def _parse_indicator(self, el: etree._Element) -> Indicator:
        """Parse an ``<Indicator>`` element into an :class:`Indicator`.

        Unrecognised values for the ``operator`` attribute fall back
        to ``OR``. The 1.1-only ``node-context`` attribute is captured
        when present.

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
            node_context=el.get("node-context"),
        )

        for child in el:
            local = etree.QName(child.tag).localname
            if local == "Indicator":
                indicator.children.append(self._parse_indicator(child))
            elif local == "IndicatorItem":
                indicator.children.append(self._parse_indicator_item(child))

        return indicator

    def _parse_indicator_item(self, el: etree._Element) -> IndicatorItem:
        """Parse an ``<IndicatorItem>`` into an :class:`IndicatorItem`.

        The ``negate`` and ``preserve-case`` attributes are parsed
        case-insensitively: only the literal string ``"true"``
        produces ``True``; anything else (including ``"True"``,
        ``"1"``, missing) produces ``False``.

        Args:
            el: The ``<IndicatorItem>`` element.

        Returns:
            Populated :class:`IndicatorItem`.
        """
        item_id = el.get("id", "")
        condition = el.get("condition", "is")
        negate = el.get("negate", "false").lower() == "true"
        preserve_case = el.get("preserve-case", "false").lower() == "true"

        context = Context(document="", search="")
        content = Content(value="")

        for child in el:
            local = etree.QName(child.tag).localname
            if local == "Context":
                context = Context(
                    document=child.get("document", ""),
                    search=child.get("search", ""),
                    context_type=child.get("type", "mir"),
                )
            elif local == "Content":
                content = Content(
                    value=(child.text or "").strip(),
                    content_type=child.get("type", "string"),
                )

        return IndicatorItem(
            id=item_id,
            context=context,
            content=content,
            condition=condition,
            negate=negate,
            preserve_case=preserve_case,
        )

    def _parse_parameters(self, el: etree._Element) -> list[Parameter]:
        """Parse a ``<parameters>`` block into a list of :class:`Parameter`.

        Args:
            el: ``<parameters>`` element.

        Returns:
            List of :class:`Parameter` in document order.
        """
        params = []
        for child in el:
            local = etree.QName(child.tag).localname
            if local == "param":
                params.append(self._parse_param(child))
        return params

    def _parse_param(self, el: etree._Element) -> Parameter:
        """Parse a single ``<param>`` element.

        Args:
            el: ``<param>`` element.

        Returns:
            Populated :class:`Parameter`.
        """
        param_id = el.get("id", "")
        ref_id = el.get("ref-id", "")
        name = el.get("name", "")
        value = ""
        value_type = "string"
        for child in el:
            local = etree.QName(child.tag).localname
            if local == "value":
                value = (child.text or "").strip()
                value_type = child.get("type", "string")
        return Parameter(id=param_id, ref_id=ref_id, name=name, value=value, value_type=value_type)
