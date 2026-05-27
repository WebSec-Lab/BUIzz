#!/usr/bin/env python3
import argparse
import ast
import json
import os
import re
from collections import defaultdict
from urllib.parse import urlparse

ROOT_DIR     = os.path.dirname(__file__)
BUGS_DIR     = os.path.join(ROOT_DIR, "bugs")
SCENARIO_DIR = os.path.join(ROOT_DIR, "fuzzer", "scenario")
SERVER_DIR   = os.path.join(ROOT_DIR, "server")

_TAG_RELEVANT_POLICIES = {"hsts", "samesite", "rp"}

_LEAK_TAG_MAP = {
    "a-href":          "<a>",
    "a-ping":          "<a>",
    "area-href":       "<area>",
    "svg-href":        "<svg>",
    "form":            "<form>",
    "form-GET":        "<form>",
    "form-POST":       "<form>",
    "window-open":     "window.open",
    "websocket":       "WebSocket",
    "fetch":           "fetch",
    "xhr":             "XMLHttpRequest",
    "link-prefetch":   "<link>",
    "link-preload":    "<link>",
    "img":             "<img>",
    "script":          "<script>",
    "iframe":          "<iframe>",
    "redirect-winloc": "redirect(window.location)",
}


def _leak_to_tag(leak: str | None, policy: str) -> str:
    if policy not in _TAG_RELEVANT_POLICIES:
        return "*"
    if not leak:
        return "unknown"
    if re.match(r"header-3\d\d$", leak):
        return "redirect(3XX)"
    return _LEAK_TAG_MAP.get(leak, leak)


_SCHEME_INSPECT_POLICIES = {"csp1", "csp2", "pp", "sandbox"}

_POLICY_CORPUS_DIR = {
    "csp1":    os.path.join(SERVER_DIR, "csp",     "backend", "templates", "output"),
    "csp2":    os.path.join(SERVER_DIR, "csp",     "backend", "templates", "output"),
    "pp":      os.path.join(SERVER_DIR, "pp",      "backend", "templates", "output"),
    "sandbox": os.path.join(SERVER_DIR, "sandbox", "backend", "templates", "output"),
}

_corpus_scheme_cache: dict[tuple, str] = {}


def _corpus_filename(corpus_url: str) -> str | None:
    path = urlparse(corpus_url).path
    stem = path.rstrip("/").rsplit("/", 1)[-1]
    return stem if stem.startswith("sep_") else None


def _scheme_from_corpus_file(policy: str, corpus_url: str) -> str:
    stem = _corpus_filename(corpus_url)
    if not stem:
        return "https:"

    cache_key = (policy, stem)
    if cache_key in _corpus_scheme_cache:
        return _corpus_scheme_cache[cache_key]

    corpus_dir = _POLICY_CORPUS_DIR.get(policy, "")
    filepath   = os.path.join(corpus_dir, stem + ".html")
    result     = "https:"

    if os.path.isfile(filepath):
        try:
            content = open(filepath, encoding="utf-8", errors="replace").read()
            if "blob:" in content or "Blob(" in content:
                result = "blob:"
            elif "data:" in content:
                result = "data:"
        except OSError:
            pass

    _corpus_scheme_cache[cache_key] = result
    return result


def _extract_scheme(record: dict, policy: str) -> str:
    if policy in _SCHEME_INSPECT_POLICIES:
        return _scheme_from_corpus_file(policy, record.get("corpus") or "")
    return "https:"


_scenario_cache: dict = {}


def _load_scenario_interaction(browser: str | None, scenario_id: str | None) -> str | None:
    if not scenario_id:
        return None
    cache_key = (browser, scenario_id)
    if cache_key in _scenario_cache:
        return _scenario_cache[cache_key]

    browsers  = [browser] if browser else ["chrome", "firefox", "edge", "opera", "brave", "whale"]
    policies  = ["hsts", "samesite", "rp", "pp", "coop", "csp1", "csp2",
                 "sandbox", "xfo", "csp", "csp-frame"]

    for b in browsers:
        for policy in policies:
            path = os.path.join(SCENARIO_DIR, b, policy, scenario_id)
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    actions = data.get("useraction", [])
                    if actions:
                        title = actions[0].get("interaction", {}).get("title")
                        _scenario_cache[cache_key] = title
                        return title
                except Exception:
                    pass

    _scenario_cache[cache_key] = None
    return None


def _get_interaction(record: dict) -> str:
    interaction = record.get("interaction")
    if interaction:
        return str(interaction)

    browser     = record.get("browser_name") or record.get("_browser_file")
    scenario_id = record.get("scenario_id")
    from_file   = _load_scenario_interaction(browser, scenario_id)
    if from_file:
        return from_file

    return "unknown"


_INTERACTION_ALIASES = {
    "Middle click":              "Open link in background tab",
    "drag_and_drop":             "drag&drop",
    "drag_and_drop_to_other_window": "drag&drop (to other window)",
}


def _norm_interaction(raw: str) -> str:
    return _INTERACTION_ALIASES.get(raw, raw)


_DT_PATTERN = re.compile(r"datetime\.datetime\([^)]+\)")


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    line = _DT_PATTERN.sub("'<ts>'", line)
    try:
        return ast.literal_eval(line)
    except Exception:
        return None


def load_bugs(policy: str, browser: str | None, depth: int | None = None) -> list[dict]:
    policy_dir = os.path.join(BUGS_DIR, policy)
    if not os.path.isdir(policy_dir):
        return []

    depth_tag = f"DEPTH{depth}" if depth else None

    records = []
    for fname in sorted(os.listdir(policy_dir)):
        if not (fname.startswith("interaction_diff_") and fname.endswith(".txt")):
            continue
        b = fname.removeprefix("interaction_diff_").removesuffix(".txt")
        if browser and b != browser:
            continue
        with open(os.path.join(policy_dir, fname), encoding="utf-8") as f:
            for line in f:
                rec = _parse_line(line)
                if rec:
                    if depth_tag:
                        sid = rec.get("scenario_id") or ""
                        if depth_tag not in sid:
                            continue
                    rec["_browser_file"] = b
                    records.append(rec)
    return records


def make_triple(record: dict, policy: str) -> tuple[str, str, str]:
    interaction = _norm_interaction(_get_interaction(record))
    tag         = _leak_to_tag(record.get("leak"), policy)
    scheme      = _extract_scheme(record, policy)
    return (interaction, tag, scheme)


def deduplicate(records: list[dict], policy: str, merge_tags: bool = False) -> dict:
    raw: dict[tuple, list] = defaultdict(list)
    for rec in records:
        raw[make_triple(rec, policy)].append(rec)

    merged: dict[tuple, dict] = {}
    for triple, recs in raw.items():
        rc_key = (triple[0], triple[2]) if merge_tags else triple
        if rc_key not in merged:
            merged[rc_key] = {"triples": [], "records": [], "browsers": set()}
        merged[rc_key]["triples"].append(triple)
        merged[rc_key]["records"].extend(recs)
        for r in recs:
            merged[rc_key]["browsers"].add(r.get("browser_name") or r.get("_browser_file", "?"))

    return merged


def print_results(merged: dict, policy: str, browser: str | None,
                  merge_tags: bool, verbose: bool, depth: int | None = None) -> None:
    depth_note = f"  depth={depth}" if depth else ""
    scope = f"policy={policy}" + (f"  browser={browser}" if browser else "  (all browsers)") + depth_note
    merge_note = "  [tag-merge ON]" if merge_tags else ""
    print(f"\n{'='*60}")
    print(f"  BUIZZ deduplication - {scope}{merge_note}")
    print(f"{'='*60}")

    total_records = sum(len(g["records"]) for g in merged.values())
    print(f"  Raw inconsistency records : {total_records}")
    print(f"  Distinct bugs (after dedup): {len(merged)}\n")

    for i, (rc_key, data) in enumerate(sorted(merged.items()), 1):
        triples  = sorted(data["triples"])
        records  = data["records"]
        browsers = sorted(data["browsers"])
        n        = len(records)

        if merge_tags:
            interaction, scheme = rc_key
            primary_tags = ", ".join(sorted({t for (_, t, _) in triples}))
            header = f"({interaction}, [{primary_tags}], {scheme})"
        else:
            interaction, tag, scheme = rc_key
            header = f"({interaction}, {tag}, {scheme})"

        merge_flag = f"  ← {len(triples)} variants merged" if len(triples) > 1 else ""
        print(f"  Bug #{i:02d}: {header}{merge_flag}")
        print(f"           browsers : {', '.join(browsers)}")
        print(f"           records  : {n}")

        if len(triples) > 1:
            for t in triples:
                print(f"           variant  : ({t[0]}, {t[1]}, {t[2]})")

        if verbose:
            for r in records[:5]:
                sid = r.get("scenario_id", "-")
                leak = r.get("leak", "-")
                ts   = r.get("timestamp", r.get("_ts", "-"))
                print(f"             [{sid}] leak={leak} ts={ts}")
            if n > 5:
                print(f"             ... and {n - 5} more")

        print()

    print(f"  Total distinct bugs: {len(merged)}")
    print()


def _parse_args():
    p = argparse.ArgumentParser(
        description="Deduplicate BUIZZ inconsistencies by (interaction, tag, scheme) triple"
    )
    p.add_argument("-s", "--policy", required=True,
                   help="Policy name under bugs/  (e.g. samesite, hsts, rp)")
    p.add_argument("-b", "--browser",
                   choices=["chrome", "firefox", "edge", "opera", "brave", "whale"],
                   default=None,
                   help="Limit to one browser (default: all)")
    p.add_argument("--merge-tags", action="store_true",
                   help="Merge groups that share (interaction, scheme) as same root cause")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Show sample records for each group")
    p.add_argument("-d", "--depth", type=int, choices=[1, 2], default=None,
                   help="Filter by scenario depth (1 or 2). Default: all depths combined")
    return p.parse_args()


if __name__ == "__main__":
    args    = _parse_args()
    records = load_bugs(args.policy, args.browser, depth=args.depth)

    if not records:
        who = f"policy='{args.policy}'" + (f", browser='{args.browser}'" if args.browser else "")
        who += f", depth={args.depth}" if args.depth else ""
        print(f"[!] No records found for {who}")
        print(f"    Expected files in: {os.path.join(BUGS_DIR, args.policy)}/interaction_diff_<browser>.txt")
    else:
        merged = deduplicate(records, args.policy, merge_tags=args.merge_tags)
        print_results(merged, args.policy, args.browser, args.merge_tags, args.verbose, depth=args.depth)
