# SentinelX Troubleshooting Guide

Common runtime problems and how to fix them.

---

## 1. The daemon starts but no alerts ever appear

### Symptom

```text
Background daemon tracking target log vector: core/tests/fixtures/auth_small.log
Opened and started watching core/tests/fixtures/auth_small.log from the end
```

…and then silence, even though traffic is being written to the file.

### Why this happens

`core/watcher.py:follow()` seeks to the **end of the file on the very
first open** of the process. Anything that was already in the log is
skipped — only lines appended *after* SentinelX starts are processed.

### Fixes

- **Append, do not overwrite.** If you `truncate` the file and then write
  to it, the watcher does see the new content (it detects truncation via
  inode + size). The bundled `generate_mock_logs.py` does exactly this.
- **Restart the daemon** after writing historical content if you need it
  scanned; the daemon reads from the start on its second-and-later opens
  of the same path.
- **Run the mock generator against a different file** than the daemon is
  watching. Verify the env var is set in *both* terminals:

  ```bash
  echo $SENTINELX_LOG_PATH
  ```

  must print the same path in both.

---

## 2. `Permission denied` on the log file

### Symptom

```text
[ERROR] core.watcher: Permissions/Missing file error reading /var/log/auth.log:
[Errno 13] Permission denied: '/var/log/auth.log'. Retrying in 5 seconds...
```

### Why this happens

`/var/log/auth.log` (Debian/Ubuntu) and `/var/log/secure` (RHEL) are
mode `0640`, owned by `root:adm`. The user running `run.py` is not in
the `adm` group and did not start as `root`.

### Fixes

- **Start as root and let SentinelX drop privileges.** The runtime calls
  `core/privileges.py:drop_privileges` after opening the file:

  ```bash
  sudo SENTINELX_LOG_PATH=/var/log/auth.log ./manage.sh run
  ```

  The default target is `nobody` / `nogroup`; override with
  `SENTINELX_RUN_AS_USER` / `SENTINELX_RUN_AS_GROUP`. The unprivileged
  user **must still be able to read the rotated log** — add it to
  `adm` if you rotate via `logrotate` and the file mode resets.

- **Run as a member of `adm`.** Or grant ACL access to the log file:

  ```bash
  sudo setfacl -m u:sentinelx:r /var/log/auth.log
  ```

- **Use the demo flow** while debugging. The bundled fixture
  `core/tests/fixtures/auth_small.log` is readable by everyone:

  ```bash
  export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
  ./manage.sh run
  ```

---

## 3. The dashboard does not load at `http://127.0.0.1:5000`

### Symptom

Browser shows “connection refused” or a long wait, and `curl` to the
endpoint hangs or refuses.

### Why this happens

- A different process is bound to port 5000. The dev server uses
  `socketio.run(app, host="127.0.0.1", port=5000, ...)`.
- SentinelX is still starting up (eventlet takes ~1 s to initialise).
- The daemon is running on a different host than your browser (it binds
  to the **loopback** interface only).

### Fixes

- Check what is listening: `ss -tlnp | grep 5000`
- Wait a second and retry. Logs will show
  `Running on http://127.0.0.1:5000` once the server is ready.
- For remote access, front the daemon with a reverse proxy (nginx /
  Caddy) — SentinelX itself does not bind a public interface.

---

## 4. State file errors after a crash

### Symptom

```text
[ERROR] core.alerts: Error loading system state index: <some JSON decode error>
```

…or simply: failure counts reset to 0 after a restart.

### Why this happens

- The state file path in `state_file` is not writable by the dropped
  privilege user.
- The file was corrupted by a kill -9 that interrupted a write (the
  engine uses atomic `os.replace`, so this should be rare, but a
  pre-existing bad file is still a bad file).
- `state_file` was set to `null` in `config.yaml`, in which case
  counters are in-memory only and **always** reset on restart.

### Fixes

- Make the directory writable by the runtime user:

  ```bash
  sudo chown -R sentinelx:sentinelx /opt/sentinelx
  ```

- Delete a corrupted file. SentinelX will recreate it on the next
  event:

  ```bash
  rm sentinelx_state.json
  ```

  (The atomic write uses a `*.tmp` then `os.replace`, so the file is
  never observed half-written by the next start.)

- Confirm `state_file` is not `null` if you want counters to survive
  restarts.

---

## 5. `validate_config` raises on startup

### Symptom

```text
ValueError: thresholds must satisfy: info <= warning <= critical
```

(or any other validation error from `config.py`).

### Why this happens

`config.py:validate_config` is called after merging defaults, YAML, and
env vars, and refuses to start with bad input. Typical cases:

- `thresholds` reordered, or one level is 0/negative
- `log_paths` is not a list
- `reset_after` or `alert_cooldown` is negative
- A `SENTINELX_THRESHOLDS_*` env var contains a non-integer

### Fixes

- Print the merged config to inspect the effective values:

  ```bash
  PYTHONPATH=. venv/bin/python -c "from config import load_config; import json; print(json.dumps(load_config(), indent=2))"
  ```

- Reorder `thresholds` so `info <= warning <= critical`.
- Unset conflicting `SENTINELX_*` env vars (`env | grep SENTINELX_`).

---

## 6. Mock generator writes to a different file than the daemon watches

### Symptom

`./manage.sh mock-logs` prints dispatched lines, but the daemon logs
nothing and the API stats show `lines_parsed: 0` staying flat.

### Why this happens

`SENTINELX_LOG_PATH` is set in one terminal but not the other (or set
to different values), so the generator and the watcher are pointed at
different files.

### Fixes

- Verify both terminals resolve the same value:

  ```bash
  echo $SENTINELX_LOG_PATH    # in BOTH terminals
  ```

- Re-export in the second terminal if needed:

  ```bash
  export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
  ./manage.sh mock-logs
  ```

- The `mock-logs` command accepts a positional path argument that
  overrides the env var for that run; make sure you are not passing a
  different path.

---

## 7. `eventlet` deprecation warning

### Symptom

```text
EventletDeprecationWarning: Eventlet is deprecated. It is currently being
maintained in bugfix mode, and we strongly recommend against using it for
new projects.
```

### Why this happens

`run.py` calls `eventlet.monkey_patch()` before any other import, and
Flask-SocketIO uses eventlet as its async driver. The warning is
informational and does not affect functionality.

### Fixes

- This is expected for the current dependency set; it can be safely
  ignored at runtime.
- The dashboard and WebSocket events work as designed. If you need a
  no-eventlet path, plan a migration to the threading or asyncio
  SocketIO async modes (tracked separately; no current code change
  needed for development).

---

## 8. Test suite failures

### Symptom

```bash
./manage.sh test
# ... FAILED
```

### Fixes

- Ensure the venv is intact: `pip install -r requirements.txt`.
- Some integration tests spawn a child Python process to validate
  shutdown. If `run.py` is missing, the test is expected to fail —
  re-clone if you have accidentally deleted the file.
- Run a single failing test with verbose output:

  ```bash
  ./manage.sh test -k test_ut_watcher_001 -v
  ```
