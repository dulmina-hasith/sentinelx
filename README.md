# SentinelX

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Stage](https://img.shields.io/badge/status-production__ready-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-16%20passed-brightgreen.svg)

SentinelX is a lightweight, real-time **Security Information & Event Management
(SIEM)** daemon for Linux authentication logs. It tails `sshd` log streams,
parses authentication events with anchored (ReDoS-safe) regular expressions,
tracks per-IP failure counts, escalates alerts as failure thresholds are
crossed, persists state atomically, and ships every alert to a live web
dashboard over WebSocket.

The runtime is built on Flask + Flask-SocketIO (eventlet) and is safe to run
without root: the watcher reads whatever file path is given to it, including
the bundled test fixture used in development.

---

## Quick Start

The fastest way to see SentinelX working is to point it at the bundled
fixture file with the `SENTINELX_LOG_PATH` environment variable, then open the
dashboard in a browser.

### 1. Clone, install, and verify

```bash
git clone https://github.com/dulmina-hasith/sentinelx.git
cd sentinelx

uv venv
uv sync
source .venv/bin/activate

./manage.sh test      # 16/16 unit + integration + stress tests
./manage.sh lint      # syntax check
```

### 2. Run SentinelX against a log file

The runtime looks for a log path in this order:

1. `SENTINELX_LOG_PATH` environment variable (highest priority — **use this for the demo flow**)
2. The first existing path listed in `log_paths` from `config.yaml`
3. Built-in fallback: `core/tests/fixtures/auth_small.log`

```bash
export SENTINELX_LOG_PATH="core/tests/fixtures/auth_small.log"
./manage.sh run
```