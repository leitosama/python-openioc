"""Profile-aware IOC validator.

Checks an :class:`~openioc.models.IOC` against a
:class:`~openioc.profiles.profile.Profile` and returns a structured
:class:`~openioc.profiles.report.Report` without modifying the IOC.
"""

from __future__ import annotations

from ..constants import IndicatorOperator
from ..models import IOC, Indicator, IndicatorItem
from .profile import Profile
from .report import Report, Severity, Violation, ViolationCode


class ProfileValidator:
    """Validate an IOC against a consumer profile.

    Args:
        profile: The profile that defines the allowed subset.
    """

    def __init__(self, profile: Profile) -> None:
        self._profile = profile

    def validate(self, ioc: IOC) -> Report:
        """Check *ioc* against the profile and return a report.

        The IOC is never modified. All violations are collected before
        returning so the caller receives a complete picture.

        Args:
            ioc: The IOC document to validate.

        Returns:
            A :class:`~openioc.profiles.report.Report` containing every
            violation found.  An empty violations list means the IOC is
            fully compatible with the profile.
        """
        violations: list[Violation] = []
        if ioc.definition is not None:
            self._walk(
                node=ioc.definition,
                location="definition",
                depth=1,
                parent_operator=None,
                violations=violations,
            )
        return Report(violations=violations)

    def _walk(
        self,
        node: Indicator,
        location: str,
        depth: int,
        parent_operator: IndicatorOperator | None,
        violations: list[Violation],
    ) -> None:
        profile = self._profile
        struct = profile.structure

        # --- Structural checks on this Indicator node ---
        if struct.max_nesting is not None and depth > struct.max_nesting:
            violations.append(
                Violation(
                    code=ViolationCode.MAX_NESTING_EXCEEDED,
                    message=(
                        f"Indicator at depth {depth} exceeds max_nesting={struct.max_nesting}"
                    ),
                    severity=Severity.ERROR,
                    location=location,
                    details={"depth": depth, "max_nesting": struct.max_nesting},
                )
            )
            # Don't recurse further — subtree is already in violation.
            return

        if (
            depth == 1
            and node.operator == IndicatorOperator.OR
            and not struct.allow_or_at_top_level
        ):
            violations.append(
                Violation(
                    code=ViolationCode.OR_NOT_ALLOWED_AT_TOP_LEVEL,
                    message="Root Indicator uses OR but profile requires AND at the top level",
                    severity=Severity.ERROR,
                    location=location,
                )
            )

        if parent_operator is not None:
            if (
                parent_operator == IndicatorOperator.AND
                and node.operator == IndicatorOperator.OR
                and not struct.allow_or_inside_and
            ):
                violations.append(
                    Violation(
                        code=ViolationCode.MIXED_OPERATORS_NOT_ALLOWED,
                        message="OR Indicator inside AND is not allowed by this profile",
                        severity=Severity.ERROR,
                        location=location,
                    )
                )
            elif (
                parent_operator == IndicatorOperator.OR
                and node.operator == IndicatorOperator.AND
                and not struct.allow_and_inside_or
            ):
                violations.append(
                    Violation(
                        code=ViolationCode.MIXED_OPERATORS_NOT_ALLOWED,
                        message="AND Indicator inside OR is not allowed by this profile",
                        severity=Severity.ERROR,
                        location=location,
                    )
                )

        # --- Recurse into children ---
        for child in node.children:
            if isinstance(child, Indicator):
                child_loc = f"{location}/Indicator[id={child.id}]"
                self._walk(
                    node=child,
                    location=child_loc,
                    depth=depth + 1,
                    parent_operator=node.operator,
                    violations=violations,
                )
            elif isinstance(child, IndicatorItem):
                child_loc = f"{location}/IndicatorItem[id={child.id}]"
                self._check_item(child, child_loc, violations)

    def _check_item(
        self,
        item: IndicatorItem,
        location: str,
        violations: list[Violation],
    ) -> None:
        profile = self._profile

        # Empty terms dict = allow all terms; skip term-level checks.
        if not profile.terms:
            return

        term_key = item.context.search
        term_spec = profile.terms.get(term_key)

        if term_spec is None:
            violations.append(
                Violation(
                    code=ViolationCode.UNSUPPORTED_TERM,
                    message=f"Term {term_key!r} is not supported by this profile",
                    severity=Severity.ERROR,
                    location=location,
                    details={"term": term_key},
                )
            )
            # No point checking operator/content_type for an unsupported term.
            return

        if item.condition not in term_spec.operators:
            violations.append(
                Violation(
                    code=ViolationCode.INVALID_OPERATOR,
                    message=(
                        f"Operator {item.condition!r} is not allowed for term "
                        f"{term_key!r}; allowed: {sorted(term_spec.operators)}"
                    ),
                    severity=Severity.ERROR,
                    location=location,
                    details={
                        "term": term_key,
                        "operator": item.condition,
                        "allowed_operators": sorted(term_spec.operators),
                    },
                )
            )

        if term_spec.content_types and item.content.content_type not in term_spec.content_types:
            violations.append(
                Violation(
                    code=ViolationCode.INVALID_CONTENT_TYPE,
                    message=(
                        f"Content type {item.content.content_type!r} is not allowed "
                        f"for term {term_key!r}; allowed: {sorted(term_spec.content_types)}"
                    ),
                    severity=Severity.ERROR,
                    location=location,
                    details={
                        "term": term_key,
                        "content_type": item.content.content_type,
                        "allowed_content_types": sorted(term_spec.content_types),
                    },
                )
            )
