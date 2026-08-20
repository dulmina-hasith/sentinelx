.PHONY: test run mock-logs lint clean help

help:
	@echo "SentinelX Makefile Commands:"
	@echo "  make run        - Run SentinelX with default configurations"
	@echo "  make test       - Run all unit and integration tests"
	@echo "  make mock-logs  - Run the mock log generator to simulate auth traffic"
	@echo "  make lint       - Run syntax verification on code files"
	@echo "  make clean      - Clean up temporary files, state, caches, and .pyc files"

run:
	./.venv/bin/python run.py

test:
	PYTHONPATH=. ./.venv/bin/pytest

mock-logs:
	./.venv/bin/python generate_mock_logs.py

lint:
	./.venv/bin/python -m py_compile run.py config.py core/*.py tests/*.py
	@echo "Syntax verification pass successful."

clean:
	rm -rf .pytest_cache
	rm -rf __pycache__ core/__pycache__ tests/__pycache__
	rm -f sentinelx_state.json sentinelx_state.json.tmp
	rm -f mock_auth.log
	@echo "Clean completed."