# API Reference

All responses are JSON. If `PIMONITOR_TOKEN` / `PIHUB_TOKEN` is set, every request must include:

```
Authorization: Bearer <token>
```

---

## Node Agent API — port 8585

### `GET /api/ping`
Health check. Returns immediately.

```json
{"ok": true, "ts": 1713100000.0}
```

---

### `GET /api/boot`
Hardware identity detected once at startup and cached.

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

> `gpu_mb` is `null` on non-Pi hardware.

---

### `GET /api/status`
Live CPU, memory, temperature, uptime, and network rates. Polled by the dashboard on every refresh cycle.

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
    "eth0": {"rx_rate": 15420, "tx_rate": 3210}
  },
  "timestamp": 1713100000.0
}
```

> `network_rates` values are **bytes/sec** since the previous poll.

---

### `GET /api/storage`
Mounted filesystem usage.

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

### `GET /api/network`
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

---

### `GET /api/processes`
Top processes by CPU.

Query params: `?limit=N` (default 12, max 50)

```json
[
  {
    "user": "root",
    "pid": 1234,
    "cpu": 12.5,
    "mem": 1.3,
    "command": "python3 /opt/rpi-monitor/rpi_monitor.py"
  }
]
```

### `DELETE /api/processes/<pid>`
Send a signal to a process.

Query param: `?signal=N` (default 15 / SIGTERM, use 9 for SIGKILL)

```bash
curl -X DELETE "http://pi:8585/api/processes/1234?signal=9"
```

```json
{"success": true, "pid": 1234, "signal": 9}
```

---

### `GET /api/services`
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

### `POST /api/services/<name>/<action>`
Control a service. Actions: `start`, `stop`, `restart`, `enable`, `disable`.

```bash
curl -X POST http://pi:8585/api/services/nginx/restart
```

```json
{"success": true, "service": "nginx", "action": "restart", "stderr": ""}
```

### Service List Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/services/config` | Return current service list |
| `POST` | `/api/services/config` | Add a service `{"name":"myapp"}` |
| `DELETE` | `/api/services/config/<name>` | Remove a service |
| `PUT` | `/api/services/config/<name>` | Rename `{"name":"new-name"}` |

---

### `POST /api/power/<action>`
Actions: `reboot`, `shutdown`.

```bash
curl -X POST http://pi:8585/api/power/reboot
```

```json
{"success": true, "action": "reboot"}
```

---

### `GET /api/logs`
In-memory event log (ring buffer, max 200 entries).

Query params: `?limit=50` (default 100)

```json
[
  {"ts": "14:22:01", "msg": "PiMonitor ready.", "level": "success"},
  {"ts": "14:23:10", "msg": "Service restarted: nginx", "level": "info"}
]
```

Log levels: `info`, `success`, `warning`, `error`

---

## Fleet Hub API — port 8686

### `GET /api/ping`
```json
{"ok": true, "hub": true, "ts": 1713100000.0}
```

### `GET /api/fleet`
Cached snapshot of all registered nodes.

```json
{
  "nodes": [
    {
      "id": "192-168-1-42-8585",
      "host": "192.168.1.42",
      "port": 8585,
      "label": "Pi-Living-Room",
      "online": true,
      "last_seen": 1713100000.0,
      "cpu_usage": 12.4,
      "temperature": 52.3,
      "memory_percent": 25.0,
      "uptime": "4d 0h 0m"
    }
  ],
  "total": 1,
  "online": 1
}
```

> Status fields are `null` if the node has never been successfully polled.

### Node Registry

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/nodes` | Register `{"host":"...", "port":8585, "label":"...", "token":""}` |
| `DELETE` | `/api/nodes/<nid>` | Remove a node |
| `PUT` | `/api/nodes/<nid>` | Update label or token |

### `POST /api/discover`
Scan the local /24 subnet for RPiMonitor agents.

```json
{"subnet": "192.168.1.0/24", "port": 8585}
```

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

### Node Proxy Routes

All proxy routes forward to the corresponding node's API.

| Method | Hub Route | Forwards To |
|---|---|---|
| `GET` | `/api/nodes/<nid>/status` | `/api/status` |
| `GET` | `/api/nodes/<nid>/boot` | `/api/boot` |
| `GET` | `/api/nodes/<nid>/services` | `/api/services` |
| `POST` | `/api/nodes/<nid>/services/<svc>/<action>` | `/api/services/<svc>/<action>` |
| `GET` | `/api/nodes/<nid>/storage` | `/api/storage` |
| `GET` | `/api/nodes/<nid>/processes` | `/api/processes` |
| `GET` | `/api/nodes/<nid>/network` | `/api/network` |
| `GET` | `/api/nodes/<nid>/logs` | `/api/logs` |
| `POST` | `/api/nodes/<nid>/power/<action>` | `/api/power/<action>` |

Unreachable nodes return `502 {"error": "unreachable"}`.

---

## Error Codes

| Status | Meaning |
|---|---|
| `400` | Bad request — invalid parameters |
| `401` | Unauthorized — missing or invalid token |
| `404` | Not found — service, PID, or node doesn't exist |
| `409` | Conflict — duplicate service or node |
| `502` | Bad gateway — hub cannot reach the node |
