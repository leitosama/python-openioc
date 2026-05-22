# Profile format specification

A **profile** is a JSON file describing which OpenIOC terms, operators,
content types, and structural patterns a specific consumer product
supports.  The engine validates every profile against a
[JSON Schema](../../src/openioc/profiles/schema/profile.schema.json)
before use.

## Current schema version: `1.0.0`

The `schema_version` field carries a [semver](https://semver.org/) string.
The engine checks only the **major** component: a profile with
`schema_version: "1.2.0"` will load on any engine that supports major
version 1.  A profile with `schema_version: "2.0.0"` will be rejected.

---

## Top-level fields

### `schema_version` *(required, string)*

Semver version of the profile format. Must match `^\d+\.\d+\.\d+$`.

```json
"schema_version": "1.0.0"
```

### `name` *(required, string)*

Unique, stable registry key.  Used as the argument to `get_profile()`.
Pattern: `^[a-z][a-z0-9_-]*$`.

```json
"name": "kedr"
```

### `profile_version` *(string)*

Semver version of this profile's data.  Increment when the vendor
changes their supported terms or operators.

```json
"profile_version": "2.1.0"
```

### `target_product` *(string)*

Human-readable product name.

```json
"target_product": "Kaspersky Anti Targeted Attack — KEDR"
```

### `target_versions` *(string or array of strings)*

Product version(s) these constraints apply to.  Informational only —
the engine does not interpret this field.

```json
"target_versions": ["5.x", "6.x"]
```

### `description` *(string)*

Free-form description.  Use this field where you would otherwise put a
JSON comment (JSON does not support comments).

### `source` *(string)*

URL of the official documentation that defines these constraints.

---

## `terms` *(object)*

Keys are `Context.search` strings — the exact value stored in an
`IndicatorItem.context.search` field, e.g. `"FileItem/FileName"`.

Omit the `terms` object entirely (or leave it empty `{}`) to allow **all
terms** without restriction.

Each value is an object with:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `operators` | **yes** | `string[]` | Allowed `condition` values (e.g. `"is"`, `"contains"`, `"matches"`). |
| `content_types` | no | `string[]` | Allowed `Content.content_type` values. Omit to allow any. |
| `description` | no | string | Human-readable note. |

Valid operator values come from the OpenIOC 1.0/1.1 vocabularies:

- **1.0**: `is`, `isnot`, `contains`, `containsnot`
- **1.1**: `is`, `contains`, `matches`, `starts-with`, `ends-with`, `greater-than`, `less-than`

Example:

```json
"terms": {
  "FileItem/FileName": {
    "operators": ["is", "contains", "matches"],
    "content_types": ["string"],
    "description": "Name (not full path) of a file."
  },
  "FileItem/Md5sum": {
    "operators": ["is"],
    "content_types": ["md5"]
  }
}
```

---

## `structure` *(object)*

Structural constraints on the indicator tree.  All sub-fields are
optional; defaults impose no restrictions.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_nesting` | integer ≥ 1 | *(no limit)* | Maximum depth of `Indicator` nesting. Root = depth 1. |
| `allow_or_at_top_level` | boolean | `true` | Whether the root `Indicator` may use the OR operator. |
| `allow_or_inside_and` | boolean | `true` | Whether an OR `Indicator` may appear inside an AND. |
| `allow_and_inside_or` | boolean | `true` | Whether an AND `Indicator` may appear inside an OR. |

Example (KEDR-style):

```json
"structure": {
  "max_nesting": 5,
  "allow_or_at_top_level": true,
  "allow_or_inside_and": true,
  "allow_and_inside_or": true
}
```

---

## `mappings` *(object, reserved)*

Term-rewrite hints for the adapter.  Keys and values are
`Context.search` strings.  Reserved for future use — the v1 engine
stores the mapping but does not apply it.

```json
"mappings": {
  "OldItem/LegacyField": "NewItem/ModernField"
}
```

---

## Minimal valid profile

```json
{
  "schema_version": "1.0.0",
  "name": "my-product"
}
```

This profile imposes no restrictions whatsoever (empty `terms` = all
terms allowed, no `structure` = no structural limits).

---

## Full example

```json
{
  "schema_version": "1.0.0",
  "name": "acme-edr",
  "profile_version": "1.0.0",
  "target_product": "Acme EDR",
  "target_versions": ["3.x", "4.x"],
  "description": "Supported OpenIOC terms for Acme EDR 3.x/4.x.",
  "source": "https://docs.acme.example/ioc-support",
  "terms": {
    "FileItem/FileName": {
      "operators": ["is", "contains", "matches"],
      "content_types": ["string"]
    },
    "FileItem/Md5sum": {
      "operators": ["is"],
      "content_types": ["md5"]
    },
    "RegistryItem/Path": {
      "operators": ["is", "contains"],
      "content_types": ["string"]
    }
  },
  "structure": {
    "max_nesting": 4,
    "allow_or_at_top_level": true,
    "allow_or_inside_and": true,
    "allow_and_inside_or": false
  }
}
```
