# Installation

## Requirements

- Python 3.11+
- Flask 3.0+ (`pip install flask`)
- systemd (for service install)
- Linux with `/proc` and `/sys` (Raspberry Pi OS, Debian, Ubuntu)

---

## One-Command Install (Recommended)

Clone the repo and run `install.sh` as root:

```bash
git clone https://github.com/bitsandbots/rpi-monitor
cd rpi-monitor
sudo ./install.sh
```

### Install options

| Command | What it does |
|---|---|
| `sudo ./install.sh` | Node agent only |
| `sudo ./install.sh --hub` | Node agent + Hub |
| `sudo ./install.sh --hub-only` | Hub only (no node agent) |
| `sudo ./install.sh --uninstall` | Remove everything |

The installer will:
1. Check Python 3.11+, pip3, and systemctl are present
2. Copy files to `/opt/pi-monitor`
3. Install Python dependencies via pip
4. Install and enable the systemd service
5. Wait up to 10 seconds for the health endpoint to respond

---

## Install from Release Tarball

Download a release from [GitHub Releases](https://github.com/bitsandbots/pi-monitor/releases):

```bash
curl -LO https://github.com/bitsandbots/rpi-monitor/releases/download/v2.0.0/rpi-monitor-2.0.0.tar.gz
# Verify checksum
curl -LO https://github.com/bitsandbots/rpi-monitor/releases/download/v2.0.0/rpi-monitor-2.0.0.sha256
sha256sum -c rpi-monitor-2.0.0.sha256

tar -xzf rpi-monitor-2.0.0.tar.gz
cd rpi-monitor-2.0.0
sudo ./install.sh
```

---

## Manual Install

```bash
# Install dependency
pip3 install flask --break-system-packages

# Run directly
python3 pi_monitor.py
```

Access at `http://<pi-ip>:8585`.

---

## Install as systemd Service (Manual)

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

---

## Sudoers (Non-Root)

If running as a non-root user, grant scoped sudoers access:

```
# /etc/sudoers.d/pi-monitor
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ssh nginx docker ollama
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ssh nginx docker ollama
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ssh nginx docker ollama
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable ssh nginx docker ollama
pimonitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable ssh nginx docker ollama
pimonitor ALL=(ALL) NOPASSWD: /sbin/reboot
pimonitor ALL=(ALL) NOPASSWD: /sbin/shutdown
```

List each service explicitly — do **not** use wildcards.

---

## Uninstall

```bash
sudo ./install.sh --uninstall
```

This stops and disables both services, removes unit files, and deletes `/opt/rpi-monitor`.
