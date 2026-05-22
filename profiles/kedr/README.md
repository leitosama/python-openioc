# openioc-profile-kedr

[KATA KEDR](https://www.kaspersky.com/enterprise-security/anti-targeted-attack-platform)
consumer profile for
[python-openioc](https://github.com/leitosama/python-openioc).

> **Status**: work-in-progress stub. The term list is based on commonly
> supported OpenIOC indicators for EDR products. The full, authoritative
> list of KEDR-supported terms will be added once official documentation
> is available. See [docs/profiles/kedr.md](../../docs/profiles/kedr.md)
> for details and how to contribute corrections.

## Installation

```bash
pip install -e profiles/kedr          # from the monorepo root
```

## Usage

```python
from openioc import read
from openioc.profiles import get_profile, ProfileValidator, ProfileAdapter, AdapterPolicy

ioc = read("indicator.ioc")
profile = get_profile("kedr")

report = ProfileValidator(profile).validate(ioc)
for v in report.violations:
    print(v.severity.value, v.code.value, v.location, "—", v.message)

if report.has_errors():
    result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
    from openioc import write
    write(result.ioc, "indicator.kedr.ioc")
```

## Profile contents

Covers the following indicator categories (stub list):

- **FileItem** — FileName, FullPath, Md5sum, Sha1sum, Sha256sum
- **RegistryItem** — Path, ValueName, Value
- **PortItem** — localPort, remoteIP
- **ProcessItem** — name, path

See [profile.json](src/openioc_profile_kedr/profile.json) for the
complete definition.
