# How to write and publish a consumer profile

This guide shows how to package an OpenIOC consumer profile as a
standalone Python distribution so that it registers automatically with
the `openioc.profiles` engine via entry points.

Use [`profiles/example/`](../../profiles/example/) as a copy-paste
template.

---

## 1. Create the package layout

```
openioc-profile-<name>/            ← distribution root
    pyproject.toml
    src/
        openioc_profile_<name>/
            __init__.py
            profile.json
    tests/
        __init__.py
        test_loads.py
    README.md
```

Replace `<name>` with a short, lowercase identifier (e.g. `kedr`,
`fireeye-hx`, `acme-edr`).

---

## 2. Write the profile JSON

See [format.md](format.md) for the full schema reference.

Minimum viable profile (`profile.json`):

```json
{
  "schema_version": "1.0.0",
  "name": "acme-edr",
  "profile_version": "0.1.0",
  "target_product": "Acme EDR",
  "description": "TODO: fill in supported terms from Acme EDR documentation.",
  "source": "https://docs.acme.example/ioc-support",
  "terms": {
    "FileItem/FileName": {
      "operators": ["is", "contains"],
      "content_types": ["string"]
    }
  }
}
```

---

## 3. Write the Python loader

`src/openioc_profile_<name>/__init__.py`:

```python
from __future__ import annotations
from importlib.resources import files
from openioc.profiles import Profile

def load() -> Profile:
    text = files(__package__).joinpath("profile.json").read_text(encoding="utf-8")
    return Profile.from_json(text)
```

The `load()` function is called by the engine exactly once (result
cached in the registry).

---

## 4. Configure `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "openioc-profile-acme-edr"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["python-openioc[profiles]>=0.1"]

[project.entry-points."openioc.profiles"]
acme-edr = "openioc_profile_acme_edr:load"

[tool.hatch.build.targets.wheel]
packages = ["src/openioc_profile_acme_edr"]

[tool.hatch.build]
include = [
    "src/openioc_profile_acme_edr/**/*.py",
    "src/openioc_profile_acme_edr/profile.json",
]
```

The entry-point key (e.g. `acme-edr`) becomes the registry name passed
to `get_profile()`.  It must match the `name` field in your profile
JSON.

---

## 5. Write a smoke test

`tests/test_loads.py`:

```python
import pytest
from openioc.profiles import Profile

def test_profile_loads():
    pytest.importorskip("jsonschema")
    from openioc_profile_acme_edr import load
    profile = load()
    assert isinstance(profile, Profile)
    assert profile.name == "acme-edr"
```

---

## 6. Install and verify

```bash
cd openioc-profile-acme-edr
pip install -e ".[dev]"           # or just pip install -e .
pytest tests/

python -c "from openioc.profiles import get_profile; print(get_profile('acme-edr'))"
```

---

## 7. Publish to PyPI

```bash
pip install build
python -m build
twine upload dist/*
```

Once published, any user who runs `pip install openioc-profile-acme-edr`
and then calls `get_profile("acme-edr")` will get your profile — no
changes to the engine package required.

---

## Contributing a profile to this repository

If your profile covers a widely-used product and you want to include it
in this monorepo under `profiles/`, open a pull request with:

1. The new directory `profiles/<name>/` following the layout above.
2. A filled-in `docs/profiles/<name>.md` with:
   - target product and versions
   - link to the official constraint documentation
   - known adapter limitations
3. Passing tests (`pytest profiles/<name>/tests/`).
4. The new directory mentioned in the root `README.md` "Available profiles" section.

Profile data accuracy is the responsibility of the profile author.
The engine team reviews format compliance and test coverage, not
product-specific term lists.
