from __future__ import annotations

import os

from lxml import etree

from ..constants import IndicatorOperator
from ..exceptions import ParseError
from ..models import IOC, Content, Context, Indicator, IndicatorItem, Link, Metadata


class IOCv10Reader:
    def read_file(self, path: str | os.PathLike) -> IOC:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML in {path}: {exc}") from exc
        return self.read_element(tree.getroot())

    def read_string(self, src: str | bytes) -> IOC:
        if isinstance(src, str):
            src = src.encode()
        try:
            root = etree.fromstring(src)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Malformed XML: {exc}") from exc
        return self.read_element(root)

    def read_element(self, root: etree._Element) -> IOC:
        tag = etree.QName(root.tag).localname.lower()
        if tag != "ioc":
            raise ParseError(f"Expected root element <ioc>, got <{root.tag}>")
        return self._parse_ioc(root)

    def _parse_ioc(self, el: etree._Element) -> IOC:
        ioc_id = el.get("id", "")
        # Real OpenIOC 1.0 uses "last-modified"; no created-date or published-date
        last_modified = el.get("last-modified", "")

        meta = Metadata()
        definition = None

        for child in el:
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
        links = []
        for child in el:
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
        indicators = []
        for child in el:
            local = etree.QName(child.tag).localname.lower()
            if local == "indicator":
                indicators.append(self._parse_indicator(child))

        if not indicators:
            raise ParseError("Empty <definition>: must contain at least one <Indicator>")

        if len(indicators) == 1:
            return indicators[0]

        # wrap multiple top-level Indicators in a synthetic OR node
        import uuid

        return Indicator(
            id=str(uuid.uuid4()),
            operator=IndicatorOperator.OR,
            children=list(indicators),
        )

    def _parse_indicator(self, el: etree._Element) -> Indicator:
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
            local = etree.QName(child.tag).localname.lower()
            if local == "indicator":
                indicator.children.append(self._parse_indicator(child))
            elif local == "indicatoritem":
                indicator.children.append(self._parse_indicator_item(child))

        return indicator

    def _parse_indicator_item(self, el: etree._Element) -> IndicatorItem:
        item_id = el.get("id", "")
        condition = el.get("condition", "is")

        context = Context(document="", search="")
        content = Content(value="")
        comment = ""

        for child in el:
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
