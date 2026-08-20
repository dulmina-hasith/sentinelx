# SentinelX Installation Guide

This document walks through installing SentinelX on a Linux host and getting
the daemon + dashboard running.

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| OS | Linux (tested on Fedora, RHEL, CentOS, Debian, Ubuntu) |
| Python | 3.10 or higher (the dev environment used 3.14.7) |
| uv | UV package manager (https://github.com/astral-sh/uv) |
| Network | Outbound HTTPS for `uv sync` (no runtime network dependency) |
| Log read access | Required only when tailing **real** auth logs (`/var/log/auth.log`, `/var/log/secure`); not required for the mock-fixture demo |

The runtime stack is **Flask 3 + Flask-SocketIO 5 + eventlet 0.41 + greenlet
3**, plus `PyYAML` and `pytest`. `uv lock` provides exact versions.

---

## 2. Clone the repository

```bash
git clone https://github.com/GGdulmina/sentinelx.git
cd sentinelx
```

A typical install location is `/opt/sentinelx` on production hosts, but
running out of a user home directory works equally well for the mock-flow
demo.

---

## 3. Create virtual environment and install dependencies

`manage.sh` and `Makefile` both look for `.venv/bin/python` and
`.venv/bin/pytest`, so the virtual environment must live at
`./.venv/` inside the project root.

```bash
uv venv
uv sync
source .venv/bin/activate
```

Verify the install:

```bash
./manage.sh test      # 16/16 unit + integration + stress tests
./manage.sh lint      # syntax check
```

---

## 4. Smoke test with the bundled fixture

This is the recommended first run. It needs **no** privileges because the
fixture lives in the repository and the daemon never touches `/var/log`.

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run
```

You should see the daemon start, the watcher log the open, and Flask begin
serving on `http://127.0.0.1:5000`. Visit that URL for the dashboard or
`curl http://127.0.0.1:5000/api/v1/health` for the JSON API.

To feed traffic, run the mock generator in a second terminal with the
**same** env var:

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh mock-logs
```

See [docs/usage.md](usage.md) for the full walkthrough.

---

## 5. Permissions for real auth logs

`/var/log/auth.log` (Debian/Ubuntu) and `/var/log/secure` (RHEL-family) are
owned by `root:adm` and mode `0640`. SentinelX has two ways to read them:

### Option A — start as root, drop privileges

The runtime in `core/privileges.py:drop_privileges` opens the log file as
root and then transitions to a low-privilege user. Defaults are
`nobody` / `nogroup`; override via `SENTINELX_RUN_AS_USER` and
`SENTINELX_RUN_AS_GROUP` (or `config.yaml`).

```bash
sudo SENTINELX_LOG_PATH=/var/log/auth.log ./manage.sh run
```

**Important:** the *target* unprivileged user must still be able to read
the log file after rotation, otherwise the watcher cannot reopen the new
file. Add it to the `adm` group (Debian/Ubuntu) or run it as a user with
explicit ACLs on the log.

### Option B — run as a dedicated user

```bash
sudo useradd -r -s /usr/sbin/nologin sentinelx
sudo usermod -aG adm sentinelx
sudo chown -R sentinelx:sentinelx /opt/sentinelx

sudo -u sentinelx SENTINELX_LOG_PATH=/var/log/auth.log ./manage.sh run
```

---

## 6. systemd service (production)

A minimal unit file that runs SentinelX as root, lets it open the log, and
then drops privileges:

```ini
# /etc/systemd/system/sentinelx.service
[Unit]
Description=SentinelX Authentication Log Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sentinelx
Environment=SENTINELX_LOG_PATH=/var/log/auth.log
ExecStart=/opt/sentinelx/.venv/bin/python /opt/sentinelx/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sentinelx.service
sudo systemctl status sentinelx.service
```

The dashboard is bound to `127.0.0.1:5000` by default, so it is only
reachable from the host. Front it with a reverse proxy (nginx, Caddy) if
you need remote access — and add authentication at the proxy layer, since
the dashboard currently exposes no auth.

---

## 7. Upgrading

```bash
cd /opt/sentinelx
git pull
uv sync
source .venv/bin/activate
./manage.sh test
sudo systemctl restart sentinelx.service
```

The atomic-write state file format has been stable since the 0.x line, so
existing `sentinelx_state.json` files survive upgrades in place.