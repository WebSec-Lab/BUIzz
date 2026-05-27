import json
import sys
import random
import argparse
import urllib.parse
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent

POLICY_FILES = {
    "samesite": [
        "test_list/samesite/samesite-test-list.txt",
        "test_list/samesite/samesite-test-list-need-mouse.txt",
    ],
    "csp1": [
        path
        for i in range(10)
        for path in (
            f"test_list/csp/csp-test-list-{i}.txt",
            f"test_list/csp/csp-test-list-need-mouse-{i}.txt",
        )
    ],
    "csp2": [
        path
        for i in range(10, 21)
        for path in (
            f"test_list/csp/csp-test-list-{i}.txt",
            f"test_list/csp/csp-test-list-need-mouse-{i}.txt",
        )
    ],
    "csp3": [
        path
        for i in range(4)
        for path in (
            f"test_list/csp/csp-test-list-{i}.txt",
            f"test_list/csp/csp-test-list-need-mouse-{i}.txt",
        )
    ],
    "coop": [
        "test_list/coop/coop-test-list.txt",
        "test_list/coop/coop-test-list-need-mouse.txt",
    ],
    "rp": [
        "test_list/rp/rp-test-list.txt",
        "test_list/rp/rp-test-list-need-mouse.txt",
    ],
    "pp": [
        "test_list/pp/pp-test-list.txt",
        "test_list/pp/pp-test-list-need-mouse.txt",
    ],
    "sandbox": [
        "test_list/sandbox/sandbox-test-list.txt",
        "test_list/sandbox/sandbox-test-list-need-mouse.txt",
    ],
    "hsts": [
        "test_list/hsts/hsts-test-list.txt",
        "test_list/hsts/hsts-test-list-need-mouse.txt",
    ],
    "xfo": [
        "test_list/xfo/xfo-test-list.txt",
        "test_list/xfo/xfo-test-list-need-mouse.txt",
    ],
    "test": [
        "test_list/test/test-test-list.txt",
        "test_list/test/test-test-list-need-mouse.txt",
    ],
}

_CSP_POLICIES = {"csp1", "csp2", "csp3", "test"}

_POLICY_FOLDER = {
    "csp3": "csp1",
}
_SPLIT_KEYWORDS = ("split", "dual")


class _Counter:
    def __init__(self, max_count=None):
        self._n = 0
        self.max_count = max_count

    def next(self):
        n = self._n
        self._n += 1
        if self.max_count is not None and self._n > self.max_count:
            print(f"[+] {self.max_count} scenarios generated — done")
            sys.exit(0)
        return n


class Scenario:
    def __init__(self, browser, corpus, security_policy):
        self.browser         = browser
        self.corpus          = corpus
        self.security_policy = security_policy
        self.user_actions    = []

    def add_action(self, action):
        self.user_actions.append(action)

    def to_dict(self):
        return {
            "browser":    self.browser,
            "corpus":     self.corpus,
            "useraction": self.user_actions,
        }

    def save(self, counter, depth):
        num      = counter.next()
        bf       = "1" if self.user_actions else "0"
        filename = f"{num}_DEPTH{depth}.json"

        tracking = urllib.parse.urlencode({
            "browser_name": self.browser,
            "scenario_id":  filename,
            "bf":           bf,
            "corpus":       self.corpus,
        })
        sep = "&" if "?" in self.corpus else "?"
        tracked_corpus = self.corpus + sep + tracking

        folder_policy = _POLICY_FOLDER.get(self.security_policy, self.security_policy)
        out_path = (
            _BASE_DIR / "scenario" / self.browser / folder_policy
            / filename
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"browser": self.browser, "corpus": tracked_corpus, "useraction": self.user_actions}
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved: {out_path}")
        return out_path


def _is_split(interaction):
    return any(kw in interaction["title"] for kw in _SPLIT_KEYWORDS)


def depth_one_scenario(data, tag, action_click, action_mouse, action_keyboard,
                       action_cve, action_keyboard_with_click,
                       browser_name, security_policy, counter, depth, rand_cve=False):
    with_link, without_link = data

    if security_policy == "xfo":
        for test_list in without_link:
            for keyboard in action_keyboard:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "keyboard", "interaction": keyboard, "tag": None})
                s.save(counter, depth)
        return

    for test_list in with_link:
        for click in action_click:
            if click["title"] == "Left click":
                continue
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "click", "interaction": click, "tag": tag})
            s.save(counter, depth)

    for test_list in with_link:
        for mouse_ui in action_mouse:
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "mouse", "interaction": mouse_ui, "tag": tag})
            s.save(counter, depth)

    for test_list in with_link:
        cve_list = [random.choice(action_cve)] if rand_cve else action_cve
        for cve in cve_list:
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "cve", "interaction": cve, "tag": tag})
            s.save(counter, depth)

    if action_keyboard_with_click:
        for test_list in with_link:
            for kwc in action_keyboard_with_click:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "keyboard_with_click", "interaction": kwc, "tag": tag})
                s.save(counter, depth)

    for test_list in with_link:
        for keyboard in action_keyboard:
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
            s.add_action({"type": "keyboard", "interaction": keyboard,        "tag": None})
            s.save(counter, depth)

    for test_list in without_link:
        for keyboard in action_keyboard:
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "keyboard", "interaction": keyboard, "tag": None})
            s.save(counter, depth)


def depth_two_scenario(data, tag, action_click, action_mouse, action_keyboard,
                       action_cve, browser_name, security_policy, counter, depth, rand_cve=False):
    with_link, without_link = data

    if security_policy == "xfo":
        for test_list in without_link:
            for kb1 in action_keyboard:
                for kb2 in action_keyboard:
                    s = Scenario(browser_name, test_list, security_policy)
                    s.add_action({"type": "keyboard", "interaction": kb1, "tag": None})
                    s.add_action({"type": "keyboard", "interaction": kb2, "tag": None})
                    s.save(counter, depth)
        return

    for test_list in with_link:
        for split_view in action_mouse:
            if not _is_split(split_view):
                continue

            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "mouse", "interaction": split_view,      "tag": tag})
            s.add_action({"type": "click", "interaction": action_click[1], "tag": tag})
            s.save(counter, depth)

            for mouse_ui in action_mouse:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse", "interaction": split_view, "tag": tag})
                s.add_action({"type": "mouse", "interaction": mouse_ui,   "tag": tag})
                s.save(counter, depth)

            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "mouse", "interaction": split_view, "tag": tag})
            s.add_action({"type": "cve",   "interaction": random.choice(action_cve) if rand_cve else action_cve[0], "tag": tag})
            s.save(counter, depth)

            for keyboard in action_keyboard:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse",    "interaction": split_view,      "tag": tag})
                s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
                s.add_action({"type": "keyboard", "interaction": keyboard,        "tag": None})
                s.save(counter, depth)

    for test_list in with_link:
        for kb1 in action_keyboard:
            for kb2 in action_keyboard:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
                s.add_action({"type": "keyboard", "interaction": kb1,             "tag": None})
                s.add_action({"type": "keyboard", "interaction": kb2,             "tag": None})
                s.save(counter, depth)

    for test_list in without_link:
        for kb1 in action_keyboard:
            for kb2 in action_keyboard:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "keyboard", "interaction": kb1, "tag": None})
                s.add_action({"type": "keyboard", "interaction": kb2, "tag": None})
                s.save(counter, depth)


def depth_two_scenario_for_CSP(data, tag, action_click, action_mouse, action_keyboard,
                                action_cve, browser_name, security_policy, counter, depth, rand_cve=False):
    random.seed(0)
    with_link, without_link = data
    split_views = [m for m in action_mouse if _is_split(m)]
    has_split   = browser_name in ("whale", "brave", "edge")

    for test_list in with_link:
        if has_split and split_views:
            case = random.randint(1, 5)
            split_view = random.choice(split_views)

            if case == 1:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse", "interaction": split_view,      "tag": tag})
                s.add_action({"type": "click", "interaction": action_click[1], "tag": tag})
                s.save(counter, depth)

            elif case == 2:
                mouse_ui = random.choice(action_mouse)
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse", "interaction": split_view, "tag": tag})
                s.add_action({"type": "mouse", "interaction": mouse_ui,   "tag": tag})
                s.save(counter, depth)

            elif case == 3:
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse", "interaction": split_view, "tag": tag})
                s.add_action({"type": "cve",   "interaction": random.choice(action_cve) if rand_cve else action_cve[0], "tag": tag})
                s.save(counter, depth)

            elif case == 4:
                keyboard = random.choice(action_keyboard)
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "mouse",    "interaction": split_view,      "tag": tag})
                s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
                s.add_action({"type": "keyboard", "interaction": keyboard,        "tag": None})
                s.save(counter, depth)

            else:
                kb1 = random.choice(action_keyboard)
                kb2 = random.choice(action_keyboard)
                s = Scenario(browser_name, test_list, security_policy)
                s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
                s.add_action({"type": "keyboard", "interaction": kb1,             "tag": None})
                s.add_action({"type": "keyboard", "interaction": kb2,             "tag": None})
                s.save(counter, depth)
        else:
            kb1 = random.choice(action_keyboard)
            kb2 = random.choice(action_keyboard)
            s = Scenario(browser_name, test_list, security_policy)
            s.add_action({"type": "click",    "interaction": action_click[0], "tag": tag})
            s.add_action({"type": "keyboard", "interaction": kb1,             "tag": None})
            s.add_action({"type": "keyboard", "interaction": kb2,             "tag": None})
            s.save(counter, depth)

    for test_list in without_link:
        kb1 = random.choice(action_keyboard)
        kb2 = random.choice(action_keyboard)
        s = Scenario(browser_name, test_list, security_policy)
        s.add_action({"type": "keyboard", "interaction": kb1, "tag": None})
        s.add_action({"type": "keyboard", "interaction": kb2, "tag": None})
        s.save(counter, depth)


def get_userinter(browser_name):
    path = _BASE_DIR / "browser_interaction" / f"{browser_name}.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_test_lists(security_policy):
    if security_policy not in POLICY_FILES:
        raise ValueError(f"Unknown security policy: '{security_policy}'")

    with_hyperlink    = []
    without_hyperlink = []

    for rel_path in POLICY_FILES[security_policy]:
        path = _BASE_DIR / rel_path
        if not path.exists():
            print(f"[!] Missing test list: {path}")
            continue
        entries = [
            line.strip()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip().startswith("http")
        ]
        if "mouse" in path.name:
            with_hyperlink.extend(entries)
        else:
            without_hyperlink.extend(entries)

    return with_hyperlink, without_hyperlink


def parse_args():
    parser = argparse.ArgumentParser(description="Generate fuzzer scenario JSON files")
    parser.add_argument("-b", "--browser",  type=str, required=True,
                        help="Target browser name")
    parser.add_argument("-s", "--security", type=str, required=True,
                        help="Security policy")
    parser.add_argument("-c", "--count",    type=int, required=False,
                        help="Max scenarios in thousands (e.g. -c 3 → 3000 scenarios)")
    parser.add_argument("-rc", "--rand_cve", action="store_true",
                        help="Pick one CVE (drag-and-drop) interaction at random per URL "
                             "instead of generating a scenario for every CVE variant")
    parser.add_argument("-d", "--depth",    type=str, required=True,
                        choices=["1", "2"],
                        help="Scenario depth (1 or 2)")
    return parser.parse_args()


if __name__ == "__main__":
    args            = parse_args()
    browser_name    = args.browser
    security_policy = args.security
    depth           = args.depth
    max_count       = args.count * 1000 if args.count is not None else None
    rand_cve        = args.rand_cve

    try:
        with_link, without_link = read_test_lists(security_policy)
    except ValueError as e:
        print(f"[-] {e}")
        sys.exit(1)

    if not with_link and not without_link:
        print("[-] No test URLs loaded — check test_list files.")
        sys.exit(1)

    data    = (with_link, without_link)
    counter = _Counter(max_count)
    tag     = "#a1"

    action          = get_userinter(browser_name)
    action_click    = action.get("click", [])
    action_mouse    = action.get("mouse", [])
    action_keyboard = action.get("keyboard", [])
    action_cve      = action.get("cve", [])
    action_kwc      = action.get("keyboard_with_click")

    if depth == "1":
        depth_one_scenario(
            data, tag, action_click, action_mouse, action_keyboard,
            action_cve, action_kwc, browser_name, security_policy, counter, depth,
            rand_cve=rand_cve,
        )
    elif depth == "2" and security_policy not in _CSP_POLICIES:
        depth_two_scenario(
            data, tag, action_click, action_mouse, action_keyboard,
            action_cve, browser_name, security_policy, counter, depth,
            rand_cve=rand_cve,
        )
    elif depth == "2" and security_policy in _CSP_POLICIES:
        depth_two_scenario_for_CSP(
            data, tag, action_click, action_mouse, action_keyboard,
            action_cve, browser_name, security_policy, counter, depth,
            rand_cve=rand_cve,
        )
    else:
        print(f"[-] Unsupported depth/policy combination: depth={depth}, policy={security_policy}")
        sys.exit(1)

    print(f"\n[FIN] Total scenarios generated: {counter._n}")
