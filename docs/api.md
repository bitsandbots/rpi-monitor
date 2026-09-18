# SysMonitor — API Reference

All responses are JSON. Authentication (if enabled) requires `Authorization: Bearer <token>` on every request.

---

## Node Agent API (`sys_monitor.py`, default port 8585)

### Health

#### `GET /api/ping`
Returns immediately. Use to check if the agent is up.

```json
{"ok": true, "ts": 1713100000.0}
```

---

### System

#### `GET /api/boot`
Hardware identity, detected once at startup and cached.

```json
{
  "model": "Generic Linux",
  "revision": "d04170",
  "serial": "abcdef12",
  "hardware": "BCM2835",
  "soc": "Intel Core i7-13700",
  "hostname": "ubuntu-server",
  "kernel": "6.8.0-100-generic",
  "architecture": "x86_64",
  "os": "Ubuntu 24.04 LTS",
  "cpu_model": "Intel Core i7-13700",
  "cpu_max_freq": "2400 MHz",
  "python": "3.13.0",
  "boot_time": "2026-04-10T07:00:00"
}
```

> `serial` is the last 8 characters of the CPU serial number.

#### `GET /api/status`
Live snapshot — CPU, memory, temperature, uptime, network rates. Polled by the dashboard on every refresh cycle.

```json
{
  "cpu": {
    "usage": 12.4,
    "cores": [10.1, 14.7, 11.2, 13.6],
    "core_count": 4,
    "load_avg": [0.45, 0.38, 0.31],
    "freq_mhz": 2400
  },
  "memory": {
    "total_mb": 8192.0,
    "used_mb": 2048.3,
    "free_mb": 4096.1,
    "available_mb": 5900.2,
    "cached_mb": 512.4,
    "buffers_mb": 128.0,
    "swap_total_mb": 100.0,
    "swap_used_mb": 0.0,
    "percent": 25.0
  },
  "temperature": 52.3,
  "uptime": {
    "seconds": 345600,
    "formatted": "4d 0h 0m",
    "days": 4,
    "hours": 0,
    "minutes": 0
  },
  "network_rates": {
    "eth0": {"rx_rate": 15420, "tx_rate": 3210},
    "wlan0": {"rx_rate": 0, "tx_rate": 0}
  },
  "timestamp": 1713100000.0
}
```

> `network_rates` values are bytes/sec since the previous poll.
> `timestamp` is a Unix float, not a formatted string.

---

### Storage

#### `GET /api/storage`
Mounted filesystem usage via `df -BM`. Returns an array.

```json
[
  {
    "device": "/dev/mmcblk0p2",
    "mount": "/",
    "total_mb": 59000,
    "used_mb": 12000,
    "avail_mb": 44000,
    "percent": 21,
    "fstype": "ext4"
  }
]
```

---

### Network

#### `GET /api/network`
Per-interface stats with throughput rates.

```json
{
  "interfaces": [
    {
      "name": "eth0",
      "state": "up",
      "mac": "d8:3a:dd:xx:xx:xx",
      "ip": "192.168.1.42",
      "rx_bytes": 1048576000,
      "tx_bytes": 524288000,
      "rx_mb": 1000.0,
      "tx_mb": 500.0
    }
  ],
  "rates": {
    "eth0": {"rx_rate": 15420, "tx_rate": 3210}
  }
}
```

> `rates` values are bytes/sec since the previous call.

---

### Processes

#### `GET /api/processes`
Top processes by CPU usage (`ps aux --sort=-%cpu`).

Query params: `?limit=N` (default 12, max 50).

```json
[
  {
    "user": "root",
    "pid": 1234,
    "cpu": 12.5,
    "mem": 1.3,
    "command": "python3 /opt/sys-monitor/sys_monitor.py"
  }
]
```

#### `DELETE /api/processes/<pid>`
Send a signal to a process.

Query param: `?signal=N` (default 15 / SIGTERM).

```bash
curl -X DELETE "http://node:8585/api/processes/1234?signal=9"
```

Response:
```json
{"success": true, "pid": 1234, "signal": 9}
```

Error (process not found):
```json
{"success": false, "error": "PID 1234 not found"}
```

---

### Services

#### `GET /api/services`
Status of all monitored services.

```json
[
  {
    "name": "ssh",
    "active": true,
    "active_state": "active",
    "enabled": true,
    "enabled_state": "enabled",
    "description": "OpenBSD Secure Shell server"
  }
]
```

#### `POST /api/services/<name>/<action>`
Control a service. Valid actions: `start`, `stop`, `restart`, `enable`, `disable`.

```bash
curl -X POST http://node:8585/api/services/nginx/restart
```

Response:
```json
{"success": true, "service": "nginx", "action": "restart", "stderr": ""}
```

#### `GET /api/services/config`
Return the current persisted service list as a bare array.

```json
["ssh", "nginx", "docker"]
```

#### `POST /api/services/config`
Add a service to the monitored list.

```json
{"name": "myapp"}
```

#### `DELETE /api/services/config/<name>`
Remove a service from the list.

#### `PUT /api/services/config/<name>`
Rename a service entry.

```json
{"name": "myapp-v2"}
```

---

### Power

#### `POST /api/power/<action>`
Valid actions: `reboot`, `shutdown`.

```bash
curl -X POST http://node:8585/api/power/reboot
```

Response:
```json
{"success": true, "action": "reboot"}
```

---

### Logs

#### `GET /api/logs`
Retrieve the in-memory event log (ring buffer, max 200 entries).

Query params:
- `?limit=50` (default 100)
- `?system=true` — Include system errors from journalctl

```json
[
  {"ts": "14:22:01", "msg": "SysMonitor ready.", "level": "success"},
  {"ts": "14:23:10", "msg": "Service restarted: nginx", "level": "info"}
]
```

Log levels: `info`, `success`, `warning`, `error`.

---

### Ports

#### `GET /api/ports`
List all listening TCP/UDP ports in range 0-9999.

```json
[
  {"port": 22, "protocol": "tcp", "address": "0.0.0.0"},
  {"port": 80, "protocol": "tcp", "address": "*"},
  {"port": 111, "protocol": "tcp", "address": "0.0.0.0"},
  {"port": 111, "protocol": "udp", "address": "0.0.0.0"}
]
```

Uses `ss -tuln` for fast enumeration (no port scanning).

---

### Services with Ports

#### `GET /api/services-with-ports`
Return systemd services merged with open port information.

```json
[
  {
    "name": "ssh",
    "port": 22,
    "protocol": "tcp",
    "active": true,
    "enabled": true,
    "known": true,
    "description": "OpenBSD Secure Shell server"
  },
  {
    "name": null,
    "port": 3306,
    "protocol": "tcp",
    "address": "127.0.0.1",
    "known": false,
    "description": "Port 3306/tcp"
  }
]
```

- `known: true` — Service is in the monitored list
- `known: false` — Port is open but not mapped to a known service

---

### System Errors

#### `GET /api/system-errors`
Retrieve recent error-level journal entries.

Query params: `?limit=50` (default 50, max 200).

```json
[
  {
    "ts": "14:22:01",
    "unit": "nginx.service",
    "msg": "Failed to start nginx.service",
    "priority": "3"
  }
]
```

Uses `journalctl -p err` to filter for error priority.

---

### System Health

#### `GET /api/system-health`
Returns system health status, critical services, and stability checks. Added in v2.2.0.

```json
{
  "stable": true,
  "issues": [],
  "critical_services_failed": [],
  "all_critical_ok": true
}
```

When there are issues:

```json
{
  "stable": false,
  "issues": [
    { "type": "oom", "severity": "critical", "message": "Out of memory condition detected" },
    { "type": "kernel_error", "severity": "critical", "message": "Kernel oops detected" },
    { "type": "restart_loop", "severity": "warning", "message": "Service restart loop detected (7 restarts)" }
  ],
  "critical_services_failed": [
    { "name": "dbus", "state": "inactive", "critical": true }
  ],
  "all_critical_ok": false
}
```

Checks performed:
- Critical service status (`systemd-journald`, `dbus`, `cron`, `systemd-networkd`/`networking`)
- OOM events in journal
- Kernel errors in journal
- Service restart loops (>5 restarts in recent logs)

---

## Fleet Hub API (`hub/sys_monitor_hub.py`, default port 8686)

### Health

#### `GET /api/ping`
```json
{"ok": true, "hub": true, "ts": 1713100000.0}
```

---

### Fleet

#### `GET /api/fleet`
Cached snapshot of all registered nodes (updated every poll interval).

```json
{
  "nodes": [
    {
      "id": "192-168-1-42-8585",
      "host": "192.168.1.42",
      "port": 8585,
      "label": "Living-Room",
      "token_set": false,
      "added": "2026-04-10T07:00:00",
      "online": true,
      "last_seen": 1713100000.0,
      "hostname": "ubuntu-server",
      "model": "Generic Linux",
      "soc": "Intel Core i7-13700",
      "architecture": "x86_64",
      "os": "Ubuntu 24.04 LTS",
      "kernel": "6.8.0-100-generic",
      "cpu_usage": 12.4,
      "cpu_cores": 4,
      "temperature": 52.3,
      "memory_percent": 25.0,
      "memory_total_mb": 8192.0,
      "memory_used_mb": 2048.3,
      "uptime": "4d 0h 0m",
      "load_avg": [0.45, 0.38, 0.31]
    }
  ],
  "total": 1,
  "online": 1
}
```

> `last_seen` is a Unix timestamp float.
> Status fields (`cpu_usage`, `temperature`, etc.) are `null` if the node has never been successfully polled.

---

### Node Registry

#### `POST /api/nodes`
Register a new node.

```json
{"host": "192.168.1.42", "port": 8585, "label": "Node-A", "token": ""}
```

#### `DELETE /api/nodes/<nid>`
Remove a node from the registry.

#### `PUT /api/nodes/<nid>`
Update a node's label or token.

---

### Discovery

#### `POST /api/discover`
Scan the local subnet for SysMonitor agents. Probes `<ip>:SYSHUB_DISCOVERY_PORT/api/ping` in parallel across the /24.

Request body (optional):
```json
{"subnet": "192.168.1.0/24", "port": 8585}
```

Response:
```json
{
  "found": [
    {
      "host": "192.168.1.42",
      "port": 8585,
      "hostname": "ubuntu-server",
      "model": "Generic Linux",
      "id": "192-168-1-42-8585",
      "already_registered": false
    }
  ],
  "count": 1
}
```

---

### Node Proxy Routes

All proxy routes forward to the corresponding node's API. Response shape matches the node API docs above.

| Method | Hub Route | Forwards To |
|--------|-----------|------------|
| `GET` | `/api/nodes/<nid>/status` | `/api/status` |
| `GET` | `/api/nodes/<nid>/boot` | `/api/boot` |
| `GET` | `/api/nodes/<nid>/services` | `/api/services` |
| `POST` | `/api/nodes/<nid>/services/<svc>/<action>` | `/api/services/<svc>/<action>` |
| `GET` | `/api/nodes/<nid>/storage` | `/api/storage` |
| `GET` | `/api/nodes/<nid>/processes` | `/api/processes` |
| `GET` | `/api/nodes/<nid>/network` | `/api/network` |
| `GET` | `/api/nodes/<nid>/logs` | `/api/logs` |
| `POST` | `/api/nodes/<nid>/power/<action>` | `/api/power/<action>` |

If a node is unreachable, proxy routes return `502` with `{"error": "unreachable"}`.

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400` | Bad request — invalid parameters |
| `401` | Unauthorized — missing or invalid token |
| `404` | Not found — service or node doesn't exist |
| `409` | Conflict — duplicate service name |
| `502` | Bad gateway — hub cannot reach the node |
