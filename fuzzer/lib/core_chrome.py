import time
from pathlib import Path
from pywinauto import Application
from playwright.sync_api import sync_playwright
from .core_common import (
    check_browserx_browsery, execution, close_render_process_with_unique_keep,
    close_extra_app_windows, load_scenario, close_browser,
    get_browser_pid_with_window, load_browser_info, force_window_position,
    reposition_if_offscreen, _ensure_clean_loop, _SCENARIO_TIMEOUT,
)

_PROCESS_NAME     = "chrome.exe"
_RESTART_SLEEP    = 4
_RESTART_INTERVAL = 50

_PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles" / "chrome"


def _start_browser(browser_name):
    _ensure_clean_loop()
    info = load_browser_info(browser_name)
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    p       = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(_PROFILE_DIR),
        headless=False,
        executable_path=info["browser_dir_command"],
        args=[
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--window-position=0,0", "--window-size=1280,800",
            "--disable-web-security",
        ],
        ignore_default_args=["--enable-automation", "--disable-component-update"],
    )
    time.sleep(1.5)
    pid = get_browser_pid_with_window(_PROCESS_NAME)
    app = Application(backend="uia").connect(process=pid)
    return app, context, p


def _fresh_session(browser_name):
    app, context, p = _start_browser(browser_name)
    page = close_render_process_with_unique_keep(None, context)
    force_window_position(app)
    browser_x, browser_y = check_browserx_browsery(app)
    return app, None, p, context, page, browser_x, browser_y


def _restart(browser_name, app, p):
    try:
        close_browser(app)
    except Exception as e:
        print(f"[debug] close_browser failed: {e}")
    try:
        if p:
            p.stop()
    except Exception as e:
        print(f"[debug] p.stop failed: {e}")
    _ensure_clean_loop()
    time.sleep(_RESTART_SLEEP)
    return _fresh_session(browser_name)


def run(subdir, files, cve, report_url, offset_x, offset_y, browser_name, security_policy):
    page_cnt   = 0
    start_time = time.time()
    app = browser = p = context = page = None

    try:
        app, browser, p, context, page, browser_x, browser_y = _fresh_session(browser_name)

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
                    app, browser, p, context, page, browser_x, browser_y = _restart(browser_name, app, p)
                    continue
                time.sleep(1)
                page = close_render_process_with_unique_keep(browser, context)
                page.bring_to_front()
                close_extra_app_windows(app)
                page_cnt += 1

                if page_cnt % _RESTART_INTERVAL == 0:
                    print("[+] Periodic browser restart")
                    app, browser, p, context, page, browser_x, browser_y = _restart(browser_name, app, p)

            except Exception as e:
                print(f"[debug] scenario error: {e}")
                try:
                    app, browser, p, context, page, browser_x, browser_y = _restart(browser_name, app, p)
                except Exception as re:
                    print(f"[debug] restart failed: {re}")

    except Exception as e:
        print(f"[debug] : {e}")

    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if p:
            p.stop()

    end_time = time.time()
    print(f"\n[FIN] Fuzzing is over. Total time: {end_time - start_time:.2f} seconds")
