import time
from pathlib import Path
from pywinauto import Application
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .core_common import (
    check_browserx_browsery, execution, reset_to_single_tab,
    load_scenario, close_browser, get_browser_pid_with_window,
    get_browser_exe, make_chromium_service, force_window_position,
    reposition_if_offscreen, _SCENARIO_TIMEOUT,
)

_PROCESS_NAME     = "opera.exe"
_RESTART_SLEEP    = 4
_RESTART_INTERVAL = 50

_PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles" / "opera"


def _start_browser(browser_name):
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = get_browser_exe(browser_name)
    options.add_argument(f"--user-data-dir={_PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-position=0,0")
    options.add_argument("--window-size=1280,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    exe = get_browser_exe(browser_name)
    options.binary_location = exe
    service = make_chromium_service(exe)
    driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)
    time.sleep(1.5)
    pid = get_browser_pid_with_window(_PROCESS_NAME)
    app = Application(backend="uia").connect(process=pid)
    return app, driver


def _fresh_session(browser_name):
    app, driver = _start_browser(browser_name)
    reset_to_single_tab(driver)
    force_window_position(app)
    browser_x, browser_y = check_browserx_browsery(app)
    return app, driver, browser_x, browser_y


def _restart(browser_name, app, driver):
    try:
        driver.quit()
    except Exception:
        pass
    close_browser(app)
    time.sleep(_RESTART_SLEEP)
    return _fresh_session(browser_name)


def run(subdir, files, cve, report_url, offset_x, offset_y, browser_name, security_policy):
    page_cnt   = 0
    start_time = time.time()
    app = driver = None

    try:
        app, driver, browser_x, browser_y = _fresh_session(browser_name)

        for f in files:
            print(f"\n[--------] TEST scenario : {subdir}/{f} [--------]")
            reposition_if_offscreen(app)
            try:
                scenario = load_scenario(f"{subdir}/{f}")
                scenario_start = time.time()
                execution(
                    driver, scenario, cve, report_url,
                    offset_x, offset_y,
                    browser_name, f, app, security_policy,
                )
                if time.time() - scenario_start > _SCENARIO_TIMEOUT:
                    print(f"[!] Scenario took >{_SCENARIO_TIMEOUT}s — restarting browser")
                    app, driver, browser_x, browser_y = _restart(browser_name, app, driver)
                    continue
                time.sleep(1)
                reset_to_single_tab(driver)
                page_cnt += 1

                if page_cnt % _RESTART_INTERVAL == 0:
                    print("[+] Periodic browser restart")
                    app, driver, browser_x, browser_y = _restart(browser_name, app, driver)
                else:
                    browser_x, browser_y = check_browserx_browsery(app)

            except Exception as e:
                print(f"[debug] scenario error: {e}")
                try:
                    app, driver, browser_x, browser_y = _restart(browser_name, app, driver)
                except Exception as re:
                    print(f"[debug] restart failed: {re}")

    except Exception as e:
        print(f"[debug] : {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        if app:
            close_browser(app)

    end_time = time.time()
    print(f"\n[FIN] Fuzzing is over. Total time: {end_time - start_time:.2f} seconds")
