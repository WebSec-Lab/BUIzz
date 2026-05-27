#!/usr/bin/env python3
"""
mini_scenario.py — Copy pre-selected example scenarios into the fuzzer's
                   scenario directory so that fuzzer.py can run immediately.

Usage:
    python example/mini_scenario.py 1    # SameSite split-view bug
    python example/mini_scenario.py 2    # CSP split-view (blob:) bug
    python example/mini_scenario.py 3    # CSP split-view (data:) bug

Run from the repository root (BUIZZ/).
"""

import sys
import shutil
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent   # BUIZZ/
EXAMPLE_DIR = Path(__file__).resolve().parent          # BUIZZ/example/
SCENARIO_DIR = BASE_DIR / "fuzzer" / "scenario"

# ── Scenario set definitions ──────────────────────────────────────────────────
# Each entry: (label, src relative to EXAMPLE_DIR, dst relative to SCENARIO_DIR)
_SETS = {
    1: (
        "SameSite split-view bug (bug_20)",
        EXAMPLE_DIR / "samesite_split" / "brave" / "samesite",
        SCENARIO_DIR / "brave" / "samesite",
    ),
    2: (
        "CSP split-view blob: bug (bug_07)",
        EXAMPLE_DIR / "csp_split_blob" / "brave" / "csp1",
        SCENARIO_DIR / "brave" / "csp1",
    ),
    3: (
        "CSP split-view data: bug (bug_06)",
        EXAMPLE_DIR / "csp_split_data" / "scenario" / "brave" / "csp1",
        SCENARIO_DIR / "brave" / "csp1",
    ),
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("1", "2", "3"):
        print("Usage: python example/mini_scenario.py <1|2|3>")
        print()
        for num, (label, src, dst) in _SETS.items():
            print(f"  {num}  {label}")
        sys.exit(1)

    num = int(sys.argv[1])
    label, src, dst = _SETS[num]

    print(f"[mini_scenario] Set {num}: {label}")
    print(f"  src : {src.relative_to(BASE_DIR)}")
    print(f"  dst : {dst.relative_to(BASE_DIR)}")

    if not src.exists():
        print(f"  [ERROR] source directory not found: {src}")
        sys.exit(1)

    files = list(src.glob("*.json"))
    if not files:
        print(f"  [ERROR] no .json files in source directory.")
        sys.exit(1)

    dst.mkdir(parents=True, exist_ok=True)

    copied = 0
    for f in sorted(files):
        shutil.copy2(f, dst / f.name)
        copied += 1

    print(f"  [OK] copied {copied} scenario file(s) → {dst.relative_to(BASE_DIR)}")
    print()
    print("Next steps:")

    if num == 1:
        print("  python base_line.py  -s samesite -b chrome")
        print("  python fuzzer/fuzzer.py -s samesite -b brave")
        print("  python analyzer.py   -s samesite -b brave")
        print("  python deduping.py   -s samesite -b brave")
    else:
        policy_flag = "csp1"
        print(f"  python base_line.py  -s {policy_flag} -b chrome")
        print(f"  python fuzzer/fuzzer.py -s {policy_flag} -b brave")
        print(f"  python analyzer.py   -s {policy_flag} -b brave")
        print(f"  python deduping.py   -s {policy_flag} -b brave")


if __name__ == "__main__":
    main()
