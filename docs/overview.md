# RPiMonitor — Overview

## Purpose

RPiMonitor is a lightweight, self-hosted system monitoring and management console for Raspberry Pi and generic Linux devices. It provides a real-time web dashboard for viewing hardware metrics, controlling systemd services, inspecting running processes, and issuing power commands — all without requiring cloud connectivity.

## Goals

- **Zero cloud dependency** — runs entirely on-device; no telemetry, no external APIs.
- **Low overhead** — reads directly from `/proc` and `/sys`; no heavy agent or daemon.
- **Operational control** — start/stop/restart services and send signals to processes from the browser.
- **Multi-node fleet management** — the optional Hub component aggregates any number of RPiMonitor nodes into a single pane of glass.
- **Secure by default** — optional bearer-token authentication; systemd hardening via `ProtectSystem`, `PrivateTmp`, `ProtectHome`.

## Components

| Component | Entry Point | Default Port | Role |
|-----------|------------|-------------|------|
| **Node Agent** | `rpi_monitor.py` | `8585` | Per-device monitor & control API |
| **Fleet Hub** | `hub/rpi_monitor_hub.py` | `8686` | Multi-node aggregation dashboard |

A node agent runs on every Pi you want to monitor. The hub is optional and typically runs on one machine (or a dedicated management Pi) that can reach all nodes over the network.

## License

MIT — open source, no restrictions on personal or commercial use.
