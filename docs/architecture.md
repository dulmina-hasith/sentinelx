# SentinelX Architecture

This document describes the runtime architecture of SentinelX as it
actually exists in the codebase — the daemon, the Flask-SocketIO web
server, the watcher, the parser, the alert engine, and the persistence
layer — and how a single log line flows from file to dashboard.

---

## 1. High-level component view

```mermaid
graph TD
    A[Log File<br/>resolved by SENTINELX_LOG_PATH] -->|follow() generator| B(core.watcher)
    B -->|raw line| C{Background Daemon Thread}
    C -->|parse_line| D(core.parser)
    D -->|structured dict| E(AlertEngine)
    E <-->|load_state / save_state| F(sentinelx_state.json)
    E -->|alert_payload| G(run.py runtime)
    G -->|logger.warning| H[Console stdout]
    G -->|socketio.emit 'security_alert'| I[WebSocket]
    I --> J[templates/index.html<br/>Live dashboard]
    K[GET /api/v1/health<br/>GET /api/v1/stats] -->|jsonify| G
```

### Components

| File | Role |
|---|---|
| `run.py` | Entry point. Loads config, resolves the log path, starts the SocketIO background task that owns the daemon loop, and serves the dashboard + JSON API. |
| `core/watcher.py` | `follow(log_path)` generator that opens the log file, yields new lines, and detects rotation (inode change) and truncation (size shrink) without blocking. |
| `core/parser.py` | `parse_line(line)` matches anchored, ReDoS-safe sshd patterns and `sanitize_input` strips ANSI / non-printable bytes from extracted strings. |
| `core/alerts.py` | `AlertEngine` tracks per-IP failure counts, escalates severity at thresholds, respects alert cooldown, and persists state. |
| `core/privileges.py` | `drop_privileges()` — when the process is running as `root`, transitions to the configured unprivileged user/group before the HTTP server starts serving. |
| `config.py` | `load_config()` merges defaults ← `config.yaml` ← environment variables, then validates the result. |
| `templates/index.html` | Static dashboard that subscribes to the `security_alert` SocketIO event and renders alerts and stats. |
| `sentinelx_state.json` | Atomic JSON store for `fail_info`, `last_alert`, `last_severity`. |

---

## 2. End-to-end data flow

1. **Path resolution (`run.py:resolve_active_log_path`)**

   ```text
   SENTINELX_LOG_PATH (env)
       └─ not set? → first existing path in cfg['log_paths']
           └─ none exist? → "core/tests/fixtures/auth_small.log"   # always-present fallback
   ```

2. **Watcher (`core/watcher.py:follow`)**

   - Opens the file, captures the inode via `os.fstat(f.fileno()).st_ino`.
   - On the **first** open of a process, seeks to the end of the file
     (only lines appended *after* startup are processed).
   - On **re-open** (after rotation), seeks to the start so historical lines
     are not silently dropped.
   - When the read returns nothing, the generator compares the current
     `os.stat(log_path).st_ino` to the descriptor's inode. If they differ,
     it re-opens (rotation). If `os.fstat(fd).st_size < f.tell()`, it
     `seek(0)`s (truncation).
   - Yields `line.strip()` to the caller.

3. **Daemon loop (`run.py:background_daemon_worker`)**

   - Started by `socketio.start_background_task(...)` so it shares the
     eventlet hub with the HTTP server.
   - For each line, increments `SYSTEM_STATS["lines_parsed"]`, calls
     `parse_line`, and passes the structured dict to
     `engine.process_event(...)`.

4. **Parser (`core/parser.py`)**

   - Three compiled patterns: `failed_password`, `invalid_user`,
     `accepted_password`. All anchored at line start and free of greedy
     `.*` to avoid ReDoS.
   - `sanitize_input` is applied to every extracted string field.
   - Returns a dict with `event`, `timestamp`, `username`, `ip`, `port`, `raw`.

5. **Alert engine (`core/alerts.py:AlertEngine.process_event`)**

   - `accepted_password` → emits a one-shot `INFO` alert.
   - `failed_password` / `invalid_user` → increments per-IP `count`.
   - Severity chosen by `count` against `thresholds`:
     - `>= critical` → `CRITICAL` ("Brute force attack detected — N failures")
     - `>= warning`  → `WARNING`  ("Repeated failures — N attempts")
     - else          → `INFO`     ("Failed login attempt")
   - `_should_alert` honours `alert_cooldown` **but bypasses it on
     severity escalation** so a critical event is never throttled away.
   - `save_state` writes the new counters via a `*.tmp` + `os.replace`
     atomic replace.

6. **Output (`run.py`)**

   - The alert payload goes to:
     - `logger.warning("SECURITY ESCALATION: [%s] %s", severity, message)`
       on the runtime logger (stdout).
     - `socketio.emit("security_alert", alert_payload)` over WebSocket
       to every connected dashboard client.
   - `SYSTEM_STATS["alerts_dispatched"]` and
     `SYSTEM_STATS["warnings_raised"]` are bumped for the JSON API.

7. **HTTP surface (`run.py`)**

   | Route | Method | Response |
   |---|---|---|
   | `/` | `GET` | `render_template("index.html")` — the dashboard |
   | `/api/v1/health` | `GET` | `{status, timestamp, daemon_alive}` |
   | `/api/v1/stats` | `GET` | `{status, lines_parsed, warnings_raised, alerts_dispatched, target_file}` |

8. **Privilege drop (`core/privileges.py:drop_privileges`)**

   - Called from `run.py` immediately after `socketio.start_background_task`
     and a 0.5 s warm-up sleep, before `socketio.run(...)`.
   - If `os.getuid() != 0`, this is a no-op.
   - Otherwise, resolves the target UID/GID from the configured
     `run_as_user` / `run_as_group` (with `nobody` / `nogroup` /
     `daemon` fallbacks and an `SUDO_USER` override), then calls
     `os.setgroups([])`, `os.setgid(...)`, `os.setuid(...)`.

---

## 3. Threading model

| Thread | Owner | Lifetime |
|---|---|---|
| Main / eventlet hub | `socketio.run` | Until `Ctrl+C` or `KeyboardInterrupt` |
| `DaemonWorker` background task | `socketio.start_background_task(background_daemon_worker, ...)` | Process lifetime, or until `shutdown_event.is_set()` |

The daemon thread is the only consumer of `follow(...)`; there is no
intermediate queue. The Flask request handlers run on the eventlet hub
alongside the daemon, but they do not share mutable state with the
parser/alert-engine path beyond the `SYSTEM_STATS` dict, which is
written only by the daemon and read only by the API handlers.

---

## 4. Configuration layering

`config.py:load_config()` builds the final configuration in this order
(lowest priority first, later layers override earlier ones):

1. `DEFAULT_CONFIG` (hard-coded in `config.py`)
2. `config.yaml` (deep-merged into the defaults)
3. `SENTINELX_*` environment variables (see
   [docs/configuration.md](configuration.md) for the full list)

After merging, `validate_config` is called to fail fast on bad input
(e.g. `info` > `warning` > `critical` ordering, non-positive thresholds).

The `SENTINELX_LOG_PATH` variable is **not** part of the layered config —
it is consumed directly by `run.py:resolve_active_log_path` and is the
canonical way to point the daemon at a single file for the demo flow.
