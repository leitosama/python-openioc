"""Exceptions raised by the openioc.profiles subsystem.

All errors derive from :class:`ProfileError` so callers can catch that
single base class to handle any failure from the profiles engine.
"""

from __future__ import annotations

from ..exceptions import OpenIOCError


class ProfileError(OpenIOCError):
    """Base class for all profile-subsystem exceptions."""


class ProfileSchemaError(ProfileError):
    """Raised when a profile JSON document fails schema validation.

    Attributes:
        errors: Human-readable validation errors collected by jsonschema.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


class UnknownProfileError(ProfileError):
    """Raised when a requested profile name is not registered.

    Attributes:
        name: The profile name that was looked up.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"No profile registered under name {name!r}")


class AdaptationFailed(ProfileError):
    """Raised when the adapter cannot produce a valid IOC.

    This happens, for example, when every IndicatorItem in the tree is
    unsupported by the target profile and removal leaves no items.
    """
