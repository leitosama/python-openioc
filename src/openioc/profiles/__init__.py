"""openioc.profiles — consumer profile engine for python-openioc.

This subpackage provides:

* :class:`Profile` — immutable description of the OpenIOC subset a
  consumer product supports.
* :class:`ProfileValidator` — checks an IOC against a profile and
  returns a structured :class:`Report`.
* :class:`ProfileAdapter` — attempts to bring an IOC into compliance
  with a profile, controlled by :class:`AdapterPolicy`.
* A :func:`registry <get_profile>` that discovers installed profile
  packages via ``importlib.metadata`` entry points and supports
  explicit :func:`register_profile` / :func:`unregister_profile` calls.

Quick start::

    import openioc
    from openioc.profiles import get_profile, ProfileValidator, ProfileAdapter, AdapterPolicy

    ioc = openioc.read("indicator.ioc")
    profile = get_profile("kedr")              # requires openioc-profile-kedr installed
    report = ProfileValidator(profile).validate(ioc)
    if report.has_errors():
        result = ProfileAdapter(
            profile, AdapterPolicy(drop_unsupported_items=True)
        ).adapt(ioc)
        openioc.write(result.ioc, "indicator.kedr.ioc")

See ``docs/profiles/`` for the full format specification and a guide on
writing your own profile package.
"""

from .adapter import AdaptationResult, Change, ProfileAdapter
from .exceptions import (
    AdaptationFailed,
    ProfileError,
    ProfileSchemaError,
    UnknownProfileError,
)
from .policy import AdapterPolicy
from .profile import Profile, StructureSpec, TermSpec
from .registry import get_profile, list_profiles, register_profile, unregister_profile
from .report import Report, Severity, Violation, ViolationCode
from .validator import ProfileValidator

__all__ = [
    # profile model
    "Profile",
    "TermSpec",
    "StructureSpec",
    # registry
    "register_profile",
    "unregister_profile",
    "get_profile",
    "list_profiles",
    # validation
    "ProfileValidator",
    "Report",
    "Violation",
    "Severity",
    "ViolationCode",
    # adaptation
    "ProfileAdapter",
    "AdapterPolicy",
    "AdaptationResult",
    "Change",
    # exceptions
    "ProfileError",
    "ProfileSchemaError",
    "UnknownProfileError",
    "AdaptationFailed",
]
