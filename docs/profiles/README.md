# openioc.profiles — consumer profile subsystem

Different consumers of OpenIOC — KATA KEDR, FireEye HX, Mandiant, and
others — support only a subset of the specification: a limited list of
terms, not all operators, and various structural constraints. This
subsystem lets you describe those constraints **declaratively** (as a
JSON file) and apply them to IOC documents: validate compatibility and,
optionally, automatically adapt the IOC to the target consumer.

## Quick start

```bash
pip install -e ".[profiles]"       # engine + jsonschema
pip install -e profiles/kedr       # KEDR profile package
```

```python
import openioc
from openioc.profiles import (
    get_profile,
    ProfileValidator,
    ProfileAdapter,
    AdapterPolicy,
)

ioc = openioc.read("indicator.ioc")

# 1. Resolve a profile (auto-discovered via entry points).
profile = get_profile("kedr")

# 2. Validate.
report = ProfileValidator(profile).validate(ioc)
print(f"{len(report.violations)} violation(s) found")
for v in report.violations:
    print(f"  [{v.severity.value}] {v.code.value}: {v.message}")
    print(f"    at {v.location}")

# 3. Adapt (conservative — only drops unsupported items when asked).
if report.has_errors():
    result = ProfileAdapter(
        profile, AdapterPolicy(drop_unsupported_items=True)
    ).adapt(ioc)
    openioc.write(result.ioc, "indicator.kedr.ioc")
    print(f"Applied {len(result.changes)} change(s)")
```

A runnable version of this script lives at
[`examples/profiles_e2e.py`](../../examples/profiles_e2e.py).

## Architecture

```
python-openioc (this package)
└── openioc.profiles          ← engine (format + validator + adapter + registry)

profiles/kedr/                ← separate distribution: openioc-profile-kedr
profiles/example/             ← separate distribution: openioc-profile-example (demo)
```

The engine knows nothing about any specific consumer — it only reads
JSON profiles that conform to the [schema](format.md). Consumer profiles
are standalone packages that register themselves via
[entry points](authoring.md), so the engine discovers them automatically
after `pip install`.

## API reference

| Symbol | Purpose |
|--------|---------|
| `Profile` | Immutable description of a consumer's supported subset. |
| `TermSpec` | Allowed operators and content types for one term. |
| `StructureSpec` | Structural constraints on the indicator tree. |
| `register_profile(p)` | Explicitly register a profile in the current process. |
| `unregister_profile(name)` | Remove a profile (useful in tests). |
| `get_profile(name)` | Look up a profile by name (triggers entry-point discovery). |
| `list_profiles()` | Return sorted list of registered profile names. |
| `ProfileValidator(p)` | Create a validator for profile `p`. |
| `ProfileValidator.validate(ioc)` | Returns a `Report`. |
| `Report` | List of `Violation` objects + `has_errors()`, `by_code()`, `to_dict()`. |
| `Violation` | `code`, `message`, `severity`, `location`, `details`. |
| `ViolationCode` | Stable enum of violation codes (see below). |
| `Severity` | `ERROR`, `WARNING`, `INFO`. |
| `ProfileAdapter(p, policy)` | Create an adapter for profile `p`. |
| `ProfileAdapter.adapt(ioc)` | Returns `AdaptationResult`. |
| `AdaptationResult` | `ioc`, `changes`, `residual`. |
| `AdapterPolicy` | `drop_unsupported_items: bool = False`. |
| `Change` | `action`, `location`, `reason`, `details`. |

### Violation codes

| Code | Meaning |
|------|---------|
| `UNSUPPORTED_TERM` | `Context.search` not listed in the profile's `terms`. |
| `INVALID_OPERATOR` | `condition` not in the term's allowed operators. |
| `INVALID_CONTENT_TYPE` | `Content.content_type` not in the term's allowed types. |
| `MAX_NESTING_EXCEEDED` | Indicator tree is deeper than `structure.max_nesting`. |
| `OR_NOT_ALLOWED_AT_TOP_LEVEL` | Root uses OR but profile requires AND. |
| `MIXED_OPERATORS_NOT_ALLOWED` | Forbidden operator nesting (OR in AND or AND in OR). |

## Further reading

- [format.md](format.md) — full JSON schema specification
- [authoring.md](authoring.md) — how to write and publish your own profile package
- [kedr.md](kedr.md) — notes on the KATA KEDR profile
