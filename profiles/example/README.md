# openioc-profile-example

Minimal demo profile for [python-openioc](https://github.com/leitosama/python-openioc).

This package exists to:

1. Demonstrate how to publish a consumer profile as a standalone
   `openioc-profile-*` package (see
   [docs/profiles/authoring.md](../../docs/profiles/authoring.md)).
2. Serve as an integration-test fixture for the entry-point discovery
   mechanism in `openioc.profiles`.

It is **not** a real product profile.

## Installation

```bash
pip install -e .
```

Or, from the monorepo root:

```bash
pip install -e profiles/example
```

## Usage

```python
from openioc.profiles import get_profile

profile = get_profile("example")
print(profile.name, profile.profile_version)
```

## Profile contents

Covers three terms (`FileItem/FileName`, `FileItem/Md5sum`,
`RegistryItem/Path`) with a small set of operators and a `max_nesting`
of 3.  See [profile.json](src/openioc_profile_example/profile.json) for
the full definition.
