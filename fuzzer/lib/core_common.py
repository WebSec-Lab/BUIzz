import uuid
import time
import json
import asyncio
import psutil
from pathlib import Path
from pywinauto import Application
from .userinteraction import mouse_userinter, mouse_click, keyboard_userinter, keyboard_with_click


def _ensure_clean_loop():
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()
    except RuntimeError:
        pass
    asyncio.set_event_loop(asyncio.new_event_loop())

_PROJECT_ROOT     = Path(__file__).resolve().parent.parent
_SCENARIO_TIMEOUT = 10


def load_scenario(relative_path):
    json_path = (_PROJECT_ROOT / relative_path).resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"Scenario not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_browser_info(browser_name):
    json_path = (_PROJECT_ROOT / "browser_info" / "browser_info.json").resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"Browser info not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        if entry["browser_name"] == browser_name:
            return entry
    raise ValueError(f"Browser '{browser_name}' not found in browser_info.json")


def insert_cookie(context, report_url):
    context.clear_cookies()
    context.add_cookies([
        {"name": "strict", "value": "strict", "url": report_url, "sameSite": "Strict"},
        {"name": "lax",    "value": "lax",    "url": report_url, "sameSite": "Lax"},
        {"name": "secure", "value": "secure", "url": report_url, "sameSite": "None", "secure": True},
    ])


def insert_cookie_for_tracking(context, report_url, scenario_id, browser_name, corpus, bf="0"):
    sid = str(scenario_id)
    bf  = str(bf)
    context.add_cookies([
        {"name": "number_of_scenario",  "value": sid,          "url": report_url, "sameSite": "Lax"},
        {"name": "number_of_scenario1", "value": sid,          "url": report_url, "sameSite": "None", "secure": True},
        {"name": "browser_name",        "value": browser_name, "url": report_url, "sameSite": "Lax"},
        {"name": "browser_name1",       "value": browser_name, "url": report_url, "sameSite": "None", "secure": True},
        {"name": "bf",                  "value": bf,           "url": report_url, "sameSite": "Lax"},
        {"name": "bf1",                 "value": bf,           "url": report_url, "sameSite": "None", "secure": True},
        {"name": "corpus",              "value": corpus,       "url": report_url, "sameSite": "Lax"},
        {"name": "corpus1",             "value": corpus,       "url": report_url, "sameSite": "None", "secure": True},
    ])


def _set_interaction_cookie(context, report_url, title):
    value = title if title is not None else ""
    try:
        context.add_cookies([
            {"name": "interaction",  "value": value, "url": report_url, "sameSite": "Lax"},
            {"name": "interaction1", "value": value, "url": report_url, "sameSite": "None", "secure": True},
        ])
    except Exception as e:
        print(f"[debug] set_interaction_cookie failed: {e}")


def _move_window(win, x, y, width=None, height=None):
    import win32gui, win32con
    hwnd = int(win.handle)
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] == win32con.SW_SHOWMAXIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass
    flags = win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
    if width is None or height is None:
        flags |= win32con.SWP_NOSIZE
        width = height = 0
    win32gui.SetWindowPos(hwnd, 0, x, y, width, height, flags)


def force_window_position(app, x=0, y=0, width=1280, height=800):
    try:
        win = app.top_window()
        win.wait("visible", timeout=10)
        _move_window(win, x, y, width, height)
        time.sleep(0.2)
    except Exception as e:
        print(f"[debug] force_window_position failed: {e}")


def force_window_maximize(app):
    try:
        win = app.top_window()
        win.wait("visible", timeout=10)
        import win32gui, win32con
        win32gui.ShowWindow(int(win.handle), win32con.SW_MAXIMIZE)
        time.sleep(0.2)
    except Exception as e:
        print(f"[debug] force_window_maximize failed: {e}")


def _virtual_screen_bounds():
    import win32api
    vl = win32api.GetSystemMetrics(76)
    vt = win32api.GetSystemMetrics(77)
    vw = win32api.GetSystemMetrics(78)
    vh = win32api.GetSystemMetrics(79)
    return vl, vt, vl + vw, vt + vh


def _is_offscreen(rect, hwnd=None):
    try:
        if hwnd is not None:
            import win32gui, win32con
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMAXIMIZED:
                return False
        vl, vt, vr, vb = _virtual_screen_bounds()
        return (rect.left   < vl or
                rect.top    < vt or
                rect.right  > vr or
                rect.bottom > vb)
    except Exception:
        return False


def reposition_if_offscreen(app, maximize_on_pullback=False):
    try:
        win = app.top_window()
        win.wait("visible", timeout=5)
        rect = win.rectangle()
        hwnd = int(win.handle)
        if _is_offscreen(rect, hwnd=hwnd):
            if maximize_on_pullback:
                print(f"[+] off-screen detected at ({rect.left},{rect.top}); re-maximizing")
                import win32gui, win32con
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            else:
                print(f"[+] off-screen detected at ({rect.left},{rect.top}); pulling back")
                _move_window(win, 0, 0, 1280, 800)
            time.sleep(0.2)
    except Exception as e:
        print(f"[debug] reposition_if_offscreen failed: {e}")


def check_browserx_browsery(app):
    win = app.top_window()
    win.wait("visible", timeout=10)
    rect = win.rectangle()
    return rect.left, rect.top


def close_browser(app):
    try:
        print("[+] Closing browser safely...")
        app.kill()
        print("[+] Browser closed successfully.")
    except Exception as e:
        print(f"[-] Error while closing browser: {e}")


def get_browser_pid_with_window(process_name):
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] and process_name in proc.info["name"].lower():
            try:
                app = Application(backend="uia").connect(process=proc.info["pid"])
                if app.windows():
                    return proc.info["pid"]
            except Exception:
                continue
    raise RuntimeError(f"No visible browser window found for: {process_name}")


def _wait_for_keep_target(browser_client, before_ids, token, max_wait_secs=3.0, poll_interval=0.1):
    deadline = time.time() + max_wait_secs
    while time.time() < deadline:
        targets = browser_client.send("Target.getTargets")["targetInfos"]
        for t in targets:
            if t["targetId"] in before_ids:
                continue
            title = t.get("title") or ""
            url   = t.get("url")   or ""
            if f"KEEP-{token}" in title or token in url:
                return t["targetId"]
        time.sleep(poll_interval)
    return None


def close_extra_app_windows(app):
    try:
        top_handle = app.top_window().handle
        for win in app.windows():
            if win.handle != top_handle:
                try:
                    win.close()
                    time.sleep(0.2)
                except Exception:
                    pass
    except Exception:
        pass


def close_render_process_with_unique_keep(browser, context, timeout_ms=5000, max_wait_secs=3.0):
    token    = uuid.uuid4().hex
    keep_url = f"data:text/html,<title>KEEP-{token}</title><body>KEEP-{token}</body>"

    if browser is None:
        keep_page = context.new_page()
        try:
            keep_page.goto(keep_url, timeout=timeout_ms)
        except Exception:
            raise RuntimeError("Browser failed to open keep tab")
        for page in list(context.pages):
            if page is not keep_page:
                try:
                    page.close()
                except Exception:
                    pass
        return keep_page

    try:
        browser_client = browser.new_browser_cdp_session()
    except Exception:
        browser_client = None

    if browser_client is None:
        keep_page = context.new_page()
        try:
            keep_page.goto(keep_url, timeout=timeout_ms)
        except Exception:
            raise RuntimeError("Browser failed to open keep tab")
        for ctx in list(browser.contexts):
            for page in list(ctx.pages):
                if page is not keep_page:
                    try:
                        page.close()
                    except Exception:
                        pass
            if ctx is not context:
                try:
                    ctx.close()
                except Exception:
                    pass
        return keep_page

    before_ids = {t["targetId"] for t in browser_client.send("Target.getTargets")["targetInfos"]}

    keep_page = context.new_page()
    try:
        keep_page.goto(keep_url, timeout=timeout_ms)
    except Exception:
        raise RuntimeError("Browser failed to open keep tab")

    keep_id = _wait_for_keep_target(browser_client, before_ids, token, max_wait_secs)
    if not keep_id:
        raise RuntimeError("Keep tab not reflected in CDP targets within timeout")

    try:
        targets = browser_client.send("Target.getTargets")["targetInfos"]
        for t in targets:
            tid   = t.get("targetId")
            ttype = t.get("type", "")
            turl  = t.get("url") or ""
            if tid == keep_id or ttype == "browser" or turl.startswith("chrome-extension://"):
                continue
            try:
                browser_client.send("Target.closeTarget", {"targetId": tid})
            except Exception:
                pass
    except Exception as e:
        raise RuntimeError(f"Failed to close render processes: {e}")

    return keep_page


def _dispatch_action(page, context, action, cve, app,
                     browser_x, browser_y, offset_x, offset_y,
                     browser_name, corpus_url):
    action_type = action.get("type")
    tag         = action.get("tag")
    interaction = action.get("interaction", {})
    num         = interaction.get("num")
    title       = interaction.get("title")

    if action_type == "click":
        mouse_click(page, tag, num)

    elif action_type == "mouse":
        page.bring_to_front()
        time.sleep(0.2)
        bx, by = check_browserx_browsery(app)
        submenu = browser_name == "opera" and "workspace" in (title or "").lower()
        mouse_userinter(page, tag, int(num), bx, by, offset_x, offset_y, submenu=submenu)

    elif action_type == "keyboard":
        keyboard_userinter(page, context, title, num, corpus_url)

    elif action_type == "cve":
        if title == "drag_and_drop":
            page.bring_to_front()
            time.sleep(0.2)
            bx, by = check_browserx_browsery(app)
            cve.drag_and_drop(page, "#a1", bx, by, offset_x, offset_y, browser_name)

        elif title == "drag_and_drop_to_other_window":
            page.bring_to_front()
            time.sleep(0.2)
            bx, by = check_browserx_browsery(app)
            cve.drag_and_drop_to_other_window(page, "#a1", bx, by, offset_x, offset_y, browser_name)

    elif action_type == "keyboard_with_click":
        keyboard_with_click(page, context, title, num, tag)

    else:
        print(f"[debug] Unknown action type: '{action_type}'")


def execution(browser, context, page, scenario, cve, report_url,
              offset_x, offset_y, browser_x, browser_y,
              browser_name, scenario_id, app, security_policy):
    corpus_url  = scenario.get("corpus")
    useractions = scenario.get("useraction", [])

    try:
        if security_policy == "samesite":
            insert_cookie(context, report_url)
        insert_cookie_for_tracking(context, report_url, scenario_id, browser_name, corpus_url, 1)
        print(f"[+] Initial page : {corpus_url}")
        print("[+] Cookie header monitor attached.")
    except Exception:
        raise RuntimeError("Failed to insert tracking cookies")

    try:
        if security_policy == "hsts":
            page.goto("https://adition.com", timeout=5000)
        page.goto(corpus_url, timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=2000)
    except Exception as e:
        raise RuntimeError(f"Failed to navigate to corpus: {e}")

    try:
        with context.expect_page(timeout=3000):
            time.sleep(1)
            prev_title = None
            for i, action in enumerate(useractions):
                print(f"[+] useraction: CASE_{i}")
                if page is None or page.is_closed():
                    continue
                title = action.get("interaction", {}).get("title")
                _set_interaction_cookie(context, report_url, title)
                if prev_title != "Left click":
                    page.bring_to_front()
                time.sleep(0.2)
                _dispatch_action(
                    page, context, action, cve, app,
                    browser_x, browser_y, offset_x, offset_y,
                    browser_name, corpus_url,
                )
                prev_title = title
        time.sleep(0.5)
    except Exception as e:
        print(f"[debug] useraction: {e}")
