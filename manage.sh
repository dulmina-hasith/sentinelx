#!/usr/bin/env bash

# SentinelX Production Management Orchestrator Helper Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function print_help() {
    echo "SentinelX Management Helper Utilities"
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  run        - Boot SentinelX system daemon and api layers"
    echo "  test       - Execute complete pytest validation suite matrices"
    echo "  mock-logs  - Run background log injection attacker cycles"
    echo "  lint       - Run fast structural syntax verification tracks"
    echo "  clean      - Flush out state dumps, temp runtime traces, and caches"
}

case "$1" in
    run)
        uv run python "$DIR/run.py" "${@:2}"
        ;;
    test)
        PYTHONPATH="$DIR" uv run pytest "$DIR/core/tests/" "${@:2}"
        ;;
    mock-logs)
        uv run python "$DIR/generate_mock_logs.py" "${@:2}"
        ;;
    lint)
        uv run python -m py_compile "$DIR/run.py" "$DIR/core/"*.py "$DIR/core/tests/"**/*.py
        echo "Syntax validation pass successful."
        ;;
    clean)
        rm -rf "$DIR/.pytest_cache"
        rm -rf "$DIR/"**/__pycache__
        rm -f "$DIR/sentinelx_state.json" "$DIR/sentinelx_state.json.tmp"
        echo "Pruning phase finished cleanly."
        ;;
    help|*)
        print_help
        ;;
esac