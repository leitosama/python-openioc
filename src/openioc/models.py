from __future__ import annotations

from dataclasses import dataclass, field

from .constants import IndicatorOperator


@dataclass
class Context:
    document: str
    search: str
    context_type: str = "mir"  # XML attribute is named "type"


@dataclass
class Content:
    value: str
    content_type: str = "string"  # XML attribute is named "type"


@dataclass
class IndicatorItem:
    id: str
    context: Context
    content: Content
    condition: str = "is"
    negate: bool = False  # 1.1 only; v1.0 writer ignores this
    preserve_case: bool = False  # 1.1 only; v1.0 writer ignores this
    comment: str = ""  # v1.0 <Comment>; v1.1 writer ignores this


@dataclass
class Indicator:
    id: str
    operator: IndicatorOperator = IndicatorOperator.AND
    node_context: str | None = None  # 1.1 only
    children: list[Indicator | IndicatorItem] = field(default_factory=list)


@dataclass
class Link:
    rel: str
    href: str = ""
    text: str = ""


@dataclass
class Metadata:
    short_description: str = ""
    description: str = ""
    keywords: str = ""
    authored_by: str = ""
    authored_date: str = ""
    links: list[Link] = field(default_factory=list)


@dataclass
class Parameter:
    """OpenIOC 1.1 only."""

    id: str
    ref_id: str
    name: str
    value: str = ""
    value_type: str = "string"


@dataclass
class IOC:
    id: str
    metadata: Metadata = field(default_factory=Metadata)
    definition: Indicator | None = None
    parameters: list[Parameter] = field(default_factory=list)
    created_date: str = ""  # not in v1.0 spec; used for v1.1 and conversion
    last_modified: str = ""  # 1.0/1.1: last-modified attribute
    published_date: str = ""  # 1.1: published-date
    format_version: str = "1.1"
