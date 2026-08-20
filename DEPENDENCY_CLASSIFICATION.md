# Dependency Classification for UV Migration

## Analysis Methodology
Each dependency from requirements.txt was evaluated based on:
1. Direct imports/usage in Python source code (grep analysis)
2. Documentation references (specifically docs/installation.md)
3. Known dependency relationships (what packages require)
4. Exclusion of installer packages (pip)
5. Separation of test dependencies (pytest)

## Classification Results

### Runtime Dependencies (to include in [project.dependencies])
| Package | Version | Reasoning |
|---------|---------|-----------|
| eventlet | 0.41.0 | Direct import in run.py; documented in installation.md |
| Flask | 3.1.3 | Direct import in run.py; documented in installation.md |
| Flask-SocketIO | 5.6.1 | Direct import in run.py; documented in installation.md |
| greenlet | 3.5.3 | Explicitly documented in installation.md as part of runtime stack |
| PyYAML | 6.0.2 | Direct import in config.py; documented in installation.md |
| Werkzeug | 3.1.8 | Core Flask dependency (required for Flask to function) |
| Jinja2 | 3.1.6 | Core Flask dependency (required for templating) |
| MarkupSafe | 3.0.3 | Core Jinja2 dependency (required for Flask templating) |
| itsdangerous | 2.2.0 | Core Flask dependency (required for session handling) |
| blinker | 1.9.0 | Standard Flask dependency (used for signals, commonly needed by Flask apps) |
| python-socketio | 5.16.3 | Direct dependency of Flask-SocketIO |
| python-engineio | 4.13.3 | Direct dependency of python-socketio |

### Development Dependencies (to include in [dependency-groups] dev)
| Package | Version | Reasoning |
|---------|---------|-----------|
| pytest | 9.1.1 | Test framework; moved from runtime per audit findings |
| pluggy | 1.6.0 | pytest dependency (for test plugin system) |
| iniconfig | 2.3.0 | pytest dependency (for configuration handling) |

### Excluded Dependencies
| Package | Version | Reasoning |
|---------|---------|-----------|
| pip | 26.0.1 | Installer tool; should never be listed as project dependency (uv manages its own installer) |
| bidict | 0.23.1 | No references found in codebase or documentation |
| click | 8.4.2 | No references found (Flask CLI not used in this daemon application) |
| dnspython | 2.8.0 | No references found in codebase or documentation |
| h11 | 0.16.0 | No references found in codebase or documentation |
| packaging | 26.2 | No references found in codebase or documentation |
| Pygments | 2.2.0 | No references found in codebase or documentation |
| simple-websocket | 1.1.0 | No references found in codebase or documentation |
| wsproto | 1.3.2 | No references found in codebase or documentation |

## Verification Notes
- All runtime dependencies either:
  - Are directly imported in the codebase (eventlet, Flask, Flask-SocketIO, PyYAML)
  - Are explicitly documented as part of the runtime stack (greenlet in installation.md)
  - Are known core dependencies of the above packages (Werkzeug, Jinja2, etc.)
- Development dependencies are separated to avoid shipping test tools with production installs
- Installer package (pip) is completely excluded as per migration requirements
- Packages with no verifiable usage or documentation support are excluded to minimize dependency surface