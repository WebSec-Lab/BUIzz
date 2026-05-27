import re
import time
import json
import psutil
import subprocess
from pathlib import Path
from pywinauto import Application
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from .userinteraction import mouse_userinter, mouse_click, keyboard_userinter, keyboard_with_click

_PROJECT_ROOT     = Path(__file__).resolve().parent.parent.parent / "fuzzer"
_SCENARIO_TIMEOUT = 10


def make_chromium_service(exe_path):
    try:
        out = subprocess.check_output(
            [exe_path, "--version"],
            stderr=subprocess.STDOUT,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode(errors="ignore")
        m = re.search(r"(\d{2,3})\.\d+\.\d+", out)
        if not m:
            return None
        major = m.group(1)
    except Exception as e:
        print(f"[debug] make_chromium_service: version detection failed: {e}")
        return None

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager(driver_version=major).install()
        print(f"[+] ChromeDriver {major} -> {driver_path}")
        return Service(driver_path)
    except Exception as e:
        print(f"[debug] make_chromium_service: driver download failed: {e}")
        return None


def load_scenario(relative_path):
    json_path = (_PROJECT_ROOT / relative_path).resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"Scenario not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_browser_info(browser_name):
    json_path = (Path(__file__).resolve().parent.parent / "browser_info" / "browser_info.json").resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"Browser info not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as f:
        entries = json.load(f)
    for entry in entries:
        if entry["browser_name"] == browser_name:
            return entry
    raise ValueError(f"Browser '{browser_name}' not found in browser_info.json")


def get_browser_exe(browser_name):
    info = load_browser_info(browser_name)
    cmd = info["browser_dir_command"]
    idx = cmd.lower().find(".exe")
    if idx != -1:
        return cmd[:idx + 4]
    return cmd.split()[0]


def insert_cookie(driver):
    driver.delete_all_cookies()
    driver.add_cookie({"name": "strict", "value": "strict", "sameSite": "Strict"})
    driver.add_cookie({"name": "lax",    "value": "lax",    "sameSite": "Lax"})
    driver.add_cookie({"name": "secure", "value": "secure", "sameSite": "None", "secure": True})


def insert_cookie_for_tracking(driver, scenario_id, browser_name, corpus, bf="0"):
    sid = str(scenario_id)
    bf  = str(bf)
    cookies = [
        {"name": "number_of_scenario",  "value": sid,          "sameSite": "Lax"},
        {"name": "number_of_scenario1", "value": sid,          "sameSite": "None", "secure": True},
        {"name": "browser_name",        "value": browser_name, "sameSite": "Lax"},
        {"name": "browser_name1",       "value": browser_name, "sameSite": "None", "secure": True},
        {"name": "bf",                  "value": bf,           "sameSite": "Lax"},
        {"name": "bf1",                 "value": bf,           "sameSite": "None", "secure": True},
        {"name": "corpus",              "value": corpus or "",  "sameSite": "Lax"},
        {"name": "corpus1",             "value": corpus or "",  "sameSite": "None", "secure": True},
    ]
    for c in cookies:
        try:
            driver.add_cookie(c)
        except Exception as e:
            print(f"[debug] add_cookie failed ({c['name']}): {e}")




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
        time.sleep(0.3)
    except Exception as e:
        print(f"[debug] force_window_position failed: {e}")


def force_window_maximize(app):
    try:
        win = app.top_window()
        win.wait("visible", timeout=10)
        import win32gui, win32con
        win32gui.ShowWindow(int(win.handle), win32con.SW_MAXIMIZE)
        time.sleep(0.3)
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
            time.sleep(0.3)
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


def reset_to_single_tab(driver):
    driver.switch_to.new_window("tab")
    new_handle = driver.current_window_handle
    for handle in list(driver.window_handles):
        if handle != new_handle:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception:
                pass
    driver.switch_to.window(new_handle)
    return new_handle


def _dispatch_action(driver, action, cve, app,
                     offset_x, offset_y,
                     browser_name, corpus_url):
    action_type = action.get("type")
    tag         = action.get("tag")
    interaction = action.get("interaction", {})
    num         = interaction.get("num")
    title       = interaction.get("title")

    if action_type == "click":
        mouse_click(driver, tag, num)

    elif action_type == "mouse":
        try:
            driver.execute_script("window.focus()")
        except Exception:
            pass
        time.sleep(0.3)
        bx, by = check_browserx_browsery(app)
        submenu = browser_name == "opera" and "workspace" in (title or "").lower()
        mouse_userinter(driver, tag, int(num), app, bx, by, offset_x, offset_y, submenu=submenu)

    elif action_type == "keyboard":
        keyboard_userinter(driver, title, num, corpus_url)

    elif action_type == "cve":
        if title == "drag_and_drop":
            try:
                driver.execute_script("window.focus()")
            except Exception:
                pass
            time.sleep(0.3)
            bx, by = check_browserx_browsery(app)
            cve.drag_and_drop(driver, "#a1", bx, by, offset_x, offset_y, browser_name, app)

        elif title == "drag_and_drop_to_other_window":
            try:
                driver.execute_script("window.focus()")
            except Exception:
                pass
            time.sleep(0.3)
            bx, by = check_browserx_browsery(app)
            cve.drag_and_drop_to_other_window(driver, "#a1", bx, by, offset_x, offset_y, browser_name, app)

    elif action_type == "keyboard_with_click":
        keyboard_with_click(driver, title, num, tag)

    else:
        print(f"[debug] Unknown action type: '{action_type}'")


def execution(driver, scenario, cve, report_url,
              offset_x, offset_y,
              browser_name, scenario_id, app, security_policy):
    corpus_url  = scenario.get("corpus")
    useractions = scenario.get("useraction", [])

    try:
        driver.get(report_url)
        if security_policy == "samesite":
            insert_cookie(driver)
        insert_cookie_for_tracking(driver, scenario_id, browser_name, corpus_url, 1)
        print(f"[+] Initial page : {corpus_url}")
        print("[+] Cookie header monitor attached.")
    except Exception as e:
        raise RuntimeError(f"Failed to insert tracking cookies: {e}")

    try:
        if security_policy == "hsts":
            driver.get("https://adition.com")
        driver.get(corpus_url)
        try:
            WebDriverWait(driver, 2).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
    except Exception as e:
        raise RuntimeError(f"Failed to navigate to corpus: {e}")

    try:
        time.sleep(1)
        for i, action in enumerate(useractions):
            print(f"[+] useraction: CASE_{i}")
            _dispatch_action(
                driver, action, cve, app,
                offset_x, offset_y,
                browser_name, corpus_url,
            )
        time.sleep(0.5)
    except Exception as e:
        print(f"[debug] useraction: {e}")
