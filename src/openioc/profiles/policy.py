"""Adapter policy configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdapterPolicy:
    """Controls which automatic transformations the adapter may apply.

    The default policy is conservative: the adapter makes no changes and
    simply reports residual violations. Enable flags explicitly to permit
    modifications that could alter detection logic.

    Attributes:
        drop_unsupported_items: When ``True``, the adapter removes
            ``IndicatorItem`` nodes that trigger ``UNSUPPORTED_TERM``,
            ``INVALID_OPERATOR``, or ``INVALID_CONTENT_TYPE`` violations.
            Empty ``Indicator`` nodes left behind are collapsed upward.
            If the entire tree becomes empty, :exc:`AdaptationFailed` is
            raised. Defaults to ``False``.
    """

    drop_unsupported_items: bool = False
