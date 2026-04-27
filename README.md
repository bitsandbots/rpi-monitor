# RPi**Monitor** v2.2.0

A lightweight, self-hosted Raspberry Pi system monitor and service control console written in Python. Single-file Flask backend, zero JavaScript dependencies, no build step.

Built for [CoreConduit Consulting Services](https://coreconduit.com) infrastructure.

## Features

### Monitoring
- **CPU** — differential usage sampling (accurate real-time %), per-core stats, load averages, current frequency
- **Temperature** — live reading with 60-second sparkline history
- **Memory** — RAM, cached, buffers, swap, GPU memory (Pi-specific via `vcgencmd`)
- **Storage** — all mounted filesystems with capacity bars
- **Network** — interface enumeration, throughput rates (bytes/sec delta tracking), RX/TX sparklines
- **Processes** — top processes by CPU with kill capability
- **Ports** — open ports (0-9999) merged with services view

### Service Control
- View systemd service status (active/enabled state)
- Start, stop, restart services
- Enable/disable services at boot
- Configurable service whitelist (rejects unlisted services)

### System Control
- Reboot and shutdown with confirmation dialog
- Hardware detection at boot (model, SoC, revision, architecture)
- Event log (in-memory ring buffer, viewable in Logs tab)
- Connection-lost detection with automatic reconnect indicator

### Hardware Health (v2.2.0)
- **Temperature Alerts** — Automatic warnings at 70°C (warning), 80°C (critical), 85°C (throttling)
- **Low Voltage Warning** — Detects under-voltage events and current voltage issues via `vcgencmd get_throttled`
- **Service Failure Detection** — Monitors critical services and reports failures
- **System Stability Checks** — Detects OOM events, kernel errors, and service restart loops

### UI
- Boot animation sequence showing detected hardware
- CoreConduit v2.1 branding (Exo 2 / Plus Jakarta Sans / IBM Plex Mono)
- 7-tab dashboard: Overview, Services, Processes, Network, Storage, System, Logs
- Responsive layout (desktop and mobile)
- Toast notifications for all actions
- Single HTML file — no build tools required

## Quick Start

### One-command install (recommended)

```bash
git clone https://github.com/coreconduit/rpi-monitor
cd rpi-monitor
sudo ./install.sh           # node agent only
sudo ./install.sh --hub     # node agent + hub
sudo ./install.sh --hub-only  # hub only
```

Access at `http://<pi-ip>:8585` (node) or `http://<pi-ip>:8686` (hub).

### Manual install

```bash
# Install dependency
pip install flask --break-system-packages

# Run directly
python3 rpi_monitor.py
```

### Install as Service (manual)

```bash
sudo cp rpi-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-monitor
```

Check status:
```bash
sudo systemctl status rpi-monitor
journalctl -u rpi-monitor -f
```

### Uninstall

```bash
sudo ./install.sh --uninstall
```

## v2.2.0 — Release Notes

**New Features:**
- **Hardware Health Alerts** — Real-time monitoring with automatic alert cards on Overview tab
  - Temperature alerts at 70°C (warning), 80°C (critical), 85°C (throttling)
  - Low voltage warning via `vcgencmd get_throttled` (undervoltage, frequency capping)
  - Critical service failure detection (systemd-journald, dbus, cron)
  - System stability checks (OOM, kernel errors, restart loops)

**New API Endpoints:**
- `GET /api/system-health` — System health status with critical services and stability checks
- `GET /api/status` — Enhanced with `temperature_status` and `power_status` objects

**Improvements:**
- Alert cards auto-clear when conditions normalize
- Temperature thresholds configurable in source (TEMP_WARNING=70, TEMP_CRITICAL=80, TEMP_THROTTLE=85)
- Power status parses vcgencmd bit fields for current and historical events

**Documentation:**
- New `docs/alerts.md` — Complete hardware alerts guide
- Updated `wiki/API-Reference.md` — New endpoint documentation

### v2.1.0 (previous)

- Services + Ports merged view
- System errors in Logs tab
- Self-hosted fonts for offline capability

**What's unchanged:**
- All existing API endpoints remain compatible
- Installation and upgrade process unchanged
- Configuration options unchanged

## Configuration

All configuration is via environment variables — no config files to manage.

| Variable | Default | Description |
|---|---|---|
| `PIMONITOR_HOST` | `0.0.0.0` | Bind address |
| `PIMONITOR_PORT` | `8585` | Port |
| `PIMONITOR_DEBUG` | `false` | Flask debug mode |
| `PIMONITOR_TOKEN` | *(empty)* | Optional Bearer token for API auth |
| `PIMONITOR_SERVICES` | `ssh,nginx,docker,...` | Comma-separated service whitelist |
| `PIMONITOR_REFRESH` | `2` | Frontend polling interval (seconds) |

### Configuring Services

Option 1 — environment variable:
```bash
export PIMONITOR_SERVICES="ssh,nginx,docker,ollama,mosquitto"
```

Option 2 — edit `CONFIG["services"]` in `rpi_monitor.py` directly.

### Authentication

Set `PIMONITOR_TOKEN` to require Bearer token auth on all API endpoints:

```bash
export PIMONITOR_TOKEN=my-secret-token
```

The web UI currently does not send auth headers — token auth is designed for API-only access. For UI auth, place RPiMonitor behind a reverse proxy with basic auth.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/ping` | GET | Health check (connection-lost detection) |
| `/api/boot` | GET | Static hardware detection info |
| `/api/status` | GET | CPU, temp, memory, uptime, network rates |
| `/api/storage` | GET | Mounted filesystems |
| `/api/network` | GET | Interfaces, MAC, IP, throughput rates |
| `/api/processes` | GET | Top processes (`?limit=N`, max 50) |
| `/api/processes/<pid>` | DELETE | Kill process (`?signal=15` or `?signal=9`) |
| `/api/services` | GET | Systemd service statuses |
| `/api/services-with-ports` | GET | Services merged with open ports |
| `/api/services/<name>/<action>` | POST | Control service (start/stop/restart/enable/disable) |
| `/api/ports` | GET | Open TCP/UDP ports (0-9999) |
| `/api/system-errors` | GET | Recent journalctl error entries |
| `/api/power/<action>` | POST | Reboot or shutdown |
| `/api/logs` | GET | Event log (`?limit=N`, `?system=true`) |

## Sudoers (optional, for non-root)

If running as a non-root user, add scoped sudoers rules:

```bash
# /etc/sudoers.d/rpi-monitor
# Restrict to specific services rather than wildcards
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ssh nginx docker ollama mosquitto
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ssh nginx docker ollama mosquitto
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ssh nginx docker ollama mosquitto
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable ssh nginx docker ollama mosquitto
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable ssh nginx docker ollama mosquitto
pimonitor ALL=(ALL) NOPASSWD: /sbin/reboot
pimonitor ALL=(ALL) NOPASSWD: /sbin/shutdown
```

**Important:** List each service explicitly rather than using wildcards to prevent privilege escalation.

## Architecture

```
rpi-monitor/
├── rpi_monitor.py          # Flask backend — all data collection + API + boot detection
├── templates/
│   └── index.html         # Self-contained frontend (HTML + CSS + JS, no build step)
├── rpi-monitor.service     # Systemd unit file
├── requirements.txt       # Flask only
└── README.md
```

### Key Design Decisions

- **Differential CPU sampling** — reads `/proc/stat` on each poll and computes usage from the delta since the previous read, giving accurate instantaneous CPU percentage
- **Network rate tracking** — stores previous byte counts per interface with timestamps; computes bytes/sec from the delta rather than showing cumulative totals
- **Service whitelist** — `control_service()` rejects any service name not in `CONFIG["services"]` before invoking systemctl
- **In-memory event log** — ring buffer (200 entries) captures service actions, kills, power events; no disk I/O
- **Single dependency** — Flask only; reads system data from `/proc` and `/sys` directly, no psutil required
- **Boot detection** — hardware identification runs once at startup and caches the result; Pi model, SoC, and revision are parsed from `/proc/cpuinfo` and `/proc/device-tree/model`

## Requirements

- Python 3.11+
- Flask 3.0+
- Raspberry Pi OS / Debian / Ubuntu (any Linux with `/proc` and `systemd`)
- `sudo` access for service control and power management

## License

MIT — CoreConduit Consulting Services
