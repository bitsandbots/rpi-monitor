# RPiMonitor — Overview

## Purpose

RPiMonitor is a lightweight, self-hosted system monitoring and management console for Raspberry Pi and generic Linux devices. It provides a real-time web dashboard for viewing hardware metrics, controlling systemd services, inspecting running processes, and issuing power commands — all without requiring cloud connectivity.

## Goals

- **Zero cloud dependency** — runs entirely on-device; no telemetry, no external APIs.
- **Low overhead** — reads directly from `/proc` and `/sys`; no heavy agent or daemon.
- **Operational control** — start/stop/restart services and send signals to processes from the browser.
- **Multi-node fleet management** — the optional Hub component aggregates any number of RPiMonitor nodes into a single pane of glass.
- **Secure by default** — optional bearer-token authentication; systemd hardening via `ProtectSystem`, `PrivateTmp`, `ProtectHome`.
- **Hardware health monitoring** — real-time alerts for temperature, power (undervoltage), and system failures.

## v2.2.0 — New Features

### Hardware Alerts

RPiMonitor now includes real-time hardware health monitoring with automated alerts:

| Feature | Description |
|---------|-------------|
| **Temperature Alerts** | Automatic warnings at 70°C (warning), 80°C (critical), and 85°C (throttling) |
| **Low Voltage Warning** | Detects under-voltage events and current voltage issues via `vcgencmd get_throttled` |
| **Service Failure Detection** | Monitors critical services (systemd-journald, dbus, cron) and reports failures |
| **System Stability Checks** | Detects OOM events, kernel errors, and service restart loops |

Alerts appear as cards on the Overview tab and clear automatically when conditions normalize.

## Components

## Components

| Component | Entry Point | Default Port | Role |
|-----------|------------|-------------|------|
| **Node Agent** | `rpi_monitor.py` | `8585` | Per-device monitor & control API |
| **Fleet Hub** | `hub/rpi_monitor_hub.py` | `8686` | Multi-node aggregation dashboard |

A node agent runs on every Pi you want to monitor. The hub is optional and typically runs on one machine (or a dedicated management Pi) that can reach all nodes over the network.

## License

MIT — open source, no restrictions on personal or commercial use.
