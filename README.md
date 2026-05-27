# BUIZZ - Browser Userinterface Fuzzer

BUIZZ is the first framework that finds header security enforcement bugs by simulating realistic user interactions at the OS level.

![BUIZZ Overview](Figure/Figure-overview.png)

> **Minimal working example** — see [`example/README.md`](example/README.md) for a step-by-step walkthrough using the bundled Brave binary.

## Repository Structure

```
BUIZZ/
├── crawler/             # User interaction study data
├── example/             # Minimal working example
├── fuzzer/              # Core fuzzer
│   ├── fuzzer.py        #   Entry point
│   ├── user_scenario_gen.py  # Scenario generator
│   ├── lib/             #   Browser drivers & interaction helpers
│   ├── scenario/        #   Generated scenario JSON files
│   ├── test_list/       #   Corpus URL lists per policy
│   └── browser_info/    #   Browser executable paths & UI configuration
├── server/              # Per-policy report servers
│   ├── samesite/
│   ├── csp/
│   ├── coop/
│   ├── hsts/
│   ├── pp/
│   ├── rp/
│   ├── sandbox/
│   └── xfo/
├── fuzzerV2/            # Extended fuzzer variant
├── scheduler/           # Distributed fuzzing coordinator
├── bugs/                # Analyzer output
├── Figure/              # Paper figures
├── safe_error/          # Baseline-error URL list
├── analyzer.py          # Inconsistency analyzer
├── base_line.py         # Baseline collector
├── base_lineV2.py       # Extended baseline
├── deduping.py          # Bug deduplicator
├── makeDB.py            # Database initializer
├── schema.sql           # Database schema
├── setup.ps1            # Environment setup
└── certs.ps1            # TLS certificate generation
```

## Tested Environments

The artifact was developed and validated on the following setup:

| Component | Tested Version |
|---|---|
| **OS** | Windows 11 23H2 (64-bit) |
| **Python** | 3.11.x |
| **Playwright** | 1.44+ |
| **MySQL** | 8.0.x |
| **Docker Desktop** | 4.x |
| **Chrome** | 138 |
| **Firefox** | 139 |
| **Edge** | 136 |
| **Opera** | 118 |
| **Brave** | 1.79 |
| **Whale** | 4.32 |

**Hardware:** 16 GB RAM minimum, 50 GB free disk space recommended


## Prerequisites

The following programs must be installed before running BUIZZ:

| Program | Version | Purpose |
|---|---|---|
| **Windows 10/11** | 64-bit | Required OS — pywinauto and pyautogui drive real OS-level input |
| **Python** | 3.11+ | All fuzzer, analyzer, and server scripts |
| **Docker Desktop** | Latest | Runs the per-policy report servers via `docker compose` |
| **MySQL** | 8.0+ | Stores test results (`event_entry` table); must be running on `localhost:3306` with user `root` / password `1234` |
| **mkcert** | Latest | Generates locally-trusted TLS certificates (`certs.ps1` installs it automatically) |
| **Browsers** | See below | The actual browsers under test |

Browsers required (install only those you intend to test):

| Browser | Installer |
|---|---|
| Google Chrome | https://www.google.com/chrome |
| Microsoft Edge | Pre-installed on Windows 10/11 |
| Mozilla Firefox | https://www.mozilla.org/firefox |
| Brave | Portable binary bundled in `example/brave-v1.80.120-win32-x64/` — no installation needed |
| Opera | https://www.opera.com |
| Naver Whale | https://whale.naver.com |

## Setup

### 1. Install dependencies

Run `setup.ps1` **as Administrator** in PowerShell. It installs all required Python packages and automatically updates the hosts file with the required domains.

```powershell
# Auto-detect the local IP
PowerShell -ExecutionPolicy Bypass -File setup.ps1

# Specify an IP explicitly (e.g. when running the server on a separate machine)
PowerShell -ExecutionPolicy Bypass -File setup.ps1 10.20.23.182
```

If no IP is provided, the script detects the primary non-loopback IPv4 address of the current machine automatically.

The script installs the following packages and runs `playwright install`:

```
playwright  psutil  pywinauto  pyautogui  webdriver-manager  mysql-connector-python
```

> **Manual alternative** — if you prefer to install packages individually:
> ```bash
> pip install playwright psutil pywinauto pyautogui webdriver-manager mysql-connector-python
> python -m playwright install
> ```
> Then add the following entries to `C:\Windows\System32\drivers\etc\hosts`:
> ```
> <your-ip>  leak.test
> <your-ip>  adition.com
> <your-ip>  attacker.test
> <your-ip>  attacker.com
> <your-ip>  victim.com
> ```

### 2. Generate TLS certificates

Run `certs.ps1` to install mkcert and generate TLS certificates for all HTTPS servers:

```powershell
PowerShell -ExecutionPolicy Bypass -File certs.ps1
```

### 3. Create the database

```bash
python makeDB.py
```

## Collector

The `crawler` directory contains an XLSX file that comprehensively collects the user interactions gathered in our study.


## Simulator

### Server

Navigate to the target policy's server directory and start it using Docker Compose:

```bash
cd server/samesite
docker compose up
```

Available server directories: `csp`, `samesite`, `pp`, `coop`, `hsts`, `rp`, `xfo`, `sandbox`

### Scenario Generation

User interaction scenarios are generated using `user_scenario_gen.py` in the `fuzzer` directory.

```bash
python fuzzer/user_scenario_gen.py -s samesite -b chrome -d 1
```

| Option | Description |
|--------|-------------|
| `-b`   | Browser (`chrome`, `firefox`, `edge`, `opera`, `brave`, `whale`) |
| `-s`   | Security policy (`samesite`, `csp`, `sandbox`, `pp`, `coop`, `hsts`, `rp`, `xfo`) |
| `-d`   | Depth (`1` = single interaction, `2` = two-interaction combination) |

### OS-Level Simulation

The fuzzer is executed via `fuzzer.py`:

```bash
python fuzzer/fuzzer.py -s samesite -b chrome
```


## Detector

### Baseline collection

To record the pre-interaction state, run `base_line.py` to capture baseline enforcement behavior before any user interaction is performed:

```bash
python base_line.py -s samesite -b chrome
```

### Analysis

Run `analyzer.py` to compare pre-interaction and post-interaction enforcement outcomes and identify inconsistencies:

```bash
python analyzer.py -s samesite -b chrome
```

Add `--lenient` for higher recall (may increase noise):

```bash
python analyzer.py -s samesite -b chrome --lenient
```

Results are written to `bugs/<policy>/interaction_diff_<browser>.txt`.

### Deduplication

Run `deduping.py` to deduplicate flagged inconsistencies and group them into distinct root-cause bugs:

```bash
python deduping.py -s samesite
python deduping.py -s samesite -b chrome        # single browser
python deduping.py -s samesite --merge-tags     # merge by root cause
python deduping.py -s samesite -d 1             # depth-1 scenarios only
python deduping.py -s samesite -d 2             # depth-2 scenarios only
```

## Database Schema

The `event_entry` table stores all fuzzing and baseline records.  
See [`schema.sql`](schema.sql) for the full annotated schema, or run `python makeDB.py` to create the database automatically.

| Column | Description |
|---|---|
| `browser_name` | Browser under test (`chrome`, `firefox`, `brave`, …) |
| `scenario_id` | Scenario file name (e.g. `0_DEPTH1.json`); NULL for baseline records |
| `corpus` | Full URL of the corpus page loaded |
| `event_type` | `corpus` (baseline) or `interaction` (post-interaction result) |
| `corpus_type` | Security policy (`samesite`, `csp`, `referrer-policy`, …) |
| `leak` | Leak channel that triggered the report (e.g. `a-href`, `fetch`, `img`) |
| `violation` | Enforcement outcome reported by the server (e.g. `lax`, `1`, empty) |
| `interaction` | Human-readable label of the simulated interaction; NULL for baseline |
| `timestamp` | UTC timestamp of record insertion |