"""Violation codes, severity levels, and the validation report model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Severity of a profile violation."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ViolationCode(str, Enum):
    """Stable, documented codes for profile violations.

    These codes are part of the public API and will not be renamed
    without a major version bump.
    """

    UNSUPPORTED_TERM = "UNSUPPORTED_TERM"
    """The IndicatorItem's Context.search value is not listed in the profile."""

    INVALID_OPERATOR = "INVALID_OPERATOR"
    """The condition on an IndicatorItem is not allowed for its term."""

    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    """The Content.content_type on an IndicatorItem is not allowed for its term."""

    MAX_NESTING_EXCEEDED = "MAX_NESTING_EXCEEDED"
    """The indicator tree is nested deeper than the profile permits."""

    OR_NOT_ALLOWED_AT_TOP_LEVEL = "OR_NOT_ALLOWED_AT_TOP_LEVEL"
    """The root Indicator uses OR but the profile requires AND at the top level."""

    MIXED_OPERATORS_NOT_ALLOWED = "MIXED_OPERATORS_NOT_ALLOWED"
    """An OR inside an AND (or AND inside an OR) is forbidden by the profile."""


@dataclass
class Violation:
    """A single constraint violation found by :class:`ProfileValidator`.

    Attributes:
        code: Stable violation code (one of :class:`ViolationCode`).
        message: Human-readable description of the violation.
        severity: How serious the violation is.
        location: Id-based path to the offending node, for example
            ``"definition/Indicator[id=abc]/IndicatorItem[id=def]"``.
        details: Optional extra context (term name, operator, limits, …).
    """

    code: ViolationCode
    message: str
    severity: Severity
    location: str
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "severity": self.severity.value,
            "location": self.location,
            "details": self.details,
        }


@dataclass
class Report:
    """Aggregated result of a profile-validation run.

    Attributes:
        violations: All findings, in tree-walk order.
    """

    violations: list[Violation] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Return ``True`` if any violation has severity ERROR."""
        return any(v.severity == Severity.ERROR for v in self.violations)

    def by_code(self, code: ViolationCode) -> list[Violation]:
        """Return all violations with the given code."""
        return [v for v in self.violations if v.code == code]

    def to_dict(self) -> dict[str, object]:
        return {"violations": [v.to_dict() for v in self.violations]}
