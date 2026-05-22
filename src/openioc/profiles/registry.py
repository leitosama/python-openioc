"""Profile registry: registration, discovery, and lookup.

Profiles are discovered via ``importlib.metadata`` entry points in the
``openioc.profiles`` group. Any installed package that declares

    [project.entry-points."openioc.profiles"]
    myproduct = "my_pkg:load_profile"

will have its ``load_profile()`` callable invoked on the first registry
access; the returned :class:`~openioc.profiles.profile.Profile` is
cached for the lifetime of the process.

Profiles can also be registered explicitly:

    from openioc.profiles import register_profile
    register_profile(Profile.from_file("my_profile.json"))
"""

from __future__ import annotations

import importlib.metadata

from .exceptions import ProfileError, UnknownProfileError
from .profile import Profile

# Module-level cache. Populated lazily on first get_profile / list_profiles
# call, then supplemented by explicit register_profile() calls.
_registry: dict[str, Profile] = {}
_entry_points_loaded = False


def register_profile(profile: Profile) -> None:
    """Add a profile to the in-process registry.

    Args:
        profile: The profile to register.

    Raises:
        ProfileError: If a profile with the same ``name`` is already
            registered (either from a prior :func:`register_profile`
            call or discovered via entry points).
    """
    _ensure_entry_points_loaded()
    _register_one(profile, source="register_profile()")


def unregister_profile(name: str) -> None:
    """Remove a profile from the in-process registry.

    This is primarily useful in tests. Entry points are re-evaluated on
    the next :func:`get_profile` / :func:`list_profiles` call only if
    you also call :func:`_reset` (internal test helper).

    Args:
        name: Registry key to remove.

    Raises:
        UnknownProfileError: If no profile with that name is registered.
    """
    if name not in _registry:
        raise UnknownProfileError(name)
    del _registry[name]


def get_profile(name: str) -> Profile:
    """Look up a profile by its registry name.

    Triggers lazy entry-point discovery on the first call.

    Args:
        name: Registry key (e.g. ``"kedr"``).

    Returns:
        The matching :class:`~openioc.profiles.profile.Profile`.

    Raises:
        UnknownProfileError: If no profile is registered under *name*.
    """
    _ensure_entry_points_loaded()
    if name not in _registry:
        raise UnknownProfileError(name)
    return _registry[name]


def list_profiles() -> list[str]:
    """Return the names of all currently registered profiles.

    Triggers lazy entry-point discovery on the first call.

    Returns:
        Sorted list of registry keys.
    """
    _ensure_entry_points_loaded()
    return sorted(_registry.keys())


def _reset() -> None:
    """Clear the registry and force re-discovery on next access.

    Intended for use in tests only.
    """
    global _entry_points_loaded
    _registry.clear()
    _entry_points_loaded = False


def _ensure_entry_points_loaded() -> None:
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    _entry_points_loaded = True
    for ep in importlib.metadata.entry_points(group="openioc.profiles"):
        try:
            loader = ep.load()
            profile: Profile = loader()
        except Exception as exc:  # noqa: BLE001
            # A broken entry point should not crash the whole registry;
            # surface it as a warning-style error instead.
            raise ProfileError(
                f"Failed to load profile from entry point {ep.name!r}: {exc}"
            ) from exc
        _register_one(profile, source=f"entry point {ep.name!r}")


def _register_one(profile: Profile, source: str) -> None:
    if profile.name in _registry:
        raise ProfileError(
            f"Profile name {profile.name!r} is already registered (conflict with {source})"
        )
    _registry[profile.name] = profile
