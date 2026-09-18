# Migration Guide: sys-monitor → sys-monitor

This guide covers upgrading from sys-monitor v2.0.0 to sys-monitor v2.0.0.

## What Changed

| Category | Old Value | New Value |
|----------|-----------|-----------|
| File name | `sys_monitor.py` | `sys_monitor.py` |
| Service name | `sys-monitor` | `sys-monitor` |
| Hub service | `sys-monitor-hub` | `sys-monitor-hub` |
| Install directory | `/opt/sys-monitor` | `/opt/sys-monitor` |
| GitHub URL | `coreconduit/sys-monitor` | `coreconduit/sys-monitor` |
| GitHub URL (bitsandbots) | `bitsandbots/sys-monitor` | `bitsandbots/sys-monitor` |

## What Stayed the Same

- **Environment variables:** `SYSMONITOR_*` and `SYSHUB_*` prefixes unchanged
- **Ports:** Node agent (8585), Hub (8686)
- **API endpoints:** All `/api/*` paths unchanged
- **Web UI:** Same interface, same functionality
- **Configuration format:** Same structure

---

## Migration Steps

### Option 1: Fresh Install (Recommended)

```bash
# Backup existing configuration (optional)
sudo cp /opt/sys-monitor/services.json /opt/sys-monitor/services.json.bak 2>/dev/null || true

# Install new version
git clone https://github.com/bitsandbots/sys-monitor
cd sys-monitor
sudo ./install.sh
```

This will install to `/opt/sys-monitor` with the new service name.

### Option 2: In-Place Upgrade (Existing Installation)

If you want to keep your existing configuration:

```bash
# 1. Stop the current service
sudo systemctl stop sys-monitor sys-monitor-hub

# 2. Clone the new repo
git clone https://github.com/bitsandbots/sys-monitor /opt/sys-monitor

# 3. Copy your existing configuration
sudo cp /opt/sys-monitor/services.json /opt/sys-monitor/
sudo cp /opt/sys-monitor/.env /opt/sys-monitor/ 2>/dev/null || true

# 4. Install as new service
cd /opt/sys-monitor
sudo ./install.sh
```

### Option 3: Manual Upgrade (Full Control)

```bash
# Stop services
sudo systemctl stop sys-monitor sys-monitor-hub

# Download and extract release
curl -LO https://github.com/bitsandbots/sys-monitor/releases/download/v2.0.0/sys-monitor-2.0.0.tar.gz
tar -xzf sys-monitor-2.0.0.tar.gz

# Install new service (this removes old service)
cd sys-monitor-2.0.0
sudo ./install.sh

# If you had custom services.json, restore it:
sudo cp /tmp/sys-monitor-2.0.0.tar.gz-backup/services.json /opt/sys-monitor/
```

---

## Post-Migration Checklist

After upgrading, verify:

- [ ] Node agent accessible at `http://<ip>:8585`
- [ ] Hub accessible at `http://<ip>:8686` (if installed)
- [ ] Service running: `systemctl status sys-monitor`
- [ ] Logs showing correct version: `journalctl -u sys-monitor -f`
- [ ] Services list persisted: Check Services tab in UI

---

## Uninstalling Old Installation

If you did a fresh install and want to clean up:

```bash
# Remove old directory
sudo rm -rf /opt/sys-monitor 2>/dev/null || true

# Uninstall hub if installed separately
cd /opt/sys-monitor/hub  # if it still exists
sudo ./install.sh --uninstall
```

---

## Troubleshooting

### "Permission denied" on /opt/sys-monitor

The new service expects `/opt/sys-monitor`. Update your sudoers rules if running as non-root:

```bash
# /etc/sudoers.d/sys-monitor (was: sys-monitor)
sys-monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ssh nginx docker
sys-monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ssh nginx docker
sys-monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ssh nginx docker
sys-monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable ssh nginx docker
sys-monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable ssh nginx docker
sys-monitor ALL=(ALL) NOPASSWD: /sbin/reboot
sys-monitor ALL=(ALL) NOPASSWD: /sbin/shutdown
```

### Old service still running after upgrade

```bash
# Check for old service
systemctl list-units | grep sys-monitor

# Stop and remove if found
sudo systemctl stop sys-monitor sys-monitor-hub
sudo systemctl disable sys-monitor sys-monitor-hub
sudo rm -f /etc/systemd/system/sys-monitor*.service
sudo systemctl daemon-reload
```

### Configuration not persisting

Environment variables in systemd unit files may reference the old paths. Check:

```bash
sudo systemctl cat sys-monitor | grep -i environment
```

If needed, update the service file:

```bash
sudo systemctl edit sys-monitor
# Add: Environment=SYSMONITOR_SERVICES_FILE=/opt/sys-monitor/services.json
sudo systemctl daemon-reload
sudo systemctl restart sys-monitor
```

---

## Support

For issues, check:
- Wiki: https://github.com/bitsandbots/sys-monitor/wiki
- Documentation: `docs/` folder in the repository
