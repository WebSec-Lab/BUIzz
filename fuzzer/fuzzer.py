import pyautogui
import argparse
import sys
import re
import importlib
import pkgutil
from types import MethodType
from pathlib import Path
from lib.core_chrome  import run as run_chrome
from lib.core_edge    import run as run_edge
from lib.core_opera   import run as run_opera
from lib.core_whale   import run as run_whale
from lib.core_brave   import run as run_brave
from lib.core_firefox import run as run_firefox

pyautogui.FAILSAFE = False

BROWSER_UI_OFFSETS = {
    "opera":   (67, 90),
    "firefox": (10, 80),
    "brave":   (3, 85),
}
_DEFAULT_UI_OFFSET = (3, 80)

DEFAULT_REPORT_URLS = {
    "samesite": "https://adition.com",
    "rp":       "https://adition.com",
    "hsts":     "https://adition.com",
    "csp1":      "https://attacker.com",
    "csp2":      "https://attacker.com",
    "csp_test":  "https://attacker.com",
    "csp_test1": "https://attacker.com",
    "csp_test2": "https://attacker.com",
    "pp":       "https://attacker.com",
    "xfo":      "http://victim.com",
    "coop":     "http://victim.com",
    "sandbox":  "http://10.20.23.182:5021",
    "test":     "http://127.0.0.1",
}

BROWSER_RUNNERS = {
    "chrome":  run_chrome,
    "edge":    run_edge,
    "opera":   run_opera,
    "whale":   run_whale,
    "brave":   run_brave,
    "firefox": run_firefox,
}


class CVE:
    def __init__(self, browser_name, lib_path="cve_lib"):
        self.interactions = {}
        self._load(browser_name, lib_path)

    def register(self, name, func):
        self.interactions[name] = func
        setattr(self, name, MethodType(func, self))

    def _load(self, browser_name, path):
        p = Path(path).resolve()
        parent = str(p.parent)
        pkg    = p.name
        if parent not in sys.path:
            sys.path.insert(0, parent)
        for _, module_name, _ in pkgutil.iter_modules([str(p)]):
            if module_name not in ("common_issue", browser_name):
                continue
            module = importlib.import_module(f"{pkg}.{module_name}")
            if hasattr(module, "register"):
                module.register(self)

    def list_interactions(self):
        return list(self.interactions.keys())


def _scenario_sort_key(filename):
    m = re.match(r"(\d+)", filename)
    return int(m.group(1)) if m else 0


def list_scenario_files(subdir):
    target_dir = (Path(__file__).resolve().parent / subdir).resolve()
    if not target_dir.exists():
        raise FileNotFoundError(f"Scenario directory not found: {target_dir}")
    files = sorted(
        [f.name for f in target_dir.iterdir() if f.is_file()],
        key=_scenario_sort_key,
    )
    print(f"[+] Number of scenarios: {len(files)}")
    return files


def parse_args():
    parser = argparse.ArgumentParser(description="Browser Fuzzer execution script")
    parser.add_argument(
        "-r", "--report-url",
        type=str,
        help="Report server URL (overrides default for the chosen security policy)",
    )
    parser.add_argument(
        "-b", "--browser",
        type=str,
        required=True,
        choices=list(BROWSER_RUNNERS),
        help="Target browser name",
    )
    parser.add_argument(
        "-s", "--security-policy",
        type=str,
        required=True,
        choices=list(DEFAULT_REPORT_URLS),
        help="Target security policy",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    browser_name     = args.browser
    security_policy  = args.security_policy
    report_url       = args.report_url or DEFAULT_REPORT_URLS.get(security_policy)

    if report_url is None:
        print(f"[-] No default report URL for policy '{security_policy}'. Provide one via -r.")
        sys.exit(1)

    offset_x, offset_y = BROWSER_UI_OFFSETS.get(browser_name, _DEFAULT_UI_OFFSET)

    subdir = f"scenario/{browser_name}/{security_policy}"
    files  = list_scenario_files(subdir)

    cve    = CVE(browser_name, lib_path=str(Path(__file__).resolve().parent / "cve_lib"))
    runner = BROWSER_RUNNERS[browser_name]
    runner(subdir, files, cve, report_url, offset_x, offset_y, browser_name, security_policy)
