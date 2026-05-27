import time
import pyautogui
from lib.userinteraction import get_element_screen_coords


def drag_and_drop(self, page, tag, browser_x, browser_y,
                  offset_x=0, offset_y=110, browser_name=""):
    abs_x, abs_y, element = get_element_screen_coords(
        page, tag, browser_x, browser_y, offset_x, offset_y, 2, 0.12,
    )
    if element is None:
        print(f"[debug] drag_and_drop: element not found: {tag}")
        return False
    if not (element.is_visible() and element.is_enabled()):
        print(f"[debug] drag_and_drop: {tag} is hidden or disabled")
        return False

    pyautogui.moveTo(abs_x, abs_y)
    pyautogui.mouseDown()
    time.sleep(0.15)

    if browser_name == "opera":
        time.sleep(0.1)
        pyautogui.moveTo(abs_x, browser_y + 10, duration=0.2)
        time.sleep(0.1)

    pyautogui.moveTo(
        browser_x + page.evaluate("window.innerWidth") / 2,
        browser_y + 10,
        duration=0.5,
    )
    pyautogui.mouseUp()
    time.sleep(0.1)

    if browser_name == "firefox":
        pyautogui.click(abs_x + 90, abs_y + 10)

    return True

def drag_and_drop_to_other_window(self, page, tag, browser_x, browser_y,
                                   offset_x=0, offset_y=110, browser_name=""):
    abs_x, abs_y, element = get_element_screen_coords(
        page, tag, browser_x, browser_y, offset_x, offset_y, 2, 0.12,
    )
    if element is None:
        print(f"[debug] drag_and_drop_to_other_window: element not found: {tag}")
        return False
    if not (element.is_visible() and element.is_enabled()):
        print(f"[debug] drag_and_drop_to_other_window: {tag} is hidden or disabled")
        return False

    screen_w, _ = pyautogui.size()

    NEW_W, NEW_H = 800, 600
    try:
        a_info = page.evaluate(
            "({x: window.screenX, y: window.screenY, w: window.outerWidth})"
        )
        a_x = int(a_info.get("x", browser_x))
        a_w = int(a_info.get("w", 900))
    except Exception:
        a_x, a_w = browser_x, 900

    if a_x + a_w + NEW_W + 10 <= screen_w:
        new_x = a_x + a_w + 10
    else:
        new_x = max(0, a_x - NEW_W - 10)
    new_y = browser_y
    drop_x = new_x + NEW_W // 2
    drop_y = new_y + 120

    try:
        with page.context.expect_page(timeout=3000) as new_page_info:
            page.evaluate(
                f"window.open('about:blank', '_blank',"
                f" 'popup,left={new_x},top={new_y},width={NEW_W},height={NEW_H}')"
            )
        new_page = new_page_info.value
        time.sleep(0.5)
    except Exception as e:
        print(f"[debug] drag_and_drop_to_other_window: failed to open new window: {e}")
        return False

    try:
        b_info = new_page.evaluate(
            "({x: window.screenX, y: window.screenY, w: window.outerWidth, h: window.outerHeight})"
        )
        drop_x = int(b_info["x"]) + int(b_info["w"]) // 2
        drop_y = int(b_info["y"]) + min(200, int(b_info["h"]) // 3)
        print(f"[debug] window B actual pos: ({b_info['x']}, {b_info['y']}) {b_info['w']}x{b_info['h']} -> drop=({drop_x},{drop_y})")
    except Exception as e:
        print(f"[debug] could not read window B position: {e}, using pre-calculated ({drop_x},{drop_y})")


    try:
        page.bring_to_front()
        time.sleep(0.5)
    except Exception:
        pass

    pyautogui.moveTo(abs_x, abs_y)
    pyautogui.mouseDown()
    time.sleep(0.4)

    pyautogui.moveTo(abs_x + 4, abs_y + 4)
    time.sleep(0.2)
    pyautogui.moveTo(abs_x, abs_y)
    time.sleep(0.15)

    try:
        new_page.bring_to_front()
        time.sleep(0.4)
    except Exception:
        pass

    if browser_name == "opera":
        pyautogui.moveTo(abs_x, browser_y + 10, duration=0.2)
        time.sleep(0.1)

    pyautogui.moveTo(drop_x, drop_y, duration=1.0)
    time.sleep(0.3)
    pyautogui.mouseUp()
    time.sleep(0.3)

    if browser_name == "firefox":
        pyautogui.click(abs_x + 90, abs_y + 10)

    return True


def register(cve):
    cve.register("drag_and_drop", drag_and_drop)
    cve.register("drag_and_drop_to_other_window", drag_and_drop_to_other_window)
