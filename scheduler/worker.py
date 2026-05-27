import sys
import json
import socket
import threading
import subprocess
import tempfile
import base64
from pathlib import Path

import argparse

BUIZZ_ROOT = Path(__file__).resolve().parent.parent

FUZZER = {
    "v1": BUIZZ_ROOT / "fuzzer"   / "fuzzer.py",
    "v2": BUIZZ_ROOT / "fuzzerV2" / "fuzzer.py",
}
SCENARIO_GEN = BUIZZ_ROOT / "fuzzer" / "user_scenario_gen.py"
BASELINE     = BUIZZ_ROOT / "base_line.py"

_proc_lock    = threading.Lock()
_current_proc = None
_current_task = None


def _send(conn, obj):
    try:
        conn.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())
    except Exception:
        pass


def _recv_msg(conn):
    buf = b""
    while b"\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buf += chunk
    return json.loads(buf.split(b"\n")[0].decode())


def _handle_status(conn):
    with _proc_lock:
        running = _current_proc is not None and _current_proc.poll() is None
    _send(conn, {
        "status": "running" if running else "idle",
        "task":   _current_task if running else None,
    })


def _handle_stop(conn):
    global _current_proc, _current_task
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            _current_proc.terminate()
            _current_task = None
            _send(conn, {"status": "ok", "msg": "process terminated"})
        else:
            _send(conn, {"status": "ok", "msg": "no running task"})


def _run_subprocess(conn, cmd_args, cwd, task_desc):
    global _current_proc, _current_task

    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            _send(conn, {"status": "error", "msg": f"already running: {_current_task}"})
            return

    try:
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(cwd),
            text=True,
            bufsize=1,
        )
    except Exception as e:
        _send(conn, {"status": "error", "msg": str(e)})
        return

    with _proc_lock:
        _current_proc = proc
        _current_task = task_desc

    _send(conn, {"status": "started", "cmd": cmd_args, "task": task_desc})
    conn.close()

    print(f"[worker] START  {task_desc}")
    print(f"[worker] CMD    {' '.join(cmd_args)}")

    def _watch():
        global _current_task
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait()
        with _proc_lock:
            _current_task = None
        print(f"[worker] DONE   {task_desc}  (rc={proc.returncode})")

    threading.Thread(target=_watch, daemon=True).start()


def _handle_run_fuzzer(conn, args):
    version    = args.get("version", "v1")
    browser    = args.get("browser")
    policy     = args.get("policy")
    report_url = args.get("report_url")

    if not browser or not policy:
        _send(conn, {"status": "error", "msg": "browser and policy are required"})
        return
    if version not in FUZZER:
        _send(conn, {"status": "error", "msg": f"unknown version '{version}'"})
        return

    script = FUZZER[version]
    cmd = [sys.executable, str(script), "-b", browser, "-s", policy]
    if report_url:
        cmd += ["-r", report_url]

    task = f"fuzzer-{version} {browser}/{policy}"
    _run_subprocess(conn, cmd, script.parent, task)


def _handle_install_ca(conn, args):
    pem_b64 = args.get("pem_b64")
    if not pem_b64:
        _send(conn, {"status": "error", "msg": "pem_b64 is required"})
        return

    try:
        pem_bytes = base64.b64decode(pem_b64)
    except Exception as e:
        _send(conn, {"status": "error", "msg": f"base64 decode failed: {e}"})
        return

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        f.write(pem_bytes)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["certutil", "-addstore", "-f", "ROOT", tmp_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _send(conn, {"status": "ok", "msg": "CA installed successfully"})
            print(f"[worker] CA installed from {tmp_path}")
        else:
            _send(conn, {"status": "error", "msg": result.stdout + result.stderr})
    except Exception as e:
        _send(conn, {"status": "error", "msg": str(e)})
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _handle_run_baseline(conn, args):
    browser    = args.get("browser")
    policy     = args.get("policy")
    report_url = args.get("report_url")
    num_proc   = args.get("num_processes", "5")

    if not browser or not policy:
        _send(conn, {"status": "error", "msg": "browser and policy are required"})
        return

    cmd = [sys.executable, str(BASELINE), "-b", browser, "-s", policy, "-n", str(num_proc)]
    if report_url:
        cmd += ["-r", report_url]

    task = f"baseline {browser}/{policy}"
    _run_subprocess(conn, cmd, BUIZZ_ROOT, task)


def _handle_run_scenario_gen(conn, args):
    browser = args.get("browser")
    policy  = args.get("policy")
    depth   = args.get("depth", "1")
    count   = args.get("count")

    if not browser or not policy:
        _send(conn, {"status": "error", "msg": "browser and policy are required"})
        return

    cmd = [sys.executable, str(SCENARIO_GEN), "-b", browser, "-s", policy, "-d", str(depth)]
    if count is not None:
        cmd += ["-c", str(count)]

    task = f"scenario-gen {browser}/{policy} depth={depth}"
    _run_subprocess(conn, cmd, SCENARIO_GEN.parent, task)


def _handle_client(conn, addr):
    print(f"[worker] connect {addr}")
    try:
        msg = _recv_msg(conn)
        if msg is None:
            return

        cmd  = msg.get("cmd")
        args = msg.get("args", {})

        if   cmd == "status":           _handle_status(conn)
        elif cmd == "stop":             _handle_stop(conn)
        elif cmd == "run_fuzzer":       _handle_run_fuzzer(conn, args)
        elif cmd == "run_baseline":     _handle_run_baseline(conn, args)
        elif cmd == "run_scenario_gen": _handle_run_scenario_gen(conn, args)
        elif cmd == "install_ca":       _handle_install_ca(conn, args)
        else:
            _send(conn, {"status": "error", "msg": f"unknown cmd '{cmd}'"})

    except Exception as e:
        _send(conn, {"status": "error", "msg": str(e)})
    finally:
        conn.close()
        print(f"[worker] disconnect {addr}")


def main():
    parser = argparse.ArgumentParser(description="Fuzzer worker daemon")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9001)
    a = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((a.host, a.port))
        srv.listen(5)
        print(f"[worker] Listening on {a.host}:{a.port}")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=_handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
