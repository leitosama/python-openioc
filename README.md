# python-openioc

Full CRUD support for [OpenIOC](https://en.wikipedia.org/wiki/Open_Indicators_of_Compromise) 1.0 and 1.1 in pure Python.

OpenIOC is an XML-based open standard, originally published by Mandiant, for
describing **indicators of compromise** — file hashes, IP addresses, registry
keys, DNS lookups, and other technical artefacts that suggest a host has been
compromised. `python-openioc` reads, builds, writes, validates, and upgrades
those documents from a small, typed dataclass model.

The library targets Python 3.10+, ships type stubs (mypy-strict), and depends
only on `lxml` at runtime.

## Features

- **Read** OpenIOC 1.0 and 1.1 documents from a file path, an XML string, or
  raw bytes.
- **Auto-detect** the format version by peeking at the root element so callers
  rarely need to pass `version=`.
- **Build** IOCs programmatically using dataclasses (`IOC`, `Indicator`,
  `IndicatorItem`, `Context`, `Content`, `Metadata`, `Link`, `Parameter`).
- **Write** an in-memory IOC back to XML, in either 1.0 or 1.1, with optional
  pretty-printing.
- **Validate** structurally and against the bundled XSD schemas. The v1.0
  validator additionally checks that condition strings are within the 1.0
  vocabulary (the 1.0 XSD declares the attribute as a free string).
- **Convert** 1.0 documents to 1.1, mapping `isnot`/`containsnot` to
  `(is|contains, negate=true)`, filling in missing UUIDs, and deriving
  `published-date` from the chain `created_date -> last_modified`.
- **Hardened parser** with external-entity resolution, network access, and
  huge-tree expansion all disabled out of the box — safer to point at
  untrusted IOC files.

## Installation

The library is not yet on PyPI. Install editable from the repository:

```bash
git clone https://github.com/leitosama/python-openioc.git
cd python-openioc
pip install -e .
```

Requirements:

- Python **3.10** or newer
- `lxml >= 4.9`

## Quick start

### Read a document

```python
import openioc

# Auto-detects 1.0 vs 1.1 from the root element.
ioc = openioc.read("tests/fixtures/v11/sharpstomp.ioc")

print(ioc.format_version)        # "1.1"
print(ioc.metadata.short_description)
print(len(ioc.definition.children))
```

`read()` accepts a file path, an XML string (one that starts with `<`), or
raw bytes. Pass `version="1.0"` or `version="1.1"` to skip auto-detection.

### Build one programmatically

```python
import uuid
import openioc

ioc = openioc.IOC(
    id=str(uuid.uuid4()),
    metadata=openioc.Metadata(
        short_description="Suspicious EXE on disk",
        authored_by="alice",
        authored_date="2026-05-21T00:00:00",
    ),
    definition=openioc.Indicator(
        id=str(uuid.uuid4()),
        operator=openioc.IndicatorOperator.AND,
        children=[
            openioc.IndicatorItem(
                id=str(uuid.uuid4()),
                context=openioc.Context(
                    document="FileItem",
                    search="FileItem/FileName",
                ),
                content=openioc.Content(value="evil.exe"),
                condition="is",
            ),
        ],
    ),
    last_modified="2026-05-21T00:00:00",
    published_date="2026-05-21T00:00:00",
    format_version="1.1",
)
```

### Write

```python
# To bytes (returns UTF-8 XML with a declaration).
xml_bytes = openioc.write(ioc)

# To a file (returns None).
openioc.write(ioc, "out.ioc")

# Force a specific format regardless of ioc.format_version.
openioc.write(ioc, "out-v10.ioc", version="1.0")

# Compact output.
xml_bytes = openioc.write(ioc, pretty_print=False)
```

### Validate

```python
from openioc import ValidationError

try:
    openioc.validate(ioc)
except ValidationError as exc:
    print(exc.source_format)  # "1.0" or "1.1"
    for err in exc.errors:
        print(" -", err)
```

`validate()` dispatches by `ioc.format_version`; `validate_10()` and
`validate_11()` are also exposed when the format is known.

### Convert 1.0 to 1.1

```python
v10 = openioc.read("legacy.ioc", version="1.0")
v11 = openioc.convert_10_to_11(v10)
openioc.write(v11, "upgraded.ioc")
```

Conversion deep-copies the input — the original IOC is never mutated.

## Public API

| Symbol                                     | Purpose                                                            |
|--------------------------------------------|--------------------------------------------------------------------|
| `IOC`                                      | Top-level document dataclass.                                      |
| `Indicator`                                | Boolean combinator node (`AND` / `OR`) in the criteria tree.       |
| `IndicatorItem`                            | Leaf node — an atomic match condition.                             |
| `Context`                                  | Where to look (document type + field reference).                   |
| `Content`                                  | What to match against (literal value + type).                      |
| `Metadata`                                 | Document metadata (description, keywords, links, ...).             |
| `Link`                                     | External reference inside `Metadata.links`.                        |
| `Parameter`                                | 1.1-only named parameter attached to an indicator.                 |
| `IndicatorOperator`                        | `AND` / `OR` enum.                                                 |
| `Condition10`                              | 1.0 condition vocabulary.                                          |
| `Condition11`                              | 1.1 condition vocabulary.                                          |
| `read(source, *, version=None)`            | Parse a file path, string, or bytes into an `IOC`.                 |
| `write(ioc, dest=None, *, version, ...)`   | Serialise to bytes (when `dest is None`) or to a file.             |
| `convert_10_to_11(ioc)`                    | Upgrade a 1.0 IOC to 1.1 (returns a new object).                   |
| `validate(ioc)`                            | Dispatch to `validate_10` / `validate_11` by `format_version`.     |
| `validate_10(ioc)` / `validate_11(ioc)`    | Structural + XSD validation against the bundled schema.            |
| `OpenIOCError`                             | Base exception class.                                              |
| `ParseError`                               | Raised on malformed XML or missing required elements.              |
| `ValidationError`                          | Raised on structural / XSD failure; `.errors` holds the findings.  |
| `ConversionError`                          | Raised when `convert_10_to_11` cannot proceed.                     |
| `WriteError`                               | Raised when required fields are missing for the target format.     |

See the module docstrings and inline docstrings (Google style) for details
on each symbol.

## Project layout

```
src/openioc/
    __init__.py       Public API: read, write, convert, validate, exceptions, models.
    constants.py      Namespace URIs, IndicatorOperator, Condition10, Condition11.
    exceptions.py     OpenIOCError hierarchy.
    models.py         Dataclasses representing the OpenIOC object model.
    convert.py        1.0 -> 1.1 conversion.
    validator.py      Structural + XSD validation.
    v10/
        reader.py     IOCv10Reader.
        writer.py     IOCv10Writer.
        schema/
            ioc.xsd   Bundled OpenIOC 1.0 XSD.
    v11/
        reader.py     IOCv11Reader.
        writer.py     IOCv11Writer.
        schema/
            ioc.xsd   Bundled OpenIOC 1.1 XSD.

tests/                pytest suite, including round-trip tests against real
                      Operation Windigo (v1.0) and SHARPSTOMP (v1.1) IOCs.
```

## Development

Set up a development environment:

```bash
git clone https://github.com/leitosama/python-openioc.git
cd python-openioc
pip install -e ".[dev]"
pre-commit install
```

Run the standard checks (all three are also run in CI on Python 3.10, 3.11,
and 3.12):

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/openioc
pytest tests/ -v --cov=openioc --cov-report=term-missing
```

The project enforces strict mypy (`disallow_untyped_defs`,
`disallow_incomplete_defs`) and ruff with `E`, `W`, `F`, `I`, `UP`, `B`,
`SIM`, `C4` rule groups.

## Conventions

- **Empty strings as "not set":** optional `str` fields in the model use
  `""` rather than `None`. Check truthiness (`if ioc.last_modified:`) rather
  than `is None`. The v1.1 writer treats `IOC.created_date` as a fallback
  for `last_modified` and `published_date` when those are empty.
- **Synthetic OR root:** when a document contains multiple top-level
  `<Indicator>` children, the reader wraps them in an `OR` Indicator with a
  generated UUID so the in-memory model always has a single root.
- **1.0 ↔ 1.1 differences:** the v1.0 writer silently drops
  `IndicatorItem.negate`, `preserve_case`, `created_date`, `published_date`,
  and the `parameters` list (none of which exist in the 1.0 schema). The
  v1.1 writer silently drops `IndicatorItem.comment` for the same reason.

## Versioning and status

Current version: **0.1.0** (alpha). The public API may still change in
backward-incompatible ways before 1.0.

## License

Released under the Apache License 2.0 — see [LICENSE](LICENSE) for the full
text.
