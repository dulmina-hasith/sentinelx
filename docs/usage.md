# SentinelX Usage Guide

This guide covers running the SentinelX daemon against both **mock fixture
files** and **real authentication logs**, and how to read what the system
produces (CLI logs, JSON API, web dashboard, WebSocket events).

The end-to-end demo flow is the fastest way to validate a deployment:

```bash
./manage.sh export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run          # daemon + dashboard
./manage.sh mock-logs    # generate traffic
```

The first command is split into the literal `export` followed by the variable
assignment — SentinelX reads `SENTINELX_LOG_PATH` from the **environment** of
the shell that launches `run.py`. `manage.sh` does not have an `export`
subcommand, so set the variable in your own shell:

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run
```

---

## 1. How the log path is resolved

`run.py → resolve_active_log_path()` picks the file to tail in this order:

| Priority | Source | Code reference |
|---|---|---|
| 1 (highest) | `SENTINELX_LOG_PATH` environment variable | `os.environ.get("SENTINELX_LOG_PATH")` |
| 2 | The first path in `config.yaml → log_paths` that exists on disk | `os.path.exists(path)` |
| 3 (fallback) | `core/tests/fixtures/auth_small.log` | hard-coded constant |

This means the **demo flow always works** even on a clean checkout, because
the fixture is bundled in the repo and is the last-resort fallback.

---

## 2. Quick start — mock fixtures (no root required)

This is the recommended way to learn the system.

### Step 1 — start the daemon on the fixture

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run
```

Output:

```text
2026-07-12 22:21:25,853 [INFO] sentinelx.runtime: Initializing SentinelX Operational System Fabric...
2026-07-12 22:21:25,853 [INFO] sentinelx.runtime: Background daemon tracking target log vector: core/tests/fixtures/auth_small.log
2026-07-12 22:21:25,853 [INFO] core.watcher: Opened and started watching core/tests/fixtures/auth_small.log from the end (Inode: 660198)
 * Running on http://127.0.0.1:5000
```

### Step 2 — feed mock traffic in a second terminal

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh mock-logs
```

`generate_mock_logs.py` truncates the target file on startup and then
appends randomised `Failed password`, `Invalid user`, and `Accepted
password` lines every 0.5–1.5 seconds. The watcher detects the truncation,
seeks to the start of the new content, and the alert engine begins
dispatching events.

In the first terminal you will see lines like:

```text
[INFO] core.watcher: Log truncation detected for core/tests/fixtures/auth_small.log. Seeking to start...
[WARNING] sentinelx.runtime: SECURITY ESCALATION: [INFO] Failed login attempt
[WARNING] sentinelx.runtime: SECURITY ESCALATION: [INFO] Failed login attempt
[WARNING] sentinelx.runtime: SECURITY ESCALATION: [INFO] Failed login attempt
```

### Step 3 — read the live dashboard

Open <http://127.0.0.1:5000> in a browser. The dashboard subscribes to the
`security_alert` SocketIO event and updates as alerts are dispatched.

### Step 4 — query the API

```bash
curl http://127.0.0.1:5000/api/v1/health
# {"daemon_alive":true,"status":"healthy","timestamp":1783875089.44}

curl http://127.0.0.1:5000/api/v1/stats
# {"alerts_dispatched":3,"lines_parsed":5,"status":"active",
#  "target_file":"core/tests/fixtures/auth_small.log","warnings_raised":0}
```

### Step 5 — shut down

Press `Ctrl+C` in the daemon terminal. `run.py` catches `KeyboardInterrupt`,
sets the shutdown event, and exits cleanly.

---

## 3. Real-world usage — tailing system logs

To monitor actual `sshd` traffic, you need read access to the OS log file.

```bash
# Either run as a user who can read /var/log/auth.log ...
./manage.sh run

# ... or run with sudo and let SentinelX drop privileges after opening the file.
sudo SENTINELX_LOG_PATH=/var/log/auth.log ./manage.sh run
```

The daemon will:

1. Open the log file (requires the read permission granted above).
2. Drop from `root` to the user/group named in `config.yaml` (defaults:
   `nobody` / `nogroup`).
3. Serve the dashboard on `http://127.0.0.1:5000`.

If you prefer a non-default unprivileged user, override it via
`config.yaml` or the `SENTINELX_RUN_AS_USER` / `SENTINELX_RUN_AS_GROUP`
environment variables (see [docs/configuration.md](configuration.md)).

---

## 4. Reading the outputs

### Console logs

`run.py` configures a single `logging` handler to `sys.stdout`. The
prefixed level tags (`[INFO]`, `[WARNING]`, `[CRITICAL]`) are the alert
severity, not the log level. A real alert from the engine looks like:

```text
[WARNING] sentinelx.runtime: SECURITY ESCALATION: [WARNING] Repeated failures — 3 attempts
```

The bracketed tag inside the message is the AlertEngine severity:

| Severity | Default threshold | Meaning |
|---|---|---|
| `INFO` | 1 failure | First failed attempt from this IP |
| `WARNING` | 3 failures | Repeated attempts, watch list |
| `CRITICAL` | 5 failures | Brute force, escalate |

### WebSocket events

The SocketIO server emits a `security_alert` event for every alert the engine
emits. Payload shape (also the `alert_payload` returned by
`AlertEngine.process_event`):

```json
{
  "severity":  "WARNING",
  "ip":        "185.190.140.5",
  "username":  "git",
  "timestamp": "Jul 12 22:21:42",
  "message":   "Repeated failures — 3 attempts"
}
```

### State file

The engine writes `sentinelx_state.json` (or the path configured via
`SENTINELX_STATE_FILE`) atomically using a `*.tmp` + `os.replace` pair:

```json
{
  "fail_info": {
    "185.190.140.5": {"count": 3, "first_seen": 1783875101.4}
  },
  "last_alert":     {"185.190.140.5": 1783875101.4},
  "last_severity":  {"185.190.140.5": "WARNING"}
}
```

Delete the file to reset all counters:

```bash
rm sentinelx_state.json
```

---

## 5. Running the test suite

```bash
./manage.sh test
```

Pytest discovers 16 tests across `core/tests/unit`, `core/tests/integration`,
and `core/tests/stress`. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the
test layout conventions.

---

## 6. Management helper summary

`manage.sh` is a thin wrapper that always invokes `venv/bin/python` so you
do not need to activate the virtual environment by hand:

| Command | Effect |
|---|---|
| `./manage.sh run` | Starts the daemon and Flask web server (`run.py`) |
| `./manage.sh test` | Runs the full pytest suite |
| `./manage.sh mock-logs` | Starts the mock sshd traffic generator |
| `./manage.sh lint` | Byte-compiles all source files to verify syntax |
| `./manage.sh clean` | Removes `.pytest_cache`, `__pycache__`, and state files |
