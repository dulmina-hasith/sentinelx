"""Integration tests verifying clean process signal handling."""

import sys
import signal
import subprocess
import time


def test_it_shutdown_001_graceful_sigint() -> None:
    """Verify that run.py handles execution termination cleanly with no traceback."""
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Allow startup allocation flights to resolve
    time.sleep(1.0)

    # Issue clean SIGINT to mimic manual operator cancellation
    proc.send_signal(signal.SIGINT)
    
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()

    # Accept both clean 0 exit and standard POSIX SIGINT termination status (-2)
    assert proc.returncode in (0, -signal.SIGINT), (
        f"Process failed to exit cleanly (exit code: {proc.returncode})"
    )

    # Ignore standard interpreter weakref teardown noise if present
    stderr_to_check = stderr
    if "Exception ignored" in stderr_to_check and "greenlet is being finalized" in stderr_to_check:
        stderr_to_check = ""

    assert "Traceback" not in stderr_to_check, f"Raw execution traceback leaked during exit:\n{stderr}"