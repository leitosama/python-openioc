"""End-to-end example: validate and adapt an IOC against the KEDR profile.

Prerequisites::

    pip install -e ".[profiles]"
    pip install -e profiles/kedr

Run::

    python examples/profiles_e2e.py

The script reads the bundled SHARPSTOMP fixture, validates it against the
KEDR profile, then adapts it with the drop policy and writes the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "v11" / "sharpstomp.ioc"
OUTPUT = Path("/tmp/sharpstomp_kedr_adapted.ioc")

import openioc
from openioc.profiles import (
    AdapterPolicy,
    ProfileAdapter,
    ProfileValidator,
    get_profile,
)
from openioc.profiles.exceptions import AdaptationFailed


def main() -> int:
    print("=== OpenIOC Profile Subsystem — end-to-end demo ===\n")

    # 1. Load the IOC.
    ioc = openioc.read(FIXTURE)
    print(f"Loaded IOC: {ioc.metadata.short_description!r}")
    print(f"Format: {ioc.format_version}, id: {ioc.id}\n")

    # 2. Resolve the KEDR profile via entry-point discovery.
    try:
        profile = get_profile("kedr")
    except Exception as exc:
        print(f"Could not load KEDR profile: {exc}")
        print("Install it with: pip install -e profiles/kedr")
        return 1

    print(f"Profile: {profile.name} v{profile.profile_version}")
    print(f"Target: {profile.target_product}, versions {profile.target_versions}\n")

    # 3. Validate.
    report = ProfileValidator(profile).validate(ioc)
    if report.violations:
        print(f"Found {len(report.violations)} violation(s):")
        for v in report.violations[:10]:
            print(f"  [{v.severity.value.upper()}] {v.code.value}: {v.message}")
            print(f"    at {v.location}")
        if len(report.violations) > 10:
            print(f"  … and {len(report.violations) - 10} more")
    else:
        print("IOC is fully compatible with the KEDR profile.")
    print()

    # 4. Adapt (drop policy).
    print("Adapting with drop_unsupported_items=True …")
    try:
        result = ProfileAdapter(profile, AdapterPolicy(drop_unsupported_items=True)).adapt(ioc)
    except AdaptationFailed as exc:
        print(f"Adaptation failed: {exc}")
        return 1

    print(f"Applied {len(result.changes)} change(s):")
    for change in result.changes[:10]:
        print(f"  {change.action}: {change.details.get('term', '')} at {change.location}")
    if len(result.changes) > 10:
        print(f"  … and {len(result.changes) - 10} more")

    if result.residual.violations:
        print(f"\nResidual violations after adaptation: {len(result.residual.violations)}")
    else:
        print("\nAdapted IOC is fully compatible.")

    # 5. Write the adapted IOC.
    openioc.write(result.ioc, OUTPUT)
    print(f"\nAdapted IOC written to: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
