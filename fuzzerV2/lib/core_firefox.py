import time
from pywinauto import Application
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from .core_common import (
    check_browserx_browsery, execution, reset_to_single_tab,
    load_scenario, close_browser, get_browser_pid_with_window,
    get_browser_exe, force_window_position, reposition_if_offscreen,
    _SCENARIO_TIMEOUT,
)

_PROCESS_NAME     = "firefox.exe"
_RESTART_SLEEP    = 4
_RESTART_INTERVAL = 40


def _start_browser(browser_name):
    options = Options()
    options.binary_location = get_browser_exe(browser_name)
    options.accept_insecure_certs = True
    options.set_preference("network.stricttransportsecurity.preloadlist", False)
    driver = webdriver.Firefox(options=options)
    time.sleep(1.5)
    pid = get_browser_pid_with_window(_PROCESS_NAME)
    app = Application(backend="win32").connect(process=pid)
    return app, driver


def _fresh_session(browser_name):
    app, driver = _start_browser(browser_name)
    reset_to_single_tab(driver)
    time.sleep(1.5)
    try:
        force_window_position(app)
        browser_x, browser_y = check_browserx_browsery(app)
    except Exception as e:
        driver.quit()
        raise RuntimeError(f"Firefox window not reachable: {e}")
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
