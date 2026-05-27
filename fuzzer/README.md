# fuzzer

The core OS-level browser fuzzer for BUIZZ. It launches real browsers, loads generated test scenarios, and drives user interactions at the OS level to detect security policy enforcement bugs.

## Entry Points

| Script | Purpose |
|---|---|
| `fuzzer.py` | Main fuzzer — loads scenarios and drives interactions for a given browser and policy |
| `user_scenario_gen.py` | Scenario generator — produces JSON test-case files from corpus URL lists |

## Directory Structure

```
fuzzer/
├── fuzzer.py               # Main entry point
├── user_scenario_gen.py    # Scenario generation
├── lib/                    # Per-browser execution cores
│   ├── core_common.py      # Shared execution logic (scenario loading, cookie injection, action dispatch)
│   ├── core_chrome.py      # Chrome / Chromium-based launcher
│   ├── core_edge.py        # Edge launcher
│   ├── core_opera.py       # Opera launcher
│   ├── core_brave.py       # Brave launcher
│   ├── core_whale.py       # Whale launcher
│   ├── core_firefox.py     # Firefox launcher
│   └── userinteraction.py  # Mouse and keyboard interaction primitives
├── browser_info/           # Browser executable path configs
├── browser_interaction/    # Per-browser interaction JSON definitions
├── cve_lib/                # Corpus URL lists per policy
├── test_list/              # Policy-specific test URL lists
└── scenario/               # Generated scenario JSON files (gitignored)
```

## Libraries

| Library | Role |
|---|---|
| **Playwright** (`playwright`) | Browser automation — launches browsers as persistent contexts, navigates to corpus URLs, and monitors new pages (popups) |
| **pyautogui** | OS-level mouse and keyboard input — moves the cursor, clicks, sends hotkeys at the screen coordinate level |
| **pywinauto** | Windows UI automation — finds browser window handles, brings windows to focus, reads window positions |
| **psutil** | Process management — detects running browser processes, kills stale instances between scenarios |
| **mysql-connector-python** | Database — writes test results (violation reports) to the MySQL `event_entry` table |

## How It Works

1. `user_scenario_gen.py` reads corpus URL lists from `test_list/<policy>/` and combines them with interaction definitions from `browser_interaction/<browser>.json` to produce numbered JSON scenario files under `scenario/<browser>/<policy>/`.
2. `fuzzer.py` iterates over scenario files, launches the target browser via the appropriate `lib/core_<browser>.py`, navigates to the corpus URL, and replays the interaction sequence using Playwright (page navigation, cookie injection) and pyautogui / pywinauto (OS-level mouse and keyboard events).
3. Any security policy violation detected during or after the interaction is written to MySQL for later analysis by `analyzer.py`.
