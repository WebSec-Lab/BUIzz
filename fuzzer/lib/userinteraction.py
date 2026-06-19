import time
import pyautogui
from playwright.sync_api import Page


def get_element_screen_coords(page, selector, browser_x=0, browser_y=0,
                              offset_x=0, offset_y=80, timeout=2.0, poll_interval=0.12,
                              debug=False):
    deadline = time.time() + timeout if timeout and timeout > 0 else None

    found_frame = None
    element     = None
    while True:
        try:
            el = page.query_selector(selector)
            if el:
                found_frame = page.main_frame
                element     = el
                break
        except Exception:
            pass

        for frame in page.frames:
            try:
                el = frame.query_selector(selector)
                if el:
                    element     = el
                    found_frame = frame
                    break
            except Exception:
                continue

        if element:
            break
        if deadline is None or time.time() >= deadline:
            return None, None, None
        time.sleep(poll_interval)

    if debug:
        print(f"[debug] found element in frame: {getattr(found_frame, 'url', '<main>')}")

    try:
        element.scroll_into_view_if_needed(timeout=500)
    except Exception:
        pass

    try:
        elem_rect = element.evaluate("""
            el => {
                const r = el.getBoundingClientRect();
                return {left: r.left, top: r.top, width: r.width, height: r.height};
            }
        """)
        if not elem_rect:
            return None, None, None
    except Exception as e:
        if debug:
            print(f"[debug] element.evaluate failed: {e}")
        return None, None, None

    total_left = float(elem_rect.get("left", 0.0))
    total_top  = float(elem_rect.get("top",  0.0))

    cur_frame = found_frame
    while cur_frame is not None and cur_frame != page.main_frame:
        try:
            iframe_el   = cur_frame.frame_element()
            iframe_rect = iframe_el.evaluate("""
                el => {
                    const r = el.getBoundingClientRect();
                    return {left: r.left, top: r.top, width: r.width, height: r.height};
                }
            """)
            if iframe_rect:
                total_left += float(iframe_rect.get("left", 0.0))
                total_top  += float(iframe_rect.get("top",  0.0))
                if debug:
                    print(f"[debug] added iframe rect: {iframe_rect}")
            else:
                try:
                    bb = iframe_el.bounding_box()
                    if bb:
                        total_left += float(bb.get("x", 0.0))
                        total_top  += float(bb.get("y", 0.0))
                except Exception:
                    pass
        except Exception as e:
            if debug:
                print(f"[debug] failed to get parent iframe rect: {e}")
            break

        try:
            cur_frame = cur_frame.parent_frame
        except Exception:
            cur_frame = None

    center_x_css = total_left + float(elem_rect.get("width",  0.0)) / 2.0
    center_y_css = total_top  + float(elem_rect.get("height", 0.0)) / 2.0

    try:
        dpr = float(page.evaluate("() => window.devicePixelRatio") or 1.0)
    except Exception:
        dpr = 1.0

    abs_x = int(browser_x + center_x_css * dpr + offset_x)
    abs_y = int(browser_y + center_y_css * dpr + offset_y)

    if debug:
        print(f"[debug] center_css=({center_x_css}, {center_y_css}), dpr={dpr}")
        print(f"[debug] screen coords -> ({abs_x}, {abs_y})")

    return abs_x, abs_y, element


def find_in_frames(page, selector, timeout=2.0, poll_interval=0.12):
    deadline = time.time() + timeout if timeout and timeout > 0 else None

    try:
        page.wait_for_load_state("domcontentloaded", timeout=500)
    except Exception:
        pass

    def search(frame):
        try:
            el = frame.query_selector(selector)
            if el:
                return frame, el
        except Exception:
            pass

        try:
            children = getattr(frame, "child_frames", None)
            if children is None:
                children = [f for f in page.frames if getattr(f, "parent_frame", None) is frame]
            for child in children:
                try:
                    found = search(child)
                    if found:
                        return found
                except Exception:
                    continue
        except Exception:
            pass

        return None

    while True:
        try:
            result = search(page.main_frame)
            if result:
                return result
        except Exception:
            pass

        if deadline is None or time.time() >= deadline:
            return None, None
        time.sleep(poll_interval)


_SPECIAL_SCHEMES = ("javascript:", "data:", "blob:")


def _is_special_scheme(el):
    try:
        href = (el.get_attribute("href") or "").strip().lower()
        return any(href.startswith(s) for s in _SPECIAL_SCHEMES)
    except Exception:
        return False


def mouse_click(page, tag, interaction="left", modifiers=None):
    try:
        page.bring_to_front()
    except Exception:
        pass
    frame, el = find_in_frames(page, tag, timeout=3.0)
    if el is None:
        return False

    try:
        if not (el.is_visible() and el.is_enabled()):
            print(f"[debug] {tag} is hidden or disabled")
            return False
    except Exception as e:
        print(f"[debug] visibility check failed: {e}")
        return False

    no_wait_after = _is_special_scheme(el)
    if no_wait_after:
        print(f"[debug] special scheme on {tag}, using no_wait_after=True")

    base_kwargs = dict(button=interaction, delay=100, timeout=3000)
    if modifiers is not None:
        base_kwargs["modifiers"] = modifiers

    try:
        el.click(no_wait_after=no_wait_after, **base_kwargs)
        return True
    except Exception as e:
        print(f"[debug] click attempt 1 failed: {e}")

    try:
        el.click(no_wait_after=True, **base_kwargs)
        return True
    except Exception as e:
        print(f"[debug] click attempt 2 (no_wait_after) failed: {e}")

    try:
        frame.locator(tag).click(no_wait_after=True, **base_kwargs)
        return True
    except Exception as e:
        print(f"[debug] click attempt 3 (locator) failed: {e}")
        return False


def mouse_userinter(page, tag, interaction, browser_x=0, browser_y=0,
                    offset_x=0, offset_y=110, submenu=False):
    abs_x, abs_y, element = get_element_screen_coords(
        page, tag, browser_x, browser_y, offset_x, offset_y, 2, 0.12, debug=True,
    )
    print(f"[debug] mouse_userinter: browser=({browser_x},{browser_y}) -> screen=({abs_x},{abs_y})")
    if element is None:
        print(f"[debug] element not found: {tag}")
        return False
    if not (element.is_visible() and element.is_enabled()):
        print(f"[debug] {tag} is hidden or disabled")
        return False

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


def keyboard_userinter(page, context, keyboard_title, keyboard, corpus_url):
    if "Reopen" in keyboard_title:
        new_page = context.new_page()
        time.sleep(0.3)
        new_page.goto("data:text/html,hi")
        page.bring_to_front()
        page.close()
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    elif "backward" in keyboard_title:
        page.goto("data:text/html,hi")
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    elif "forward" in keyboard_title:
        page.goto("data:text/html,hi")
        page.goto(corpus_url)
        time.sleep(0.3)
        page.go_back()
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    else:
        time.sleep(0.5)
        pyautogui.hotkey(*keyboard)

    time.sleep(0.3)
    pyautogui.press("f5")
    time.sleep(0.1)
    return True


def keyboard_with_click(page, context, keyboard_title, keyboard, tag):
    try:
        print(keyboard)
        mouse_click(page, tag, "left", keyboard)
    except Exception as e:
        print(f"[debug] keyboard_with_click error: {e}")
