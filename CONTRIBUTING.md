# Contributing to SentinelX

Thanks for your interest in contributing. This guide covers the
contribution workflow, coding standards, and the test layout used in
this repository.

---

## 1. Development environment

```bash
git clone https://github.com/GGdulmina/sentinelx.git
cd sentinelx

uv venv
uv sync
```

The `manage.sh` script uses `uv run` under the hood, so you do not need
to activate the virtual environment. For example:

```bash
uv run ./manage.sh test
```

---

## 2. Branch model

SentinelX uses a three-branch workflow:

- `main`: Staging branch. Receives merges from `testing` only after
  validation.
- `testing`: Validation branch. Receives merges from `develop` for
  integration/regression/stress testing.
- `develop`: Integration branch for new work. Contributors open PRs
  here.

### Promotion flow

```text
feature work -> PR into develop -> PR develop into testing -> PR testing into main
```

### Contributor workflow

1. **Fork** the repository.
2. **Create a feature branch** from `develop`:
   ```bash
   git checkout -b feature/my-new-feature develop
   ```
3. **Write code + tests** — see [§3 Coding standards](#3-coding-standards)
   and [§4 Test layout](#4-test-layout) below.
4. **Verify locally** before pushing:
   ```bash
   uv run ./manage.sh lint    # syntax check across run.py, config.py, core/*.py
   uv run ./manage.sh test    # full pytest suite
   ```
5. **Open a pull request** against `develop`. Describe the problem, the
   solution, and how you validated it. Reference any related issue.
6. After your PR is merged into `develop`, maintainers will:
   - Create a PR from `develop` into `testing`.
   - After testing passes, create a PR from `testing` into `main`.

---

## 3. Coding standards

- **PEP 8.** Standard Python style. Four-space indent, snake_case,
  type hints on public function signatures.
- **Imports:** Group standard library, third-party, local imports.
- **Documentation:** Docstrings for all public functions and classes.
- **Changelog:** Add entries to `CHANGELOG.md` for notable changes.

---

## 4. Test layout

Tests live inside the `core/` package:

- `core/tests/unit/` — Unit tests for individual functions and classes.
- `core/tests/integration/` — Integration tests that exercise multiple
  components.
- `core/tests/stress/` — Stress tests for performance and longevity
  (run only if explicitly requested).

Run the test suite with:

```bash
uv run ./manage.sh test
```

---

## 5. Conventions

- **Conventional Commits**: Use `feat:`, `fix:`, `chore:`, etc.
- **Never commit directly to `main` or `testing`**.
- **Keep dependencies in `pyproject.toml` and `uv.lock`**.

---

### Related documentation

- [Installation guide](docs/installation.md) - For setting up the development environment
- [Usage guide](docs/usage.md) - For understanding how SentinelX works
- [Configuration reference](docs/configuration.md) - For detailed configuration options
- [Architecture overview](docs/architecture.md) - For understanding the system design
- [Troubleshooting guide](docs/troubleshooting.md) - For common issues and solutions

