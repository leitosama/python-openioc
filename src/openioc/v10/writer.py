from __future__ import annotations

import os
import uuid

from lxml import etree

from ..constants import NS_V10
from ..exceptions import WriteError
from ..models import IOC, Indicator, IndicatorItem, Link, Metadata


class IOCv10Writer:
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
        data = self.write_string(ioc, pretty_print=pretty_print)
        with open(path, "wb") as fh:
            fh.write(data)

    def write_string(self, ioc: IOC, *, pretty_print: bool = True) -> bytes:
        root = self.write_element(ioc)
        return etree.tostring(
            root, pretty_print=pretty_print, xml_declaration=True, encoding="utf-8"
        )

    def write_element(self, ioc: IOC) -> etree._Element:
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
        el = etree.SubElement(parent, self._tag("link"))
        el.set("rel", link.rel)
        if link.href:
            el.set("href", link.href)
        if link.text:
            el.text = link.text

    def _build_indicator(self, indicator: Indicator) -> etree._Element:
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
        el = etree.Element(self._tag("IndicatorItem"))
        el.set("id", self._ensure_id(item.id))
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
