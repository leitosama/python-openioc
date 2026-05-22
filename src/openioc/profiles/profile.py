"""Profile dataclass and JSON loading/validation.

A :class:`Profile` is an immutable description of the OpenIOC subset
supported by a specific consumer product. Instances are normally created
via :meth:`Profile.from_file`, :meth:`Profile.from_json`, or
:meth:`Profile.from_dict`.

Schema validation uses ``jsonschema``, which is an optional dependency
(``pip install python-openioc[profiles]``). A clear error is raised if
the package is missing.
"""

from __future__ import annotations

import functools
import importlib.resources
import json
import os
from dataclasses import dataclass, field
from typing import Any

from .exceptions import ProfileSchemaError

SUPPORTED_SCHEMA_MAJOR = 1
"""Major version of the profile schema format this engine supports."""


@dataclass(frozen=True)
class TermSpec:
    """Constraints for a single term.

    Attributes:
        operators: Allowed condition values (e.g. ``["is", "contains"]``).
        content_types: Allowed Content.content_type values.  An empty
            tuple means any content type is allowed.
        description: Optional human-readable note.
    """

    operators: tuple[str, ...]
    content_types: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class StructureSpec:
    """Structural constraints on the indicator tree.

    All fields are optional; defaults impose no restrictions.

    Attributes:
        max_nesting: Maximum Indicator nesting depth, or ``None`` for no
            limit.
        allow_or_at_top_level: Whether the root Indicator may use OR.
        allow_or_inside_and: Whether an OR node may be a child of AND.
        allow_and_inside_or: Whether an AND node may be a child of OR.
    """

    max_nesting: int | None = None
    allow_or_at_top_level: bool = True
    allow_or_inside_and: bool = True
    allow_and_inside_or: bool = True


@dataclass(frozen=True)
class Profile:
    """Immutable description of an OpenIOC consumer's supported subset.

    Normally constructed via :meth:`from_dict`, :meth:`from_json`, or
    :meth:`from_file`.

    Attributes:
        schema_version: Version of the profile format used.
        name: Unique registry key (e.g. ``"kedr"``).
        profile_version: Version of this profile's data.
        target_product: Human-readable product name.
        target_versions: Product version(s) the profile applies to.
        description: Free-form description.
        source: URL of the official constraint documentation.
        terms: Mapping from ``Context.search`` string to
            :class:`TermSpec`. Empty means "allow all terms".
        structure: Structural constraints on the indicator tree.
        mappings: Term-rewrite hints (reserved, not used by the engine).
    """

    schema_version: str
    name: str
    profile_version: str = ""
    target_product: str = ""
    target_versions: tuple[str, ...] = ()
    description: str = ""
    source: str = ""
    terms: dict[str, TermSpec] = field(default_factory=dict)
    structure: StructureSpec = field(default_factory=StructureSpec)
    mappings: dict[str, str] = field(default_factory=dict)

    # frozen=True prevents mutation but dataclass fields need default_factory
    # to be unhashable containers — we use field() for those.

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        """Build a :class:`Profile` from a parsed JSON dictionary.

        Validates the dictionary against the bundled JSON Schema before
        constructing the dataclass.

        Args:
            data: A dict parsed from a profile JSON file.

        Returns:
            A validated, immutable :class:`Profile`.

        Raises:
            ProfileSchemaError: If ``data`` does not conform to the
                profile JSON Schema, or if ``schema_version`` has a
                major component that differs from
                :data:`SUPPORTED_SCHEMA_MAJOR`.
        """
        _validate_against_json_schema(data)
        _check_schema_major(data.get("schema_version", ""))
        return cls._from_validated_dict(data)

    @classmethod
    def from_json(cls, text: str) -> Profile:
        """Parse and validate a profile from a JSON string.

        Args:
            text: Raw JSON text of a profile document.

        Returns:
            A validated :class:`Profile`.

        Raises:
            ProfileSchemaError: If the JSON is invalid or the document
                fails schema validation.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProfileSchemaError([f"Invalid JSON: {exc}"]) from exc
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> Profile:
        """Load and validate a profile from a JSON file.

        Args:
            path: Path to a ``.json`` profile file.

        Returns:
            A validated :class:`Profile`.

        Raises:
            ProfileSchemaError: If the file content fails validation.
            OSError: If the file cannot be read.
        """
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        return cls.from_json(text)

    @classmethod
    def _from_validated_dict(cls, data: dict[str, Any]) -> Profile:
        terms: dict[str, TermSpec] = {}
        for search, spec in (data.get("terms") or {}).items():
            terms[search] = TermSpec(
                operators=tuple(spec["operators"]),
                content_types=tuple(spec.get("content_types") or []),
                description=spec.get("description", ""),
            )

        raw_struct = data.get("structure") or {}
        structure = StructureSpec(
            max_nesting=raw_struct.get("max_nesting"),
            allow_or_at_top_level=raw_struct.get("allow_or_at_top_level", True),
            allow_or_inside_and=raw_struct.get("allow_or_inside_and", True),
            allow_and_inside_or=raw_struct.get("allow_and_inside_or", True),
        )

        raw_tv = data.get("target_versions", "")
        if isinstance(raw_tv, list):
            target_versions: tuple[str, ...] = tuple(raw_tv)
        elif raw_tv:
            target_versions = (raw_tv,)
        else:
            target_versions = ()

        return cls(
            schema_version=data["schema_version"],
            name=data["name"],
            profile_version=data.get("profile_version", ""),
            target_product=data.get("target_product", ""),
            target_versions=target_versions,
            description=data.get("description", ""),
            source=data.get("source", ""),
            terms=terms,
            structure=structure,
            mappings=dict(data.get("mappings") or {}),
        )


def _check_schema_major(version: str) -> None:
    """Verify the major version component is supported."""
    try:
        major = int(version.split(".")[0])
    except (ValueError, IndexError) as exc:
        raise ProfileSchemaError(
            [f"schema_version {version!r} is not a valid semver string"]
        ) from exc
    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ProfileSchemaError(
            [
                f"Unsupported schema_version major={major}; "
                f"this engine supports major={SUPPORTED_SCHEMA_MAJOR}"
            ]
        )


def _validate_against_json_schema(data: dict[str, Any]) -> None:
    """Run jsonschema validation against the bundled profile schema."""
    try:
        import jsonschema  # type: ignore[import]
    except ImportError as exc:
        raise ProfileSchemaError(
            [
                "jsonschema is required for profile validation. "
                "Install it with: pip install python-openioc[profiles]"
            ]
        ) from exc

    schema = _load_profile_schema()
    validator_cls = jsonschema.Draft202012Validator
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        messages = [
            f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
        ]
        raise ProfileSchemaError(messages)


@functools.lru_cache(maxsize=1)
def _load_profile_schema() -> dict[str, Any]:
    pkg = importlib.resources.files("openioc.profiles.schema")
    return json.loads(pkg.joinpath("profile.schema.json").read_text(encoding="utf-8"))
