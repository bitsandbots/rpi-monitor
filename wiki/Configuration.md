# Configuration

All configuration is via environment variables. No config files are required.

Set them in the systemd unit file (`/etc/systemd/system/sys-monitor.service`) or export them before running directly.

---

## Node Agent (`sys_monitor.py`)

| Variable | Default | Description |
|---|---|---|
| `SYSMONITOR_HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` to restrict to localhost. |
| `SYSMONITOR_PORT` | `8585` | Listen port. |
| `SYSMONITOR_DEBUG` | `false` | Flask debug mode. **Never enable in production.** |
| `SYSMONITOR_TOKEN` | *(empty)* | Bearer token for API auth. Leave empty to disable. |
| `SYSMONITOR_SERVICES` | `ssh,nginx,docker,...` | Comma-separated list of systemd services to monitor. |
| `SYSMONITOR_REFRESH` | `2` | Frontend polling interval in seconds. |
| `SYSMONITOR_SERVICES_FILE` | `./services.json` | Path to persist the service list. |

### Authentication

When `SYSMONITOR_TOKEN` is set, all API endpoints require:

```
Authorization: Bearer <your-token>
```

The web UI does not currently send auth headers — token auth is intended for API-only access. For UI auth, place SysMonitor behind a reverse proxy with HTTP basic auth.

### Service List

The service list is seeded from `SYSMONITOR_SERVICES` on first run, then persisted to `services.json`. Once the file exists, the env var is ignored. To reset, delete `services.json` and restart.

You can also manage the list live via the API:
- `POST /api/services/config` — add a service
- `DELETE /api/services/config/<name>` — remove
- `PUT /api/services/config/<name>` — rename

---

## Hub (`hub/sys_monitor_hub.py`)

| Variable | Default | Description |
|---|---|---|
| `SYSHUB_HOST` | `0.0.0.0` | Bind address. |
| `SYSHUB_PORT` | `8686` | Listen port. |
| `SYSHUB_TOKEN` | *(empty)* | Bearer token for hub API auth. |
| `SYSHUB_POLL_INTERVAL` | `5` | Seconds between fleet health polls. |
| `SYSHUB_TIMEOUT` | `4` | Per-node HTTP timeout in seconds. |
| `SYSHUB_DISCOVERY_PORT` | `8585` | Default port to probe during network discovery. |
| `SYSHUB_NODES_FILE` | `./hub_nodes.json` | Path to the persistent node registry. |
| `SYSHUB_DEBUG` | `false` | Flask debug mode. |

### Node Registry

Registered nodes are stored in `hub_nodes.json`. This file is created automatically when the first node is added. To clear all nodes, delete the file and restart the hub.

---

## Setting Variables in the systemd Unit

Edit the service file:

```bash
sudo systemctl edit sys-monitor
```

Add:

```ini
[Service]
Environment=SYSMONITOR_TOKEN=my-secret
Environment=SYSMONITOR_SERVICES=ssh,nginx,docker,ollama
Environment=SYSMONITOR_REFRESH=3
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart sys-monitor
```

---

## `.env.example`

A complete `.env.example` is included in the repo covering all variables for both components.
