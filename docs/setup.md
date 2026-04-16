# RPiMonitor — Setup & Usage

## Prerequisites

- Raspberry Pi (any model) running Raspberry Pi OS 64-bit, or any Debian-based Linux
- Python 3.11+
- `pip3` and `venv`

---

## Node Agent

### 1. Install

```bash
sudo mkdir -p /opt/rpi-monitor
sudo cp rpi_monitor.py requirements.txt /opt/rpi-monitor/
sudo cp -r templates /opt/rpi-monitor/

cd /opt/rpi-monitor
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

### 2. Run (development)

```bash
python3 rpi_monitor.py
# Dashboard → http://<pi-ip>:8585
```

### 3. Run as a systemd service (production)

```bash
sudo cp rpi-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-monitor
sudo systemctl status rpi-monitor
```

Edit `/etc/systemd/system/rpi-monitor.service` to set environment variables before enabling.

> **If using a venv**, update `ExecStart` in the service file to use the venv Python:
> ```
> ExecStart=/opt/rpi-monitor/.venv/bin/python3 /opt/rpi-monitor/rpi_monitor.py
> ```
> The default service file points to `/usr/bin/python3` (system Python). Flask will not be found if it was installed only into the venv.

### 4. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIMONITOR_HOST` | `0.0.0.0` | Bind address |
| `PIMONITOR_PORT` | `8585` | Listen port |
| `PIMONITOR_DEBUG` | `false` | Flask debug mode |
| `PIMONITOR_TOKEN` | _(empty)_ | Bearer token for auth. Empty = auth disabled |
| `PIMONITOR_SERVICES` | `ssh,nginx,docker,...` | Comma-separated list of systemd services to monitor |
| `PIMONITOR_REFRESH` | `2` | Dashboard auto-refresh interval in seconds |
| `PIMONITOR_SERVICES_FILE` | `./services.json` | Path to persist the service list |

### 5. Authentication

Set `PIMONITOR_TOKEN` to any secret string. All API requests must then include:

```
Authorization: Bearer <token>
```

The dashboard prompts for the token automatically if auth is enabled.

### 6. Adding / Removing Monitored Services

Via the dashboard UI (Services tab → edit icon), or via API:

```bash
# Add
curl -X POST http://pi:8585/api/services/config \
  -H "Content-Type: application/json" \
  -d '{"name": "myapp"}'

# Remove
curl -X DELETE http://pi:8585/api/services/config/myapp
```

Changes persist to `services.json` and survive restarts.

---

## Fleet Hub

The Hub is optional. Run it on any machine that can reach your Pi nodes over the network.

### 1. Install

```bash
cd hub/
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Run (development)

```bash
python3 pi_monitor_hub.py
# Dashboard → http://<hub-ip>:8686
```

### 3. Run as a systemd service

```bash
sudo cp hub/rpi-monitor-hub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-monitor-hub
```

### 4. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIHUB_HOST` | `0.0.0.0` | Bind address |
| `PIHUB_PORT` | `8686` | Listen port |
| `PIHUB_DEBUG` | `false` | Flask debug mode |
| `PIHUB_TOKEN` | _(empty)_ | Bearer token for hub auth |
| `PIHUB_POLL_INTERVAL` | `5` | Seconds between node polls |
| `PIHUB_TIMEOUT` | `4` | Per-request timeout to nodes (seconds) |
| `PIHUB_DISCOVERY_PORT` | `8585` | Port scanned during subnet discovery |
| `PIHUB_NODES_FILE` | `./hub_nodes.json` | Path to persist node registry |

### 5. Adding Nodes

Via the Hub dashboard UI, or via API:

```bash
# Add a node manually
curl -X POST http://hub:8686/api/nodes \
  -H "Content-Type: application/json" \
  -d '{"host": "192.168.1.42", "port": 8585, "label": "Pi-Living-Room"}'

# Trigger subnet auto-discovery
curl -X POST http://hub:8686/api/discover
```

### 6. Node Authentication

If a node has `PIMONITOR_TOKEN` set, provide it when registering:

```bash
curl -X POST http://hub:8686/api/nodes \
  -H "Content-Type: application/json" \
  -d '{"host": "192.168.1.42", "port": 8585, "label": "Secure-Pi", "token": "secret"}'
```

The hub stores and uses the token for all requests to that node.

---

## Sudo Permissions

The node agent runs as `root` under systemd (required for `systemctl` control and `reboot`/`shutdown`). For development without root, service control and power actions will fail gracefully — metric reads still work.

To run as a non-root user with limited sudo, add to `/etc/sudoers.d/rpi-monitor`:

```
rpi-monitor ALL=(ALL) NOPASSWD: /bin/systemctl, /sbin/reboot, /sbin/shutdown
```

Then change `User=root` to `User=rpi-monitor` in the service file and create the user.
