import os
import argparse
import mysql.connector
from pathlib import Path
from urllib.parse import parse_qs, urlencode


def _get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "1234"),
        database=os.environ.get("DB_NAME", "diffuserinter"),
    )


def get_base_line(conn, browser_name, security_policy):
    query = """
        SELECT *
        FROM event_entry
        WHERE browser_name = %s
          AND event_type = 'corpus'
          AND corpus_type = %s
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (browser_name, security_policy))
        return cursor.fetchall()
    finally:
        cursor.close()


def select_interaction_diff(conn, browser_name, security_policy):
    query = """
        SELECT *
        FROM event_entry
        WHERE browser_name = %s
          AND event_type = 'interaction'
          AND corpus_type = %s
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (browser_name, security_policy))
        return cursor.fetchall()
    finally:
        cursor.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Interaction diff analyzer")
    parser.add_argument("-b", "--browser", type=str, required=True,
                        choices=["edge", "chrome", "firefox", "whale", "opera", "brave"])
    parser.add_argument("-s", "--security-policy", type=str, required=True,
                        choices=["samesite", "csp", "coop", "rp", "pp", "sandbox", "hsts", "xfo", "test"])
    parser.add_argument("--lenient", action="store_true",
                        help="Also flag fuzzer events whose (corpus, leak) key is absent from "
                             "baseline. Higher recall (catches novel leak channels opened by BUI "
                             "interactions) at the cost of more noise from baseline sampling gaps. "
                             "Default is strict mode: only flag value-mismatches.")
    return parser.parse_args()


def _base_url(url, keep_params=None):
    if not url or "?" not in url:
        return url
    base, qs = url.split("?", 1)
    if not keep_params:
        return base
    kept = {k: v[:1] for k, v in parse_qs(qs, keep_blank_values=True).items() if k in keep_params}
    return base + "?" + urlencode(kept, doseq=True) if kept else base


_CORPUS_TYPE_MAP = {
    "rp":  "referrer-policy",
    "pp":  "permission-policy",
    "xfo": "x-frame-options",
}

_SILENT_POLICIES = {"csp", "sandbox"}

_ERROR_LOG = Path(__file__).resolve().parent / "safe_error" / "err-list-need-mouse.txt"


def _load_error_urls():
    if not _ERROR_LOG.exists():
        return set()
    return {
        line.strip()
        for line in _ERROR_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

if __name__ == "__main__":
    args            = parse_args()
    browser_name    = args.browser
    security_policy = args.security_policy
    corpus_type     = _CORPUS_TYPE_MAP.get(security_policy, security_policy)

    base_line_browser = "firefox" if browser_name == "firefox" else "chrome"

    out_dir  = Path(__file__).resolve().parent / "bugs" / security_policy
    out_file = str(out_dir / f"interaction_diff_{browser_name}.txt")
    out_dir  = str(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    error_urls = _load_error_urls() if security_policy in _SILENT_POLICIES else set()
    if error_urls:
        print(f"[info] loaded {len(error_urls)} baseline-error URL(s) from {_ERROR_LOG.name}")

    conn = _get_connection()
    try:
        keep_params  = {"policy"} if security_policy == "rp" else None

        base_line    = get_base_line(conn, base_line_browser, corpus_type)
        baseline_map = {
            _base_url(bl["corpus"], keep_params) + bl["leak"]: bl["violation"]
            for bl in base_line
        }
        baseline_corpus_urls = {
            _base_url(bl["corpus"], keep_params)
            for bl in base_line
            if bl["violation"]
        }

        interactions = select_interaction_diff(conn, browser_name, corpus_type)
        flagged = 0
        skipped_errors = 0
        with open(out_file, "w", encoding="utf-8") as f:
            for row in interactions:
                key = _base_url(row["corpus"], keep_params) + row["leak"]
                if security_policy in _SILENT_POLICIES:
                    corpus_url = row["corpus"] or ""
                    if corpus_url in error_urls or corpus_url.split("?")[0] in error_urls:
                        skipped_errors += 1
                        continue
                    base = _base_url(corpus_url, keep_params)
                    hit = bool(row["violation"]) and base not in baseline_corpus_urls
                elif args.lenient:
                    hit = key not in baseline_map or baseline_map[key] != row["violation"]
                else:
                    hit = key in baseline_map and baseline_map[key] != row["violation"]
                if hit:
                    f.write(str(row) + "\n")
                    flagged += 1
        mode = "lenient" if args.lenient else "strict"
        if security_policy in _SILENT_POLICIES:
            print(f"[silent-enforcement] flagged {flagged}/{len(interactions)} interaction rows"
                  + (f"  (skipped {skipped_errors} baseline-error URL(s))" if skipped_errors else ""))
        else:
            print(f"[{mode}] flagged {flagged}/{len(interactions)} interaction rows")
    finally:
        conn.close()

    print(f"[+] Results written to {out_file}")
