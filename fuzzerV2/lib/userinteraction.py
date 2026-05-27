import time
import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def _read_browser_xy(app):
    try:
        rect = app.top_window().rectangle()
        return rect.left, rect.top
    except Exception:
        return None


def get_element_screen_coords(driver, selector, browser_x=0, browser_y=0,
                              offset_x=0, offset_y=80, timeout=2.0, debug=False,
                              app=None, max_depth=5):

    def _find_with_offset(path, acc_x, acc_y):
        driver.switch_to.default_content()
        try:
            for idx in path:
                driver.switch_to.frame(idx)
        except Exception:
            return None

        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            if el:
                return el, acc_x, acc_y
        except Exception:
            pass

        if len(path) >= max_depth:
            return None

        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
        except Exception:
            return None

        child_offsets = []
        for iframe in iframes:
            try:
                ir = driver.execute_script(
                    "var r=arguments[0].getBoundingClientRect();"
                    "return {left:r.left,top:r.top};",
                    iframe,
                )
                child_offsets.append((acc_x + float(ir.get("left", 0)),
                                      acc_y + float(ir.get("top",  0))))
            except Exception:
                child_offsets.append((acc_x, acc_y))

        for i, (cx, cy) in enumerate(child_offsets):
            result = _find_with_offset(path + [i], cx, cy)
            if result is not None:
                return result
        return None

    el = None
    iframe_offset_x = iframe_offset_y = 0.0
    deadline = time.time() + timeout

    while time.time() < deadline:
        result = _find_with_offset([], 0.0, 0.0)
        if result is not None:
            el, iframe_offset_x, iframe_offset_y = result
            break
        time.sleep(0.12)

    if el is None:
        return None, None, None

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    except Exception:
        pass

    try:
        rect = driver.execute_script(
            "var r=arguments[0].getBoundingClientRect();"
            "return {left:r.left,top:r.top,width:r.width,height:r.height};",
            el,
        )
        if not rect:
            return None, None, None
    except Exception as e:
        if debug:
            print(f"[debug] getBoundingClientRect failed: {e}")
        return None, None, None

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    center_x = rect["left"] + rect["width"]  / 2.0 + iframe_offset_x
    center_y = rect["top"]  + rect["height"] / 2.0 + iframe_offset_y

    try:
        dpr = float(driver.execute_script("return window.devicePixelRatio") or 1.0)
    except Exception:
        dpr = 1.0

    if app is not None:
        pos = _read_browser_xy(app)
        if pos is not None:
            browser_x, browser_y = pos

    abs_x = int(browser_x + center_x * dpr + offset_x)
    abs_y = int(browser_y + center_y * dpr + offset_y)

    if debug:
        print(f"[debug] iframe_offset=({iframe_offset_x}, {iframe_offset_y})")
        print(f"[debug] center_css=({center_x}, {center_y}), dpr={dpr}")
        print(f"[debug] browser_xy=({browser_x}, {browser_y})")
        print(f"[debug] screen coords -> ({abs_x}, {abs_y})")

    return abs_x, abs_y, el


def find_in_frames(driver, selector, timeout=2.0, poll_interval=0.12, max_depth=5, debug=False):

    def _search(path):
        driver.switch_to.default_content()
        try:
            for idx in path:
                driver.switch_to.frame(idx)
        except Exception as e:
            if debug:
                print(f"[find_in_frames] switch_to.frame failed path={path}: {e}")
            return None

        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            if el:
                if debug:
                    print(f"[find_in_frames] found {selector} at path={path}")
                return el
        except Exception:
            pass

        if len(path) >= max_depth:
            return None

        try:
            count = len(driver.find_elements(By.TAG_NAME, "iframe"))
        except Exception as e:
            if debug:
                print(f"[find_in_frames] find iframes failed path={path}: {e}")
            return None

        if debug:
            print(f"[find_in_frames] path={path} has {count} child iframe(s)")

        for i in range(count):
            result = _search(path + [i])
            if result is not None:
                return result
        return None

    deadline = time.time() + timeout
    while True:
        el = _search([])
        if el is not None:
            return el
        if time.time() >= deadline:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return None
        time.sleep(poll_interval)


_SPECIAL_SCHEMES = ("javascript:", "data:", "blob:")


def _is_special_scheme(el):
    try:
        href = (el.get_attribute("href") or "").strip().lower()
        return any(href.startswith(s) for s in _SPECIAL_SCHEMES)
    except Exception:
        return False


def mouse_click(driver, tag, interaction="left", modifiers=None, debug=False):
    el = find_in_frames(driver, tag, timeout=3.0, debug=debug)
    if el is None:
        return False

    try:
        if not (el.is_displayed() and el.is_enabled()):
            print(f"[debug] {tag} is hidden or disabled")
            return False
    except Exception as e:
        print(f"[debug] visibility check failed: {e}")
        return False

    ac = ActionChains(driver)
    mod_keys = []
    if modifiers:
        mod_list = modifiers if isinstance(modifiers, list) else [modifiers]
        for mod in mod_list:
            key = getattr(Keys, str(mod).upper(), None)
            if key:
                ac.key_down(key)
                mod_keys.append(key)

    if interaction == "right":
        ac.context_click(el)
    else:
        ac.click(el)

    for key in mod_keys:
        ac.key_up(key)

    try:
        ac.perform()
        return True
    except Exception as e:
        print(f"[debug] click attempt 1 (ActionChains) failed: {e}")

    try:
        el.click()
        return True
    except Exception as e:
        print(f"[debug] click attempt 2 (direct) failed: {e}")

    try:
        driver.execute_script("arguments[0].click()", el)
        return True
    except Exception as e:
        print(f"[debug] click attempt 3 (js) failed: {e}")
        return False
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def mouse_userinter(driver, tag, interaction, app, browser_x=0, browser_y=0,
                    offset_x=0, offset_y=110, submenu=False):
    abs_x, abs_y, element = get_element_screen_coords(
        driver, tag, browser_x, browser_y, offset_x, offset_y, 2.0, debug=True, app=app,
    )
    print(f"[debug] mouse_userinter: browser=({browser_x},{browser_y}) -> screen=({abs_x},{abs_y})")
    if element is None:
        print(f"[debug] element not found: {tag}")
        return False
    try:
        if not (element.is_displayed() and element.is_enabled()):
            print(f"[debug] {tag} is hidden or disabled")
            return False
    except Exception:
        pass

    pyautogui.moveTo(abs_x, abs_y)
    time.sleep(0.2)
    pyautogui.click(button="right")
    time.sleep(0.2)
    pyautogui.press("down", presses=interaction, interval=0.02)
    if submenu:
        pyautogui.press("right")
        time.sleep(0.1)
    pyautogui.press("enter")
    return True


def keyboard_userinter(driver, keyboard_title, keyboard, corpus_url):
    if "Reopen" in keyboard_title:
        original_handle = driver.current_window_handle
        driver.switch_to.new_window("tab")
        new_handle = driver.current_window_handle
        driver.get("data:text/html,hi")
        driver.switch_to.window(original_handle)
        time.sleep(0.3)
        driver.close()
        driver.switch_to.window(new_handle)
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    elif "backward" in keyboard_title:
        driver.get("data:text/html,hi")
        try:
            driver.execute_script("window.focus()")
        except Exception:
            pass
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    elif "forward" in keyboard_title:
        driver.get("data:text/html,hi")
        driver.get(corpus_url)
        time.sleep(0.3)
        driver.back()
        try:
            driver.execute_script("window.focus()")
        except Exception:
            pass
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    else:
        try:
            driver.execute_script("window.focus()")
        except Exception:
            pass
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    time.sleep(0.1)
    return True


def keyboard_with_click(driver, keyboard_title, keyboard, tag):
    try:
        print(keyboard)
        mouse_click(driver, tag, "left", keyboard)
    except Exception as e:
        print(f"[debug] keyboard_with_click error: {e}")
