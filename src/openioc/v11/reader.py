from __future__ import annotations

import os

from lxml import etree

from ..constants import NS_V11, IndicatorOperator
from ..exceptions import ParseError
from ..models import IOC, Content, Context, Indicator, IndicatorItem, Link, Metadata, Parameter


class IOCv11Reader:
    NAMESPACE = NS_V11

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
        local = etree.QName(root.tag).localname
        if local != "OpenIOC":
            raise ParseError(f"Expected root element <OpenIOC>, got <{root.tag}>")
        return self._parse_ioc(root)

    def _ns(self, tag: str) -> str:
        return f"{{{self.NAMESPACE}}}{tag}"

    def _parse_ioc(self, el: etree._Element) -> IOC:
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
        indicators = [
            self._parse_indicator(child)
            for child in el
            if etree.QName(child.tag).localname == "Indicator"
        ]
        if not indicators:
            raise ParseError("Empty <criteria>: must contain at least one <Indicator>")
        if len(indicators) == 1:
            return indicators[0]
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
        params = []
        for child in el:
            local = etree.QName(child.tag).localname
            if local == "param":
                params.append(self._parse_param(child))
        return params

    def _parse_param(self, el: etree._Element) -> Parameter:
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
