import sys
import time
import math
import argparse
from pathlib import Path
from multiprocessing import Pool

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait

_BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(_BASE_DIR))
from fuzzerV2.lib.core_common import load_browser_info, make_chromium_service, get_browser_exe
from fuzzerV2.lib.userinteraction import mouse_click

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
}

DEFAULT_REPORT_URLS = {
    "samesite": "https://adition.com",
    "rp":       "https://adition.com",
    "hsts":     "https://adition.com",
    "csp":      "https://attacker.com",
    "pp":       "https://attacker.com",
    "xfo":      "http://victim.com",
    "coop":     "http://victim.com",
    "sandbox":  "http://10.20.23.182:5021",
    "test":     "http://127.0.0.1",
}

_RENEW_INTERVAL  = 100
_NETWORK_SETTLE  = 1.0
_PAGE_LOAD_TIMEOUT = 10


def chunk_list(data, num_chunks):
    if not data:
        return []
    size = max(1, math.ceil(len(data) / max(1, num_chunks)))
    return [data[i:i + size] for i in range(0, len(data), size)]


def _resolve_gecko_path():
    try:
        from webdriver_manager.firefox import GeckoDriverManager
        path = GeckoDriverManager().install()
        print(f"[+] GeckoDriver -> {path}")
        return path
    except Exception as e:
        print(f"[debug] GeckoDriverManager failed: {e}, using default")
        return None


def _launch_driver(browser_name, gecko_path=None):
    exe = get_browser_exe(browser_name)

    if browser_name == "firefox":
        options = FirefoxOptions()
        options.binary_location = exe
        options.accept_insecure_certs = True
        service = FirefoxService(gecko_path) if gecko_path else FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)
    else:
        options = ChromeOptions()
        options.binary_location = exe
        options.add_argument("--no-sandbox")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-extensions")
        service = make_chromium_service(exe)
        driver = webdriver.Chrome(service=service, options=options)

    driver.set_page_load_timeout(_PAGE_LOAD_TIMEOUT)
    return driver


def _insert_cookies(driver, corpus, browser_name, security_policy):
    driver.delete_all_cookies()
    cookies = [
        {"name": "browser_name",        "value": browser_name,  "sameSite": "Lax"},
        {"name": "browser_name1",       "value": browser_name,  "sameSite": "None", "secure": True},
        {"name": "bf",                  "value": "0",           "sameSite": "Lax"},
        {"name": "bf1",                 "value": "0",           "sameSite": "None", "secure": True},
        {"name": "corpus",              "value": corpus,        "sameSite": "Lax"},
        {"name": "corpus1",             "value": corpus,        "sameSite": "None", "secure": True},
        {"name": "number_of_scenario",  "value": "IAMCORPUS",  "sameSite": "Lax"},
        {"name": "number_of_scenario1", "value": "IAMCORPUS",  "sameSite": "None", "secure": True},
    ]
    if security_policy == "samesite":
        cookies += [
            {"name": "strict", "value": "strict", "sameSite": "Strict"},
            {"name": "lax",    "value": "lax",    "sameSite": "Lax"},
            {"name": "secure", "value": "secure",  "sameSite": "None", "secure": True},
        ]
    for c in cookies:
        try:
            driver.add_cookie(c)
        except Exception as e:
            print(f"[debug] add_cookie failed ({c['name']}): {e}")




def _wait_for_ready(driver, timeout=8):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass


def _wait_for_load(driver, timeout=8):
    _wait_for_ready(driver, timeout)
    time.sleep(_NETWORK_SETTLE)


def fuzz(browser_name, url_list, report_url, security_policy, hyperlink=False, gecko_path=None):
    driver = _launch_driver(browser_name, gecko_path)
    page_cnt = 0

    try:
        for num, url in enumerate(url_list):
            try:
                print(f"[{num}] TEST URL: {url}")

                try:
                    driver.get(report_url)
                    _wait_for_load(driver, timeout=4)
                except Exception:
                    pass

                _insert_cookies(driver, url, browser_name, security_policy)

                if security_policy == "hsts":
                    driver.get("https://adition.com")
                    time.sleep(0.2)

                try:
                    driver.get(url)
                except Exception:
                    pass
                _wait_for_ready(driver)

                if hyperlink:
                    clicked = mouse_click(driver, "#a1", debug=True)
                    if not clicked:
                        print(f"[debug] click failed: #a1 not found url={url}")
                        err_path = _BASE_DIR / "safe_error" / "err-list-need-mouse.txt"
                        err_path.parent.mkdir(parents=True, exist_ok=True)
                        with err_path.open("a", encoding="utf-8") as f:
                            f.write(f"{url}\n")
                    else:
                        time.sleep(0.3)

                time.sleep(_NETWORK_SETTLE)

                if "/sw/" in url:
                    try:
                        driver.refresh()
                        _wait_for_load(driver)
                    except Exception:
                        pass

                page_cnt += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"[debug] exception: {e}")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = _launch_driver(browser_name, gecko_path)
                page_cnt = 0

            if page_cnt > 0 and page_cnt % _RENEW_INTERVAL == 0:
                print("[+] Periodic browser renew")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = _launch_driver(browser_name, gecko_path)
                page_cnt = 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


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
    parser = argparse.ArgumentParser(description="Baseline crawler (Selenium)")
    parser.add_argument("-r", "--report-url",      type=str)
    parser.add_argument("-b", "--browser",         type=str, required=True,
                        choices=["chrome", "firefox", "edge", "opera", "brave", "whale"])
    parser.add_argument("-s", "--security-policy", type=str, required=True,
                        choices=list(DEFAULT_REPORT_URLS))
    parser.add_argument("-n", "--num-processes",   type=int, default=1,
                        help="Number of parallel processes (default: 1)")
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

    gecko_path = _resolve_gecko_path() if browser_name == "firefox" else None

    no_hyperlink_chunks = chunk_list(without_link, num_processes)
    hyperlink_chunks    = chunk_list(with_link,    num_processes)

    with Pool(processes=num_processes) as pool:
        pool.starmap(fuzz, [
            (browser_name, chunk, report_url, security_policy, False, gecko_path)
            for chunk in no_hyperlink_chunks
        ])

    with Pool(processes=num_processes) as pool:
        pool.starmap(fuzz, [
            (browser_name, chunk, report_url, security_policy, True, gecko_path)
            for chunk in hyperlink_chunks
        ])
