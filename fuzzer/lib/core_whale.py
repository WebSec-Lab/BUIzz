import time
from pywinauto import Application
from playwright.sync_api import sync_playwright
from .core_common import (
    check_browserx_browsery, execution, close_render_process_with_unique_keep,
    load_scenario, close_browser, load_browser_info, force_window_maximize,
    get_browser_pid_with_window, reposition_if_offscreen, _SCENARIO_TIMEOUT,
)

_CDP_URL          = "http://localhost:9222"
_RESTART_SLEEP    = 4
_RESTART_INTERVAL = 50


def _launch_browser(browser_name):
    info = load_browser_info(browser_name)
    app  = Application(backend="uia").start(info["browser_dir_command"])
    try:
        app.connect(title_re=info["browser_regex"], timeout=15)
    except Exception as e:
        print(f"[debug] title-based connect failed ({e}); falling back to process-based")
        time.sleep(2)
        pid = get_browser_pid_with_window("whale.exe")
        if pid is None:
            raise RuntimeError("whale.exe with a window not found after launch")
        app = Application(backend="uia").connect(process=pid)
    force_window_maximize(app)
    browser_x, browser_y = check_browserx_browsery(app)
    return app, browser_x, browser_y


def _connect(p):
    browser = p.chromium.connect_over_cdp(_CDP_URL)
    context = browser.contexts[0]
    return browser, context


def _fresh_session(p, browser_name):
    app, browser_x, browser_y = _launch_browser(browser_name)
    time.sleep(1)
    browser, context = _connect(p)
    page = close_render_process_with_unique_keep(browser, context)
    browser_x, browser_y = check_browserx_browsery(app)
    return app, browser, context, page, browser_x, browser_y


def _restart(p, browser_name, app):
    close_browser(app)
    time.sleep(_RESTART_SLEEP)
    return _fresh_session(p, browser_name)


def run(subdir, files, cve, report_url, offset_x, offset_y, browser_name, security_policy):
    start_time = time.time()
    page_cnt   = 0

    with sync_playwright() as p:
        app, browser, context, page, browser_x, browser_y = _fresh_session(p, browser_name)
        try:
            for f in files:
                print(f"\n[--------] TEST scenario : {subdir}/{f} [--------]")
                reposition_if_offscreen(app, maximize_on_pullback=True)
                try:
                    scenario = load_scenario(f"{subdir}/{f}")
                    scenario_start = time.time()
                    execution(
                        browser, context, page, scenario, cve, report_url,
                        offset_x, offset_y, browser_x, browser_y,
                        browser_name, f, app, security_policy,
                    )
                    if time.time() - scenario_start > _SCENARIO_TIMEOUT:
                        print(f"[!] Scenario took >{_SCENARIO_TIMEOUT}s — restarting browser")
                        app, browser, context, page, browser_x, browser_y = _restart(p, browser_name, app)
                        continue
                    time.sleep(0.8)
                    page.bring_to_front()
                    time.sleep(0.2)
                    page = close_render_process_with_unique_keep(browser, context)
                    page_cnt += 1

                    if page_cnt % _RESTART_INTERVAL == 0:
                        print("[+] Periodic browser restart")
                        app, browser, context, page, browser_x, browser_y = _restart(p, browser_name, app)

                except Exception as e:
                    print(f"[debug] scenario error: {e}")
                    try:
                        app, browser, context, page, browser_x, browser_y = _restart(p, browser_name, app)
                    except Exception as re:
                        print(f"[debug] restart failed: {re}")

        except Exception as e:
            print(f"[debug] : {e}")
        finally:
            close_browser(app)

    end_time = time.time()
    print(f"\n[FIN] Fuzzing is over. Total time: {end_time - start_time:.2f} seconds")
