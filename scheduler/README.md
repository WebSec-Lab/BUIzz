# scheduler Usage

## 1. Start worker (on the machine with browsers installed)

```
python worker.py
```

---

## 2. master commands

### Check status
```
python master.py --host <worker_ip> status
```

### Stop running task
```
python master.py --host <worker_ip> stop
```

### Run fuzzer
```
python master.py --host <worker_ip> run-fuzzer -b <browser> -s <policy>
python master.py --host <worker_ip> run-fuzzer -b <browser> -s <policy> --v2
```

- Browsers: `chrome` `edge` `firefox` `brave` `whale` `opera`
- Policies: `samesite` `rp` `hsts` `csp1` `csp2` `pp` `xfo` `coop` `sandbox` `test`
- `--v2` : Use Selenium-based fuzzerV2 (default is Playwright)

### Run baseline

```
python master.py --host <worker_ip> run-baseline -b <browser> -s <policy>
python master.py --host <worker_ip> run-baseline -b <browser> -s <policy> -n 3
python master.py --host <worker_ip> run-baseline -b <browser> -s <policy> -r https://attacker.com
```

- `-n` : number of parallel processes (default: 5)
- `-r` : report URL (default: auto-configured per policy)
- Policies: `samesite` `rp` `hsts` `csp` `pp` `xfo` `coop` `sandbox` `test`

### Run scenario generator
```
python master.py --host <worker_ip> run-scenario-gen -b <browser> -s <policy>
python master.py --host <worker_ip> run-scenario-gen -b <browser> -s <policy> -d 2 -c 100
```

- `-d` : depth (default: 1)
- `-c` : number of scenarios to generate (default: unlimited)

### Scan for workers
```
python master.py scan
python master.py scan --subnet 10.20.23
```

---

## Examples

```
python master.py --host 10.20.23.238 status
python master.py --host 10.20.23.238 run-fuzzer -b chrome -s test
python master.py --host 10.20.23.238 run-fuzzer -b firefox -s samesite --v2
python master.py --host 10.20.23.238 stop
python master.py --host 10.20.23.238 run-baseline -b chrome -s csp
python master.py --host 10.20.23.238 run-baseline -b chrome -s pp -n 3
python master.py scan
```
