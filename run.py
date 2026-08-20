"""SentinelX Management API and Background Daemon orchestrator.

Handles configuration ingestion, dynamic OS log detection, secure root privilege
dropping, and real-time WebSocket event dispatching.
"""

import sys

# CRITICAL FIX: Eventlet requires patching BEFORE any other imports occur
try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    pass

# Now wrap everything else in a try-except to handle KeyboardInterrupt during imports
try:
    import os
    import threading
    import time
    import logging
    from flask import Flask, jsonify, render_template
    from flask_socketio import SocketIO

    # Force absolute path registration to survive sudo environment changes
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    # Check if privileges.py is in root or inside core/
    try:
        from privileges import drop_privileges
    except ModuleNotFoundError:
        from core.privileges import drop_privileges

    from config import load_config
    from core.watcher import follow
    from core.parser import parse_line
    from core.alerts import AlertEngine

    # Setup structured console logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("sentinelx.runtime")

    import signal
    # Register signal handlers - simple immediate exit for clean termination
    def signal_handler(signum, frame):
        logger.info("Termination signal captured. Exiting cleanly...")
        logging.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

except KeyboardInterrupt:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("sentinelx.runtime")
    logger.info("Termination signal captured during initialization. Exiting cleanly...")
    logging.shutdown()
    os._exit(0)

# 1. Ingest layered configuration parameters
cfg = load_config()

# 2. Dynamic OS Log Path Selector
def resolve_active_log_path(configured_paths: list) -> str:
    """Scan the local system to match and bind the first valid host OS log track."""
    env_override = os.environ.get("SENTINELX_LOG_PATH")
    if env_override:
        return env_override

    for path in configured_paths:
        if os.path.exists(path):
            logger.info(f"OS Detection Success: Found active security log file at {path}")
            return path

    fallback_path = "core/tests/fixtures/auth_small.log"
    logger.warning(f"No production system logs found. Falling back to dev sandbox: {fallback_path}")
    return fallback_path

TARGET_LOG_PATH = resolve_active_log_path(cfg['log_paths'])

# Initialize Web Engine Components
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sentinelx-core-secure-key')
socketio = SocketIO(app, cors_allowed_origins="*")

SYSTEM_STATS = {
    "status": "active",
    "lines_parsed": 0,
    "warnings_raised": 0,
    "alerts_dispatched": 0,
    "target_file": TARGET_LOG_PATH
}

shutdown_event = threading.Event()


def background_daemon_worker(log_path: str, state_path: str) -> None:
    """Run real-time authentication monitoring inside an isolated background thread."""
    logger.info(f"Background daemon tracking target log vector: {log_path}")

    engine = AlertEngine(state_path=state_path)

    try:
        for raw_line in follow(log_path):
            if shutdown_event.is_set():
                break

            SYSTEM_STATS["lines_parsed"] += 1
            parsed_data = parse_line(raw_line)
            if not parsed_data:
                continue

            alert_payload = engine.process_event(parsed_data)
            if alert_payload:
                SYSTEM_STATS["alerts_dispatched"] += 1

                severity_level = str(alert_payload.get('severity', '')).strip().lower()

                if severity_level == 'warning':
                    SYSTEM_STATS["warnings_raised"] += 1

                logger.warning(f"SECURITY ESCALATION: [{alert_payload['severity']}] {alert_payload['message']}")
                socketio.emit('security_alert', alert_payload)

    except Exception as e:
        logger.error(f"Uncaught exception inside background execution track: {e}")


# =========================================================================
# Interface Render Layer
# =========================================================================

@app.route("/", methods=["GET"])
def render_dashboard():
    """Serve the real-time security control command dashboard UI."""
    return render_template("index.html")


# =========================================================================
# Management API Routing Layer
# =========================================================================

@app.route("/api/v1/health", methods=["GET"])
def get_health_status():
    """Retrieve runtime operational health indicators."""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "daemon_alive": any(t.name == "DaemonWorker" for t in threading.enumerate())
    }), 200


@app.route("/api/v1/stats", methods=["GET"])
def get_telemetry_metrics():
    """Expose total lines parsed and metric indicators."""
    return jsonify({
        "status": SYSTEM_STATS["status"],
        "lines_parsed": SYSTEM_STATS["lines_parsed"],
        "warnings_raised": SYSTEM_STATS.get("warnings_raised", 0),
        "alerts_dispatched": SYSTEM_STATS["alerts_dispatched"],
        "target_file": SYSTEM_STATS["target_file"]
    }), 200


if __name__ == "__main__":
    logger.info("Initializing SentinelX Operational System Fabric...")

    # Spawn background monitoring thread using socketio background management
    socketio.start_background_task(
        target=background_daemon_worker,
        log_path=TARGET_LOG_PATH,
        state_path=cfg['state_file']
    )

    time.sleep(0.5)

    # Securely Drop Privileges right after starting the background file link
    drop_privileges(username=cfg['run_as_user'], group=cfg['run_as_group'])

    try:
        socketio.run(app, host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Termination signal captured. Executing graceful system shutdown...")
    finally:
        shutdown_event.set()
        logger.info("SentinelX Daemon stopped cleanly.")
        logging.shutdown()
        sys.exit(0)