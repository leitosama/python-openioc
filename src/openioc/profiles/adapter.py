"""Profile-aware IOC adapter.

Attempts to bring an IOC into compliance with a consumer profile by
applying the transformations permitted by the caller's
:class:`~openioc.profiles.policy.AdapterPolicy`.  The input IOC is
never mutated; a deep copy is always produced.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..models import IOC, Indicator, IndicatorItem
from .exceptions import AdaptationFailed
from .policy import AdapterPolicy
from .profile import Profile
from .report import Report, ViolationCode
from .validator import ProfileValidator


@dataclass
class Change:
    """A single transformation applied by the adapter.

    Attributes:
        action: Short description of the action (e.g. ``"DROPPED_ITEM"``).
        location: Id-based path to the affected node.
        reason: Human-readable explanation.
        details: Optional structured context.
    """

    action: str
    location: str
    reason: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass
class AdaptationResult:
    """Output of :meth:`ProfileAdapter.adapt`.

    Attributes:
        ioc: The (possibly transformed) IOC.  Always a deep copy of the
            input — the original is never mutated.
        changes: Ordered list of every transformation applied.
        residual: Validation report after adaptation.  An empty
            violations list means the adapted IOC is fully compatible.
    """

    ioc: IOC
    changes: list[Change]
    residual: Report


class ProfileAdapter:
    """Adapt an IOC to conform to a consumer profile.

    Args:
        profile: The target profile.
        policy: Controls which transformations are permitted.
            Defaults to the conservative no-op policy.
    """

    def __init__(self, profile: Profile, policy: AdapterPolicy | None = None) -> None:
        self._profile = profile
        self._policy = policy if policy is not None else AdapterPolicy()
        self._validator = ProfileValidator(profile)

    def adapt(self, ioc: IOC) -> AdaptationResult:
        """Return a (possibly transformed) copy of *ioc*.

        When the policy enables no transformations the returned IOC is
        still a deep copy; only the residual report differs from a plain
        :meth:`~openioc.profiles.validator.ProfileValidator.validate`
        call.

        Args:
            ioc: Source IOC document.

        Returns:
            :class:`AdaptationResult` with the adapted IOC, a changelog,
            and a residual validation report.

        Raises:
            AdaptationFailed: If ``policy.drop_unsupported_items`` is
                ``True`` and removing all unsupported items leaves the
                indicator tree empty.
        """
        adapted = copy.deepcopy(ioc)
        changes: list[Change] = []

        initial_report = self._validator.validate(adapted)
        if not initial_report.violations:
            return AdaptationResult(ioc=adapted, changes=[], residual=initial_report)

        if self._policy.drop_unsupported_items and adapted.definition is not None:
            # Collect locations of items to drop.
            item_violation_codes = {
                ViolationCode.UNSUPPORTED_TERM,
                ViolationCode.INVALID_OPERATOR,
                ViolationCode.INVALID_CONTENT_TYPE,
            }
            drop_locations = {
                v.location for v in initial_report.violations if v.code in item_violation_codes
            }

            _drop_items(adapted.definition, "definition", drop_locations, changes, initial_report)

            # Collapse empty Indicators (post-drop).
            _collapse_empty(adapted.definition)

            # If root has no children left, we have nothing useful.
            if not adapted.definition.children:
                raise AdaptationFailed(
                    "All IndicatorItems in the IOC are unsupported by this profile; "
                    "nothing remains after adaptation."
                )

        residual = self._validator.validate(adapted)
        return AdaptationResult(ioc=adapted, changes=changes, residual=residual)


def _drop_items(
    node: Indicator,
    location: str,
    drop_locations: set[str],
    changes: list[Change],
    report: Report,
) -> None:
    """Recursively remove IndicatorItems whose location is in *drop_locations*."""
    kept: list[Indicator | IndicatorItem] = []
    for child in node.children:
        if isinstance(child, IndicatorItem):
            child_loc = f"{location}/IndicatorItem[id={child.id}]"
            if child_loc in drop_locations:
                # Find the violation(s) for this item to build the reason.
                reasons = [v.message for v in report.violations if v.location == child_loc]
                changes.append(
                    Change(
                        action="DROPPED_ITEM",
                        location=child_loc,
                        reason="; ".join(reasons) if reasons else "item violates profile",
                        details={"term": child.context.search, "condition": child.condition},
                    )
                )
            else:
                kept.append(child)
        elif isinstance(child, Indicator):
            child_loc = f"{location}/Indicator[id={child.id}]"
            _drop_items(child, child_loc, drop_locations, changes, report)
            kept.append(child)
        else:
            kept.append(child)
    node.children = kept


def _collapse_empty(node: Indicator) -> None:
    """Remove child Indicators that have no children after item-dropping."""
    new_children: list[Indicator | IndicatorItem] = []
    for child in node.children:
        if isinstance(child, Indicator):
            _collapse_empty(child)
            if child.children:
                new_children.append(child)
            # else: silently discard the now-empty sub-tree
        else:
            new_children.append(child)
    node.children = new_children
