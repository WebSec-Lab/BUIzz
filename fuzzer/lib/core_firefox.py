import time
from pywinauto import Application
from playwright.sync_api import sync_playwright
from .core_common import (
    check_browserx_browsery, execution, load_scenario,
    close_browser, get_browser_pid_with_window,
    close_render_process_with_unique_keep, force_window_position,
    reposition_if_offscreen, _ensure_clean_loop, _SCENARIO_TIMEOUT,
)

_RESTART_SLEEP = 4
_BROWSER_RESTART_INTERVAL = 40


def _start_browser():
    _ensure_clean_loop()
    print("[+] Starting Firefox with Playwright")
    p       = sync_playwright().start()
    browser = p.firefox.launch(
        headless=False,
        channel="firefox",
        firefox_user_prefs={
            "network.stricttransportsecurity.preloadlist": False,
        },
    )
    return browser, p


def _fresh_session():
    browser, p = _start_browser()
    context    = browser.new_context()
    page = close_render_process_with_unique_keep(browser, context)
    time.sleep(1.5)
    pid = get_browser_pid_with_window("firefox.exe")
    app = Application(backend="win32").connect(process=pid)
    try:
        force_window_position(app)
        browser_x, browser_y = check_browserx_browsery(app)
    except Exception as e:
        browser.close()
        p.stop()
        raise RuntimeError(f"Firefox window not reachable: {e}")
    return app, browser, p, context, page, pid, browser_x, browser_y


def _restart(app, browser, p):
    try:
        close_browser(app)
    except Exception as e:
        print(f"[debug] close_browser failed: {e}")
    if browser:
        try:
            browser.close()
        except Exception:
            pass
    try:
        if p:
            p.stop()
    except Exception as e:
        print(f"[debug] p.stop failed: {e}")
    _ensure_clean_loop()
    time.sleep(_RESTART_SLEEP)
    return _fresh_session()


def CFF(subdir, files, cve, report_url, offset_x, offset_y, browser_name, security_policy):
    page_cnt = 0
    start_time = time.time()
    app = browser = p = context = page = None

    try:
        app, browser, p, context, page, pid, browser_x, browser_y = _fresh_session()

        for f in files:
            print(f"\n[--------] TEST scenario : {subdir}/{f} [--------]")
            reposition_if_offscreen(app)
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
                    app, browser, p, context, page, pid, browser_x, browser_y = _restart(app, browser, p)
                    continue
                page = close_render_process_with_unique_keep(browser, context)
                page_cnt += 1

                if page_cnt % _BROWSER_RESTART_INTERVAL == 0:
                    print("[+] Periodic browser restart")
                    app, browser, p, context, page, pid, browser_x, browser_y = _restart(app, browser, p)
                else:
                    page.bring_to_front()
                    browser_x, browser_y = check_browserx_browsery(app)

            except Exception as e:
                print(f"[debug] scenario error: {e}")
                try:
                    app, browser, p, context, page, pid, browser_x, browser_y = _restart(app, browser, p)
                except Exception as re:
                    print(f"[debug] restart failed: {re}")

    except Exception as e:
        print(f"[debug] : {e}")

    finally:
        if app:
            close_browser(app)
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if p:
            p.stop()

    end_time = time.time()
    print(f"\n[FIN] Fuzzing is over. Total time: {end_time - start_time:.2f} seconds")


run = CFF
