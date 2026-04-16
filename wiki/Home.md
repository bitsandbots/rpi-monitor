# RPiMonitor Wiki

> Lightweight, self-hosted system monitor and service console for Raspberry Pi and Linux devices.

**Version:** v2.0.0 · **License:** MIT · **Author:** [CoreConduit Consulting Services](https://coreconduit.io)

---

## What is RPiMonitor?

RPiMonitor is a zero-dependency, single-file Flask dashboard that turns any Raspberry Pi or Linux box into a remotely observable node. It reads live data directly from `/proc` and `/sys` — no agents, no psutil, no cloud.

The **Hub** (`rpi_monitor_hub.py`) adds a fleet layer: discover nodes on your network, view aggregate metrics, and control services across all your Pis from one dashboard.

```
Browser
  │
  ├─► Node Agent :8585  ─► /proc, /sys, systemctl
  │
  └─► Hub :8686  ─►  Node A :8585
                  ─►  Node B :8585
                  ─►  Node N :8585
```

---

## Pages

| Page | Description |
|---|---|
| [[Installation]] | One-command and manual install, systemd setup, uninstall |
| [[Configuration]] | All environment variables for node agent and hub |
| [[API Reference]] | Full REST API docs for node agent and hub |
| [[Architecture]] | Data flows, design decisions, key components |
| [[Hub Setup]] | Multi-node fleet management walkthrough |
| [[Release Guide]] | How to version, package, and tag a release |
| [[Troubleshooting]] | Common issues and fixes |

---

## Quick Start

```bash
git clone https://github.com/bitsandbots/rpi-monitor
cd rpi-monitor
sudo ./install.sh
```

Open `http://<pi-ip>:8585`

---

## Repository

**GitHub:** https://github.com/bitsandbots/rpi-monitor
