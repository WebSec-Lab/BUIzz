import sys
import time
import math
import argparse
from pathlib import Path
from multiprocessing import Pool

from playwright.sync_api import sync_playwright
from fuzzer.lib.userinteraction import mouse_click

_BASE_DIR = Path(__file__).resolve().parent

POLICY_FILES = {
    "samesite": [
        "fuzzer/test_list/samesite/samesite-test-list.txt",
        "fuzzer/test_list/samesite/samesite-test-list-need-mouse.txt",
    ],
    "csp": [
        path
        for i in range(21)
        for path in (
            f"fuzzer/test_list/csp/csp-test-list-{i}.txt",
            f"fuzzer/test_list/csp/csp-test-list-need-mouse-{i}.txt",
        )
    ],
    "csp3": [
        path
        for i in range(4)
        for path in (
            f"fuzzer/test_list/csp/csp-test-list-{i}.txt",
            f"fuzzer/test_list/csp/csp-test-list-need-mouse-{i}.txt",
        )
    ],
    "coop": [
        "fuzzer/test_list/coop/coop-test-list.txt",
        "fuzzer/test_list/coop/coop-test-list-need-mouse.txt",
    ],
    "rp": [
        "fuzzer/test_list/rp/rp-test-list.txt",
        "fuzzer/test_list/rp/rp-test-list-need-mouse.txt",
    ],
    "pp": [
        "fuzzer/test_list/pp/pp-test-list.txt",
        "fuzzer/test_list/pp/pp-test-list-need-mouse.txt",
    ],
    "sandbox": [
        "fuzzer/test_list/sandbox/sandbox-test-list.txt",
        "fuzzer/test_list/sandbox/sandbox-test-list-need-mouse.txt",
    ],
    "hsts": [
        "fuzzer/test_list/hsts/hsts-test-list.txt",
        "fuzzer/test_list/hsts/hsts-test-list-need-mouse.txt",
    ],
    "xfo": [
        "fuzzer/test_list/xfo/xfo-test-list.txt",
        "fuzzer/test_list/xfo/xfo-test-list-need-mouse.txt",
    ],
    "test": [
        "fuzzer/test_list/test/test-list.txt",
        "fuzzer/test_list/test/test-list-need-mouse.txt",
    ],
    "errors": [
        "safe_error/err-list-need-mouse.txt",
    ],
}

DEFAULT_REPORT_URLS = {
    "samesite": "https://adition.com",
    "rp":       "https://adition.com",
    "hsts":     "https://adition.com",
    "csp":      "https://attacker.com",
    "csp3":     "https://attacker.com",
    "pp":       "https://attacker.com",
    "xfo":      "http://victim.com",
    "coop":     "http://victim.com",
    "sandbox":  "http://10.20.23.182:5021",
    "test":     "http://127.0.0.1",
}

_BROWSER_EXECUTABLE = {
    "chrome":  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": None,
}

_RENEW_INTERVAL = 100


def chunk_list(data, num_chunks):
    if not data:
        return []
    size = max(1, math.ceil(len(data) / max(1, num_chunks)))
    return [data[i:i + size] for i in range(0, len(data), size)]


def _launch_browser(p, browser_name):
    if browser_name == "chrome":
        return p.chromium.launch(
            executable_path=_BROWSER_EXECUTABLE["chrome"],
            headless=False,
        )
    if browser_name == "firefox":
        return p.firefox.launch(headless=False)
    raise ValueError(f"Unsupported browser: '{browser_name}'")


def _new_context(browser):
    ctx = browser.new_context()
    ctx.set_default_timeout(4000)
    return ctx


def _fresh_session(p, browser_name):
    browser = _launch_browser(p, browser_name)
    context = _new_context(browser)
    page    = context.new_page()
    return browser, context, page


def _close_session(browser, context):
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass


def _insert_cookies(context, report_url, corpus, browser_name, security_policy):
    context.add_cookies([
        {"name": "browser_name",        "value": browser_name, "url": report_url, "sameSite": "Lax"},
        {"name": "browser_name1",       "value": browser_name, "url": report_url, "sameSite": "None", "secure": True},
        {"name": "bf",                  "value": "0",          "url": report_url, "sameSite": "Lax"},
        {"name": "bf1",                 "value": "0",          "url": report_url, "sameSite": "None", "secure": True},
        {"name": "corpus",              "value": corpus,       "url": report_url, "sameSite": "Lax"},
        {"name": "corpus1",             "value": corpus,       "url": report_url, "sameSite": "None", "secure": True},
        {"name": "number_of_scenario",  "value": "IAMCORPUS", "url": report_url, "sameSite": "Lax"},
        {"name": "number_of_scenario1", "value": "IAMCORPUS", "url": report_url, "sameSite": "None", "secure": True},
    ])
    if security_policy == "samesite":
        context.add_cookies([
            {"name": "strict", "value": "strict", "url": report_url, "sameSite": "Strict"},
            {"name": "lax",    "value": "lax",    "url": report_url, "sameSite": "Lax"},
            {"name": "secure", "value": "secure", "url": report_url, "sameSite": "None", "secure": True},
        ])


def fuzz(browser_name, url_list, report_url, security_policy, hyperlink=False):
    page_cnt = 0
    with sync_playwright() as p:
        browser, context, page = _fresh_session(p, browser_name)
        try:
            for num, url in enumerate(url_list):
                try:
                    print(f"[{num}] TEST URL: {url}")
                    _insert_cookies(context, report_url, url, browser_name, security_policy)
                    if security_policy == "hsts":
                        page.goto("https://adition.com")
                        time.sleep(0.2)
                    page.goto(url, wait_until="networkidle")
                    if "/sw/" in url:
                        try:
                            page.reload(wait_until="networkidle", timeout=5000)
                        except Exception:
                            pass
                    if hyperlink:
                        try:
                            mouse_click(page, "#a1", "left")
                        except Exception as e:
                            print(f"[debug] click failed: {e}")
                            err_path = _BASE_DIR / "safe_error" / "err-list-need-mouse.txt"
                            err_path.parent.mkdir(parents=True, exist_ok=True)
                            err_path.open("a", encoding="utf-8").write(f"{url}\n")
                    page_cnt += 1
                    time.sleep(0.3)

                except Exception as e:
                    print(f"[debug] exception: {e}")
                    _close_session(browser, context)
                    browser, context, page = _fresh_session(p, browser_name)

                if page_cnt > 0 and page_cnt % _RENEW_INTERVAL == 0:
                    print("[+] Periodic browser renew")
                    _close_session(browser, context)
                    browser, context, page = _fresh_session(p, browser_name)
        finally:
            _close_session(browser, context)


def read_test_lists(security_policy):
    if security_policy not in POLICY_FILES:
        raise ValueError(f"Unknown security policy: '{security_policy}'")

    with_hyperlink    = []
    without_hyperlink = []
    for rel_path in POLICY_FILES[security_policy]:
        path = _BASE_DIR / rel_path
        if not path.exists():
            print(f"[!] Missing file: {path}")
            continue
        entries = [
            line.strip()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip().startswith("http")
        ]
        if "mouse" in path.name:
            with_hyperlink.extend(entries)
        else:
            without_hyperlink.extend(entries)
    return with_hyperlink, without_hyperlink


def parse_args():
    parser = argparse.ArgumentParser(description="Baseline crawler")
    parser.add_argument("-r", "--report-url",      type=str)
    parser.add_argument("-b", "--browser",         type=str, required=True,
                        choices=list(_BROWSER_EXECUTABLE))
    parser.add_argument("-s", "--security-policy", type=str, required=True,
                        choices=list(DEFAULT_REPORT_URLS))
    parser.add_argument("-n", "--num-processes",   type=int, default=5,
                        help="Number of parallel processes (default: 5)")
    return parser.parse_args()


if __name__ == "__main__":
    args            = parse_args()
    browser_name    = args.browser
    security_policy = args.security_policy
    report_url      = args.report_url or DEFAULT_REPORT_URLS.get(security_policy)
    num_processes   = args.num_processes

    if report_url is None:
        print(f"[-] No default report URL for '{security_policy}'. Use -r.")
        sys.exit(1)

    try:
        with_link, without_link = read_test_lists(security_policy)
    except ValueError as e:
        print(f"[-] {e}")
        sys.exit(1)

    if not with_link and not without_link:
        print("[-] No URLs loaded — check test_list files.")
        sys.exit(1)

    no_hyperlink_chunks = chunk_list(without_link, num_processes)
    hyperlink_chunks    = chunk_list(with_link,    num_processes)

    with Pool() as pool:
        pool.starmap(fuzz, [
            (browser_name, chunk, report_url, security_policy, False)
            for chunk in no_hyperlink_chunks
        ])

    with Pool() as pool:
        pool.starmap(fuzz, [
            (browser_name, chunk, report_url, security_policy, True)
            for chunk in hyperlink_chunks
        ])
