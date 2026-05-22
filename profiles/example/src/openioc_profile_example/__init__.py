"""openioc-profile-example: minimal demo profile for openioc.profiles."""

from __future__ import annotations

from importlib.resources import files

from openioc.profiles import Profile


def load() -> Profile:
    """Return the example consumer profile.

    This is the entry-point callable registered under
    ``openioc.profiles`` in this package's pyproject.toml.
    """
    text = files(__package__).joinpath("profile.json").read_text(encoding="utf-8")
    return Profile.from_json(text)
