from __future__ import annotations

import os
import uuid
from typing import Union

from lxml import etree

from ..models import Content, Context, IOC, Indicator, IndicatorItem, Link, Metadata, Parameter
from ..exceptions import WriteError


class IOCv10Writer:
    def write_file(
        self,
        ioc: IOC,
        path: Union[str, os.PathLike],
        *,
        pretty_print: bool = True,
    ) -> None:
        data = self.write_string(ioc, pretty_print=pretty_print)
        with open(path, "wb") as fh:
            fh.write(data)

    def write_string(self, ioc: IOC, *, pretty_print: bool = True) -> bytes:
        root = self.write_element(ioc)
        return etree.tostring(
            root,
            pretty_print=pretty_print,
            xml_declaration=True,
            encoding="utf-8",
        )

    def write_element(self, ioc: IOC) -> etree._Element:
        root = etree.Element("ioc")
        root.set("id", self._ensure_id(ioc.id))
        if ioc.created_date:
            root.set("created-date", ioc.created_date)
        if ioc.last_modified:
            root.set("last-modified-date", ioc.last_modified)
        if ioc.published_date:
            root.set("published-date", ioc.published_date)

        root.append(self._build_metadata(ioc.metadata))

        if ioc.definition is None:
            raise WriteError("IOC.definition must not be None for v1.0 serialization")
        defn = etree.SubElement(root, "definition")
        defn.append(self._build_indicator(ioc.definition))

        return root

    def _build_metadata(self, meta: Metadata) -> etree._Element:
        el = etree.Element("metadata")
        self._sub_text(el, "short_description", meta.short_description)
        self._sub_text(el, "description", meta.description)
        self._sub_text(el, "keywords", meta.keywords)
        self._sub_text(el, "authored_by", meta.authored_by)
        self._sub_text(el, "authored_date", meta.authored_date)
        if meta.links:
            links_el = etree.SubElement(el, "links")
            for link in meta.links:
                self._build_link(links_el, link)
        return el

    def _build_link(self, parent: etree._Element, link: Link) -> None:
        el = etree.SubElement(parent, "link")
        el.set("rel", link.rel)
        if link.href:
            el.set("href", link.href)
        if link.text:
            el.text = link.text

    def _build_indicator(self, indicator: Indicator) -> etree._Element:
        el = etree.Element("Indicator")
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
        el = etree.Element("IndicatorItem")
        el.set("id", self._ensure_id(item.id))
        el.set("condition", item.condition)

        ctx = etree.SubElement(el, "Context")
        ctx.set("document", item.context.document)
        ctx.set("search", item.context.search)
        ctx.set("type", item.context.context_type)

        content = etree.SubElement(el, "Content")
        content.set("type", item.content.content_type)
        content.text = item.content.value

        return el

    def _sub_text(self, parent: etree._Element, tag: str, text: str) -> None:
        el = etree.SubElement(parent, tag)
        el.text = text

    def _ensure_id(self, value: str) -> str:
        return value if value else str(uuid.uuid4())
