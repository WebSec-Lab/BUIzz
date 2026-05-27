import sys
import json
import socket
import argparse
import threading
import base64
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9001

_TERMINAL = {"done", "error", "idle", "running", "ok"}


def _connect(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def _send(sock, obj):
    sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())


def _iter_messages(sock):
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line:
                yield json.loads(line.decode())


def _exchange(host, port, payload):
    with _connect(host, port) as sock:
        _send(sock, payload)
        for msg in _iter_messages(sock):
            status = msg.get("status")
            if "output" in msg:
                sys.stdout.write(msg["output"])
                sys.stdout.flush()
            else:
                print(f"[master] {msg}", flush=True)
            if status in _TERMINAL:
                return msg
    return None


def _probe(ip, port, results, lock):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((ip, port))
        _send(s, {"cmd": "status", "args": {}})
        s.settimeout(2.0)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        s.close()
        msg = json.loads(buf.split(b"\n")[0].decode())
        with lock:
            results.append((ip, msg))
    except Exception:
        pass


def cmd_scan(args):
    subnet   = args.subnet
    port     = args.port
    threads  = []
    results  = []
    lock     = threading.Lock()

    print(f"[scan] Scanning {subnet}.1-254 port {port} ...")
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        t  = threading.Thread(target=_probe, args=(ip, port, results, lock), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if not results:
        print("[scan] No workers found.")
        return

    results.sort(key=lambda x: int(x[0].rsplit(".", 1)[-1]))
    print(f"[scan] Found {len(results)} worker(s):")
    for ip, msg in results:
        status = msg.get("status", "?")
        task   = msg.get("task") or "-"
        print(f"  {ip}  status={status}  task={task}")


def _find_mkcert_ca(pem_path=None):
    if pem_path:
        p = Path(pem_path)
        if not p.exists():
            raise FileNotFoundError(f"PEM not found: {p}")
        return p

    local_app_data = Path.home() / "AppData" / "Local" / "mkcert"
    candidate = local_app_data / "rootCA.pem"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        "mkcert rootCA.pem not found. "
        "Run 'mkcert -install' first, or pass --pem <path>."
    )


def cmd_install_ca(args):
    try:
        pem_path = _find_mkcert_ca(args.pem)
    except FileNotFoundError as e:
        print(f"[master] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    pem_b64 = base64.b64encode(pem_path.read_bytes()).decode()
    print(f"[master] Sending {pem_path.name} ({pem_path.stat().st_size} bytes) to worker ...")
    _exchange(args.host, args.port, {"cmd": "install_ca", "args": {"pem_b64": pem_b64}})


def cmd_status(args):
    _exchange(args.host, args.port, {"cmd": "status", "args": {}})


def cmd_stop(args):
    _exchange(args.host, args.port, {"cmd": "stop", "args": {}})


def cmd_run_fuzzer(args):
    a = {
        "version":    "v2" if args.v2 else "v1",
        "browser":    args.browser,
        "policy":     args.policy,
    }
    if args.report_url:
        a["report_url"] = args.report_url
    _exchange(args.host, args.port, {"cmd": "run_fuzzer", "args": a})


def cmd_run_baseline(args):
    a = {
        "browser":       args.browser,
        "policy":        args.policy,
        "num_processes": str(args.num_processes),
    }
    if args.report_url:
        a["report_url"] = args.report_url
    _exchange(args.host, args.port, {"cmd": "run_baseline", "args": a})


def cmd_run_scenario_gen(args):
    a = {
        "browser": args.browser,
        "policy":  args.policy,
        "depth":   str(args.depth),
    }
    if args.count is not None:
        a["count"] = str(args.count)
    _exchange(args.host, args.port, {"cmd": "run_scenario_gen", "args": a})


def build_parser():
    p = argparse.ArgumentParser(description="Send commands to fuzzer worker")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = p.add_subparsers(dest="subcmd", required=True)

    sub.add_parser("status", help="Show worker status")
    sub.add_parser("stop",   help="Stop running task")

    rf = sub.add_parser("run-fuzzer", help="Run fuzzer on worker")
    rf.add_argument("-b", "--browser",    required=True)
    rf.add_argument("-s", "--policy",     required=True)
    rf.add_argument("-r", "--report-url", dest="report_url", default=None)
    rf.add_argument("--v2", action="store_true", help="Use fuzzerV2 (Selenium)")

    rb = sub.add_parser("run-baseline", help="Run baseline crawler on worker")
    rb.add_argument("-b", "--browser",       required=True)
    rb.add_argument("-s", "--policy",        required=True)
    rb.add_argument("-r", "--report-url",    dest="report_url", default=None)
    rb.add_argument("-n", "--num-processes", dest="num_processes", type=int, default=5)

    rsg = sub.add_parser("run-scenario-gen", help="Run scenario generator on worker")
    rsg.add_argument("-b", "--browser", required=True)
    rsg.add_argument("-s", "--policy",  required=True)
    rsg.add_argument("-d", "--depth",   type=int, default=1)
    rsg.add_argument("-c", "--count",   type=int, default=None)

    sc = sub.add_parser("scan", help="Scan subnet for running workers")
    sc.add_argument("--subnet", default="10.20.23", help="First 3 octets, e.g. 10.20.23")

    ic = sub.add_parser("install-ca", help="Push mkcert root CA to worker and install it")
    ic.add_argument("--pem", default=None, help="Path to rootCA.pem (default: mkcert CAROOT)")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    dispatch = {
        "status":           cmd_status,
        "stop":             cmd_stop,
        "run-fuzzer":       cmd_run_fuzzer,
        "run-baseline":     cmd_run_baseline,
        "run-scenario-gen": cmd_run_scenario_gen,
        "scan":             cmd_scan,
        "install-ca":       cmd_install_ca,
    }
    try:
        dispatch[args.subcmd](args)
    except ConnectionRefusedError:
        print(f"[master] ERROR: cannot connect to worker at {args.host}:{args.port}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
