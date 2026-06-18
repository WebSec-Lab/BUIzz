"""
Baseline collection scoped to the scenario files currently in fuzzer/scenario/.

Reads fuzzer/scenario/<fuzzer_browser>/<policy>/*.json to get the corpus URLs,
then visits each one using the baseline browser (chrome, or firefox when the
fuzzer browser is firefox) — mirroring the logic in analyzer.py.

Usage:
    python scenario_base_line.py -b whale  -s csp1
    python scenario_base_line.py -b brave  -s samesite
    python scenario_base_line.py -b firefox -s coop
"""

import sys
import json
import argparse
from pathlib import Path

# Allow imports from the project root (BUIZZ/) regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base_line import fuzz, DEFAULT_REPORT_URLS, _BASE_DIR

_SCENARIO_DIR = _BASE_DIR / "fuzzer" / "scenario"

# scenario policy name (directory) -> base_line policy name (used by fuzz())
_POLICY_NORM = {
    "csp1":      "csp",
    "csp2":      "csp",
    "csp_test":  "csp",
    "csp_test1": "csp",
    "csp_test2": "csp",
}

# scenario policy name -> report URL
_REPORT_URLS = {
    **DEFAULT_REPORT_URLS,
    "csp1":      DEFAULT_REPORT_URLS["csp"],
    "csp2":      DEFAULT_REPORT_URLS["csp"],
    "csp_test":  DEFAULT_REPORT_URLS["csp"],
    "csp_test1": DEFAULT_REPORT_URLS["csp"],
    "csp_test2": DEFAULT_REPORT_URLS["csp"],
}

_FUZZER_BROWSERS = ["chrome", "edge", "firefox", "whale", "opera", "brave"]


def load_scenario_urls(fuzzer_browser, policy):
    """Read scenario JSONs and split corpus URLs into hyperlink / no-hyperlink lists."""
    scen_dir = _SCENARIO_DIR / fuzzer_browser / policy
    if not scen_dir.exists():
        raise FileNotFoundError(f"Scenario directory not found: {scen_dir}")

    with_hyperlink    = []
    without_hyperlink = []

    for path in sorted(scen_dir.glob("*.json"),
                       key=lambda p: int(p.stem.split("_")[0])):
        data    = json.loads(path.read_text(encoding="utf-8"))
        corpus  = data.get("corpus", "")
        actions = data.get("useraction", [])
        if any(a.get("tag") == "#a1" for a in actions):
            with_hyperlink.append(corpus)
        else:
            without_hyperlink.append(corpus)

    return with_hyperlink, without_hyperlink


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scenario-scoped baseline crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-r", "--report-url", type=str,
                        help="Override report server URL")
    parser.add_argument("-b", "--browser", type=str, required=True,
                        choices=_FUZZER_BROWSERS,
                        help="Fuzzer browser (same as fuzzer.py -b). "
                             "Baseline runs on chrome (or firefox if browser=firefox).")
    parser.add_argument("-s", "--security-policy", type=str, required=True,
                        help="Policy name matching the scenario directory (e.g. csp1, samesite)")
    return parser.parse_args()


if __name__ == "__main__":
    args            = parse_args()
    fuzzer_browser  = args.browser
    security_policy = args.security_policy
    baseline_browser = "firefox" if fuzzer_browser == "firefox" else "chrome"
    baseline_policy  = _POLICY_NORM.get(security_policy, security_policy)
    report_url       = args.report_url or _REPORT_URLS.get(security_policy)

    if report_url is None:
        print(f"[-] No default report URL for '{security_policy}'. Use -r.")
        sys.exit(1)

    try:
        with_link, without_link = load_scenario_urls(fuzzer_browser, security_policy)
    except FileNotFoundError as e:
        print(f"[-] {e}")
        sys.exit(1)

    total = len(with_link) + len(without_link)
    if total == 0:
        print("[-] No scenario files found.")
        sys.exit(1)

    print(f"[+] Fuzzer browser  : {fuzzer_browser}")
    print(f"[+] Baseline browser: {baseline_browser}")
    print(f"[+] {len(without_link)} no-hyperlink + {len(with_link)} hyperlink URLs (total {total})")

    if without_link:
        fuzz(baseline_browser, without_link, report_url, baseline_policy, hyperlink=False)
    if with_link:
        fuzz(baseline_browser, with_link, report_url, baseline_policy, hyperlink=True)
