# KATA KEDR profile notes

**Package**: `openioc-profile-kedr`  
**Location**: [`profiles/kedr/`](../../profiles/kedr/)  
**Registry name**: `kedr`

---

## Status

> **Work in progress.** The current profile contains a reasonable
> starter set of terms derived from typical EDR telemetry categories
> (FileItem, RegistryItem, PortItem, ProcessItem).  The authoritative
> list of KEDR-supported OpenIOC terms has not yet been sourced from
> official documentation.

Once the official documentation link is available, add it to `source`
in `profile.json` and update the `profile_version`.

---

## Target product

| Field | Value |
|-------|-------|
| Product | Kaspersky Anti Targeted Attack Platform — KEDR component |
| Tested versions | 5.x, 6.x (stub; update when verified) |
| Source | *(pending — add official documentation URL here)* |

---

## Current term coverage (stub)

| Term | Allowed operators | Allowed content types |
|------|------------------|-----------------------|
| `FileItem/FileName` | is, contains, matches, starts-with, ends-with | string |
| `FileItem/FullPath` | is, contains, matches, starts-with, ends-with | string |
| `FileItem/Md5sum` | is | md5 |
| `FileItem/Sha1sum` | is | sha1 |
| `FileItem/Sha256sum` | is | sha256 |
| `RegistryItem/Path` | is, contains, starts-with | string |
| `RegistryItem/ValueName` | is, contains | string |
| `RegistryItem/Value` | is, contains | string |
| `PortItem/localPort` | is | string |
| `PortItem/remoteIP` | is, contains | string |
| `ProcessItem/name` | is, contains, matches | string |
| `ProcessItem/path` | is, contains, starts-with | string |

---

## Structural constraints (stub)

| Constraint | Value |
|-----------|-------|
| `max_nesting` | 5 |
| `allow_or_at_top_level` | true |
| `allow_or_inside_and` | true |
| `allow_and_inside_or` | true |

---

## Known adapter limitations

- FireEye HX-style terms (`fileWriteEvent/*`, `processEvent/*`) are not
  in the stub and will be flagged as `UNSUPPORTED_TERM`.  With
  `drop_unsupported_items=True` they are dropped; if your IOC uses only
  those terms, adaptation will fail with `AdaptationFailed`.
- The adapter does not remap HX terms to their KEDR equivalents
  (e.g. `fileWriteEvent/fileName` → `FileItem/FileName`) — that would
  require semantic knowledge beyond the current scope.  Add a `mappings`
  entry in the profile and implement a rewrite action in a future adapter
  version.

---

## How to improve this profile

1. Find the official KATA KEDR documentation for supported OpenIOC terms.
2. Edit
   [`profiles/kedr/src/openioc_profile_kedr/profile.json`](../../profiles/kedr/src/openioc_profile_kedr/profile.json):
   - Add missing terms with their operators and content types.
   - Set `source` to the documentation URL.
   - Bump `profile_version`.
3. Update the golden tests in
   [`tests/test_kedr_golden.py`](../../tests/test_kedr_golden.py) to
   reflect the new expected violations for the bundled fixtures.
4. Open a pull request following the guide in
   [authoring.md](authoring.md#contributing-a-profile-to-this-repository).
