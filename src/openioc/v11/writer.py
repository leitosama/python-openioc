from __future__ import annotations

import os

from lxml import etree

from ..constants import NS_V11
from ..exceptions import WriteError
from ..models import IOC, Indicator, IndicatorItem, Link, Metadata, Parameter


class IOCv11Writer:
    NAMESPACE = NS_V11
    NSMAP: dict[str | None, str] = {None: NS_V11}

    def write_file(
        self,
        ioc: IOC,
        path: str | os.PathLike,
        *,
        pretty_print: bool = True,
    ) -> None:
        data = self.write_string(ioc, pretty_print=pretty_print)
        with open(path, "wb") as fh:
            fh.write(data)

    def write_string(self, ioc: IOC, *, pretty_print: bool = True) -> bytes:
        root = self.write_element(ioc)
        return etree.tostring(
            root, pretty_print=pretty_print, xml_declaration=True, encoding="utf-8"
        )

    def write_element(self, ioc: IOC) -> etree._Element:
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
        el = etree.SubElement(parent, self._tag("link"))
        el.set("rel", link.rel)
        if link.href:
            el.set("href", link.href)
        if link.text:
            el.text = link.text

    def _build_indicator(self, indicator: Indicator) -> etree._Element:
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
