# SentinelX Configuration Guide

SentinelX is configured by three layers, applied in this order (later
layers override earlier ones):

1. **Defaults** baked into [`config.py`](../config.py)
2. **`config.yaml`** at the project root, deep-merged over the defaults
3. **`SENTINELX_*` environment variables**, applied last

`SENTINELX_LOG_PATH` is a special case — it is not part of the layered
config and is read directly by `run.py:resolve_active_log_path`. See
[§3](#3-sentinelx_log_path-the-demo-flow-shortcut) below.

The full default configuration is also exported as
[`config.yaml.example`](../config.yaml.example) so you can copy it and edit
in place:

```bash
cp config.yaml.example config.yaml
```

---

## 1. `config.yaml` schema

| Key | Type | Default | Description |
|---|---|---|---|
| `log_paths` | list[string] | `['/var/log/auth.log', '/var/log/secure']` | Candidate log files. The first one that exists on disk is used (unless `SENTINELX_LOG_PATH` is set). |
| `thresholds.info` | int | `1` | Failed attempts before an `INFO` alert. |
| `thresholds.warning` | int | `3` | Failed attempts before a `WARNING` alert. |
| `thresholds.critical` | int | `5` | Failed attempts before a `CRITICAL` alert. |
| `reset_after` | int (seconds) | `86400` (24h) | Inactivity window after which an IP's failure count is reset. |
| `alert_cooldown` | int (seconds) | `300` (5m) | Minimum gap between alerts for the same IP at the **same** severity. Severity escalation bypasses cooldown. |
| `state_file` | string \| null | `"sentinelx_state.json"` | JSON file used to persist counters. Set to `null` to disable persistence. |
| `run_as_user` | string | `"nobody"` | Target UID for `drop_privileges` when started as root. |
| `run_as_group` | string | `"nogroup"` | Target GID for `drop_privileges` when started as root. |
| `output_format.icons` | dict | see below | Display icon per severity. |
| `output_format.column_widths` | dict | `{ip: 16, username: 12}` | Reserved for CLI alignment (the current runtime logs to `logging`, but the format block is loaded for forward compatibility). |
| `output_format.date_format` | string | `""` | Reserved `strftime` override. Empty keeps the original log timestamp. |

`validate_config` in `config.py` enforces that the three threshold levels
are positive integers and that `info <= warning <= critical`. Bad values
raise `ValueError` at startup.

### Default `output_format.icons`

```yaml
output_format:
  icons:
    info:    "[  INFO  ]"
    warning: "[WARNING ]"
    critical: "[CRITICAL]"
```

---

## 2. Environment variables

All keys in `config.yaml` (except `output_format`) can be overridden by
environment variables. Names are upper-snake-case, prefixed with
`SENTINELX_`.

| Variable | Overrides | Example |
|---|---|---|
| `SENTINELX_LOG_PATHS` | `log_paths` (comma-separated) | `SENTINELX_LOG_PATHS="/var/log/auth.log,/tmp/test.log"` |
| `SENTINELX_THRESHOLDS_INFO` | `thresholds.info` | `3` |
| `SENTINELX_THRESHOLDS_WARNING` | `thresholds.warning` | `5` |
| `SENTINELX_THRESHOLDS_CRITICAL` | `thresholds.critical` | `10` |
| `SENTINELX_RESET_AFTER` | `reset_after` | `3600` |
| `SENTINELX_ALERT_COOLDOWN` | `alert_cooldown` | `60` |
| `SENTINELX_STATE_FILE` | `state_file` | `/var/lib/sentinelx/state.json` |
| `SENTINELX_RUN_AS_USER` | `run_as_user` | `sentinelx` |
| `SENTINELX_RUN_AS_GROUP` | `run_as_group` | `sentinelx` |

`SECRET_KEY` is also read by `run.py` to set Flask's `SECRET_KEY`
(`os.environ.get('SECRET_KEY', 'sentinelx-core-secure-key')`).

---

## 3. `SENTINELX_LOG_PATH` — the demo-flow shortcut

The `SENTINELX_LOG_PATH` variable is **not** part of `config.py`. It is
read by `run.py` and is the recommended way to point the daemon at a
specific file for both development and the bundled demo flow:

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run
```

The resolution order in `run.py:resolve_active_log_path` is:

1. `SENTINELX_LOG_PATH` (if set and non-empty) — **always wins**
2. The first path in `config.yaml → log_paths` that exists on disk
3. Hard-coded fallback: `core/tests/fixtures/auth_small.log` (always
   present in the repo, so the demo flow works on a clean checkout with
   no privileges)

Because the env var short-circuits the layered config, you can leave
`config.yaml` pointing at production paths (`/var/log/auth.log`) and
still demo the system against the fixture simply by exporting the env
var in the shell that runs `run.py`.

The same variable is read by `generate_mock_logs.py`, so the mock
generator and the daemon can be pointed at the same file independently
of `config.yaml`:

```bash
# Terminal 1 — daemon
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run

# Terminal 2 — traffic
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh mock-logs
```

---

## 4. Full worked example

`config.yaml`:

```yaml
log_paths:
  - /var/log/auth.log
  - /var/log/secure

thresholds:
  info: 1
  warning: 3
  critical: 5

reset_after: 86400
alert_cooldown: 300
state_file: sentinelx_state.json

run_as_user: nobody
run_as_group: nogroup
```

Override a few values from the shell:

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
export SENTINELX_THRESHOLDS_WARNING=2
export SENTINELX_THRESHOLDS_CRITICAL=4
export SENTINELX_RUN_AS_USER=sentinelx
./manage.sh run
```

Effective configuration after merging:

| Key | Value | Source |
|---|---|---|
| `log_paths` | `['/var/log/auth.log', '/var/log/secure']` | `config.yaml` |
| `thresholds.info` | `1` | default |
| `thresholds.warning` | `2` | **env** |
| `thresholds.critical` | `4` | **env** |
| `reset_after` | `86400` | default |
| `alert_cooldown` | `300` | default |
| `state_file` | `sentinelx_state.json` | default |
| `run_as_user` | `sentinelx` | **env** |
| `run_as_group` | `nogroup` | default |
| (effective log path) | `core/tests/fixtures/auth_small.log` | **env** (`SENTINELX_LOG_PATH`) |

---

## 5. Validating configuration

`load_config` calls `validate_config` after merging, so the daemon refuses
to start with bad input. To validate without starting the server:

```bash
PYTHONPATH=. venv/bin/python -c "from config import load_config; import json; print(json.dumps(load_config(), indent=2))"
```

Common validation errors:

- `info <= warning <= critical` violated
- A threshold is not a positive integer
- `log_paths` is not a list of strings
- `reset_after` or `alert_cooldown` is negative
