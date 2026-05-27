import time
import pyautogui
from lib.userinteraction import get_element_screen_coords, _read_browser_xy


def drag_and_drop(self, driver, tag, browser_x, browser_y,
                  offset_x=0, offset_y=110, browser_name="", app=None):
    abs_x, abs_y, element = get_element_screen_coords(
        driver, tag, browser_x, browser_y, offset_x, offset_y, 2.0, app=app,
    )
    if element is None:
        print(f"[debug] drag_and_drop: element not found: {tag}")
        return False
    try:
        if not (element.is_displayed() and element.is_enabled()):
            print(f"[debug] drag_and_drop: {tag} is hidden or disabled")
            return False
    except Exception:
        # element is in a nested iframe; driver was reset to default_content by
        # get_element_screen_coords, so is_displayed() may raise StaleElementReferenceException.
        # Coordinates are already computed correctly — proceed with the interaction.
        pass

    pyautogui.moveTo(abs_x, abs_y)
    pyautogui.mouseDown()
    time.sleep(0.15)

    # Re-read browser position right before computing drag destination
    if app is not None:
        pos = _read_browser_xy(app)
        if pos is not None:
            browser_x, browser_y = pos

    if browser_name == "opera":
        time.sleep(0.1)
        pyautogui.moveTo(abs_x, browser_y + 10, duration=0.2)
        time.sleep(0.1)

    inner_width = driver.execute_script("return window.innerWidth")
    pyautogui.moveTo(
        browser_x + inner_width / 2,
        browser_y + 10,
        duration=0.5,
    )
    pyautogui.mouseUp()
    time.sleep(0.1)

    if browser_name == "firefox":
        pyautogui.click(abs_x + 90, abs_y + 10)

    return True


def drag_and_drop_to_other_window(self, driver, tag, browser_x, browser_y,  # noqa: ARG001
                                   offset_x=0, offset_y=110, browser_name="", app=None):
    abs_x, abs_y, element = get_element_screen_coords(
        driver, tag, browser_x, browser_y, offset_x, offset_y, 2.0, app=app,
    )
    if element is None:
        print(f"[debug] drag_and_drop_to_other_window: element not found: {tag}")
        return False
    try:
        if not (element.is_displayed() and element.is_enabled()):
            print(f"[debug] drag_and_drop_to_other_window: {tag} is hidden or disabled")
            return False
    except Exception:
        pass

    screen_w, _ = pyautogui.size()

    NEW_W, NEW_H = 800, 600
    try:
        a_x = int(driver.execute_script("return window.screenX"))
        a_w = int(driver.execute_script("return window.outerWidth"))
    except Exception:
        a_x, a_w = browser_x, 900

    if a_x + a_w + NEW_W + 10 <= screen_w:
        new_x = a_x + a_w + 10
    else:
        new_x = max(0, a_x - NEW_W - 10)
    new_y = browser_y
    drop_x = new_x + NEW_W // 2
    drop_y = new_y + 120

    # Open B first, then bring A back
    orig_handle    = driver.current_window_handle
    before_handles = set(driver.window_handles)
    try:
        driver.execute_script(
            f"window.open('about:blank', '_blank',"
            f" 'popup,left={new_x},top={new_y},width={NEW_W},height={NEW_H}')"
        )
        time.sleep(0.5)
        new_handles = set(driver.window_handles) - before_handles
        if not new_handles:
            print("[debug] drag_and_drop_to_other_window: no new window opened")
            return False
        new_handle = next(iter(new_handles))
    except Exception as e:
        print(f"[debug] drag_and_drop_to_other_window: failed to open new window: {e}")
        return False

    try:
        driver.switch_to.window(orig_handle)
        driver.execute_script("window.focus()")
        time.sleep(0.5)
    except Exception:
        pass

    # Start drag on A
    pyautogui.moveTo(abs_x, abs_y)
    pyautogui.mouseDown()
    time.sleep(0.4)

    # Tiny nudge to fire dragstart while still over the element
    pyautogui.moveTo(abs_x + 4, abs_y + 4)
    time.sleep(0.2)
    pyautogui.moveTo(abs_x, abs_y)
    time.sleep(0.15)

    # Bring B to front while drag is in progress
    try:
        driver.switch_to.window(new_handle)
        driver.execute_script("window.focus()")
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

    try:
        driver.switch_to.window(orig_handle)
    except Exception:
        pass

    return True


def register(cve):
    cve.register("drag_and_drop", drag_and_drop)
    cve.register("drag_and_drop_to_other_window", drag_and_drop_to_other_window)
