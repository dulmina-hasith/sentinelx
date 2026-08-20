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
source .venv/bin/activate
```

`manage.sh` already wraps `.venv/bin/python` and `.venv/bin/pytest`, so
you do not need to keep the venv activated for the commands below.

---

## 2. Contribution workflow

1. **Fork** the repository.
2. **Create a feature branch** with a descriptive name:
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **Write code + tests** — see [§3 Coding standards](#3-coding-standards)
   and [§4 Test layout](#4-test-layout) below.

4. **Verify locally** before pushing:
   ```bash
   ./manage.sh lint    # syntax check across run.py, config.py, core/*.py
   ./manage.sh test    # full pytest suite — must be 16/16 green
   ```

5. **Open a pull request** against `main`. Describe the problem, the
   solution, and how you validated it. Reference any related issue.

---

## 3. Coding standards

- **PEP 8.** Standard Python style. Four-space indent, snake_case,
  type hints on public function signatures.