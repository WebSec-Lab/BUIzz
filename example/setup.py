import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

BRAVE_VERSION = "1.80.120"
BRAVE_ZIP_NAME = f"brave-v{BRAVE_VERSION}-win32-x64.zip"
BRAVE_URL = f"https://github.com/brave/brave-browser/releases/download/v{BRAVE_VERSION}/{BRAVE_ZIP_NAME}"

EXAMPLE_DIR = Path(__file__).resolve().parent
EXTRACT_DIR = EXAMPLE_DIR / f"brave-v{BRAVE_VERSION}-win32-x64"
ZIP_PATH    = EXAMPLE_DIR / BRAVE_ZIP_NAME
# Dedicated profile so the pinned portable Brave never collides with a
# system-installed (newer) Brave's default profile.
PROFILE_DIR = EXAMPLE_DIR / "brave-profile"
# Pre-configured profile shipped with the artifact (Shields disabled, English UI,
# startup = New Tab). Seeded into PROFILE_DIR so no manual Brave setup is needed.
TEMPLATE_DIR = EXAMPLE_DIR / "brave-profile-template"

BROWSER_INFO_PATH = Path(__file__).resolve().parent.parent / "fuzzer" / "browser_info" / "browser_info.json"


def download(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    def _progress(count, block_size, total):
        pct = count * block_size * 100 // total if total > 0 else 0
        print(f"\r  {min(pct, 100):3d}%", end="", flush=True)
    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()


def extract(zip_path: Path, dest: Path) -> None:
    print(f"Extracting to {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = dest / member.filename
            if member.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as out:
                    out.write(src.read())
    print("  Done.")


def update_browser_info(brave_exe: Path) -> None:
    with open(BROWSER_INFO_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    cmd = (
        f'"{brave_exe}" --user-data-dir="{PROFILE_DIR}"'
        " --lang=en-US --no-first-run --no-default-browser-check"
        " --remote-debugging-port=9222 --start-maximized --disable-extensions"
    )
    for entry in entries:
        if entry.get("browser_name") == "brave":
            entry["browser_dir_command"] = cmd
            break

    with open(BROWSER_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"browser_info.json updated: {cmd}")


def seed_profile() -> None:
    """Copy the pre-configured profile template into the working profile so Brave
    starts with Shields disabled + English UI. Skips if a profile already exists
    (so re-running setup.py never wipes the reviewer's state)."""
    working_pref = PROFILE_DIR / "Default" / "Preferences"
    if working_pref.exists():
        print(f"Profile already present, leaving as-is: {PROFILE_DIR}")
        return
    template_pref = TEMPLATE_DIR / "Default" / "Preferences"
    if not template_pref.exists():
        print(f"WARNING: profile template missing ({template_pref}); "
              "Brave will start unconfigured — disable Shields manually.")
        return
    working_pref.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_pref, working_pref)
    print(f"Seeded pre-configured profile -> {PROFILE_DIR}")


def main() -> None:
    if not ZIP_PATH.exists():
        download(BRAVE_URL, ZIP_PATH)
    else:
        print(f"Zip already exists: {ZIP_PATH}")

    if not EXTRACT_DIR.exists():
        extract(ZIP_PATH, EXTRACT_DIR)
    else:
        print(f"Already extracted: {EXTRACT_DIR}")

    brave_exe = EXTRACT_DIR / "brave.exe"
    if not brave_exe.exists():
        candidates = list(EXTRACT_DIR.rglob("brave.exe"))
        if not candidates:
            print("ERROR: brave.exe not found after extraction.", file=sys.stderr)
            sys.exit(1)
        brave_exe = candidates[0]

    update_browser_info(brave_exe)
    seed_profile()
    print(f"\nDone. Brave exe: {brave_exe}")


if __name__ == "__main__":
    main()
