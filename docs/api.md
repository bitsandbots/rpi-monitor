# PiMonitor — API Reference

All responses are JSON. Authentication (if enabled) requires `Authorization: Bearer <token>` on every request.

---

## Node Agent API (`pi_monitor.py`, default port 8585)

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
  "is_raspberry_pi": true,
  "model": "Raspberry Pi 5 Model B Rev 1.0",
  "revision": "d04170",
  "serial": "abcdef12",
  "hardware": "BCM2835",
  "soc": "BCM2712",
  "gpu_mb": 76,
  "hostname": "pi5",
  "kernel": "6.6.31+rpt-rpi-2712",
  "architecture": "aarch64",
  "os": "Debian GNU/Linux 12 (bookworm)",
  "cpu_model": "Cortex-A76",
  "cpu_max_freq": "2400 MHz",
  "python": "3.11.2",
  "boot_time": "2026-04-10T07:00:00"
}
```

> `serial` is the last 8 characters of the CPU serial number.
> `gpu_mb` is `null` on non-Pi hardware.

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
    "gpu_mb": 76,
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
    "command": "python3 /opt/pi-monitor/pi_monitor.py"
  }
]
```

#### `DELETE /api/processes/<pid>`
Send a signal to a process.

Query param: `?signal=N` (default 15 / SIGTERM).

```bash
curl -X DELETE "http://pi:8585/api/processes/1234?signal=9"
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
curl -X POST http://pi:8585/api/services/nginx/restart
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
curl -X POST http://pi:8585/api/power/reboot
```

Response:
```json
{"success": true, "action": "reboot"}
```

---

### Logs

#### `GET /api/logs`
Retrieve the in-memory event log (ring buffer, max 200 entries).

Query params: `?limit=50` (default 100).

```json
[
  {"ts": "14:22:01", "msg": "PiMonitor ready.", "level": "success"},
  {"ts": "14:23:10", "msg": "Service restarted: nginx", "level": "info"}
]
```

Log levels: `info`, `success`, `warning`, `error`.

---

## Fleet Hub API (`hub/pi_monitor_hub.py`, default port 8686)

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
      "label": "Pi-Living-Room",
      "token_set": false,
      "added": "2026-04-10T07:00:00",
      "online": true,
      "last_seen": 1713100000.0,
      "hostname": "pi5",
      "model": "Raspberry Pi 5 Model B Rev 1.0",
      "soc": "BCM2712",
      "architecture": "aarch64",
      "os": "Debian GNU/Linux 12 (bookworm)",
      "kernel": "6.6.31+rpt-rpi-2712",
      "is_raspberry_pi": true,
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
{"host": "192.168.1.42", "port": 8585, "label": "Pi-A", "token": ""}
```

#### `DELETE /api/nodes/<nid>`
Remove a node from the registry.

#### `PUT /api/nodes/<nid>`
Update a node's label or token.

---

### Discovery

#### `POST /api/discover`
Scan the local subnet for PiMonitor agents. Probes `<ip>:PIHUB_DISCOVERY_PORT/api/ping` in parallel across the /24.

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
      "hostname": "pi5",
      "model": "Raspberry Pi 5 Model B Rev 1.0",
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
