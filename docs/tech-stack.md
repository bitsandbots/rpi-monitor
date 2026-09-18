# SysMonitor — Tech Stack

## Runtime

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| OS | Ubuntu 24.04 (also Debian-compatible) | 64-bit | |
| Python | CPython | 3.11+ | 3.13 used in dev |
| Web framework | Flask | ≥ 3.0.0 | Node agent and hub both use Flask |
| HTTP client | Requests | ≥ 2.31 | Hub only — proxies to node APIs |

## Frontend

| Technology | Role |
|-----------|------|
| Vanilla JS (ES2020) | Dashboard polling, DOM updates, tab management |
| Bootstrap 5 | Layout, modals, utility classes |
| Self-hosted WOFF2 (Exo 2, Plus Jakarta Sans, IBM Plex Mono) | Typography — offline capable, no CDN dependency |
| CSS custom properties | Brand theming (navy/silver/blue/orange) |

No build step — the dashboard is a single self-contained `index.html`.

## System Interfaces

| Interface | Used By | Data |
|-----------|---------|------|
| `/proc/stat` | `get_cpu_usage()` | Per-core CPU jiffies (delta method) |
| `/proc/meminfo` | `get_memory()` | Total, free, available, cached RAM |
| `/proc/uptime` | `get_uptime()` | Seconds since boot |
| `/sys/class/net/<iface>/statistics/{rx,tx}_bytes` | `get_network()` | Interface RX/TX byte counters |
| `ps aux` (subprocess) | `get_top_processes()` | Top processes by CPU: user, PID, cpu%, mem%, command |
| `/sys/class/thermal/thermal_zone0/temp` | `get_cpu_temperature()` | CPU temp in millidegrees |
| `df -BM` (subprocess) | `get_storage()` | Mount points, sizes in MB, filesystem type, used/free space |
| `systemctl` (subprocess) | `get_services()`, `control_service()` | Service status, start/stop/restart/enable/disable |
| `sudo reboot / shutdown` (subprocess) | `system_power()` | Power actions |

## Process Management (Node)

| Tool | Purpose |
|------|---------|
| `os.kill(pid, sig)` | Send signal to process (default SIGTERM=15) |
| `threading.Lock` | Guards CPU stat differential and event log |

## Concurrency (Hub)

| Tool | Purpose |
|------|---------|
| `threading.Thread` | Background poller loop |
| `concurrent.futures.ThreadPoolExecutor` | Parallel node polling (`max_workers=min(node_count, 8)`) |
| `threading.Lock` | Guards node registry dict |

## Persistence

| File | Location | Contents |
|------|----------|---------|
| `services.json` | `SYSMONITOR_SERVICES_FILE` (default: project root) | Ordered list of monitored service names |
| `hub_nodes.json` | `SYSHUB_NODES_FILE` (default: `hub/`) | Node registry (host, port, label, token) |

## Process Supervisor

| Tool | Config File |
|------|------------|
| systemd | `sys-monitor.service` / `hub/sys-monitor-hub.service` |
