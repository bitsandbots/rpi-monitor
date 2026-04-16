# Troubleshooting

## Service won't start

**Check logs first:**

```bash
journalctl -u rpi-monitor -n 50 --no-pager
```

Common causes:

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: flask` | Flask not installed | `pip3 install flask --break-system-packages` |
| `Permission denied` on `/proc/...` | Running in restricted sandbox | Check `ProtectSystem=` in the unit file |
| `Address already in use` | Port 8585 taken | Change `PIMONITOR_PORT` or stop the conflicting process |
| `python3: not found` | Python not installed | `sudo apt install python3` |

---

## Dashboard shows stale data / no data

- Check the browser console for failed XHR requests to `/api/status`
- Confirm the service is running: `systemctl status rpi-monitor`
- Verify the Pi's IP and port: `curl http://localhost:8585/api/ping`
- If behind a firewall: `sudo ufw allow 8585/tcp`

---

## CPU usage shows 0% or 100%

The node agent uses **differential sampling** — it computes CPU% from the delta between two `/proc/stat` reads. On the very first poll after startup there is no previous reading, so CPU shows 0%. This corrects itself on the second poll (within `PIMONITOR_REFRESH` seconds).

---

## Temperature reads as `null`

`/sys/class/thermal/thermal_zone0/temp` doesn't exist on all hardware. This is normal on some non-Pi Linux machines and VMs. The dashboard handles `null` gracefully.

---

## Service control returns 401

`PIMONITOR_TOKEN` is set but the request didn't include the `Authorization: Bearer` header. The web UI does not send auth headers — use a reverse proxy with basic auth for UI-level authentication.

---

## `systemctl` commands fail (Permission denied)

The service is running as a non-root user without sudoers rules. Add scoped rules — see [[Installation#Sudoers (Non-Root)]].

---

## Hub shows all nodes as offline

1. Check hub logs: `journalctl -u rpi-monitor-hub -n 50`
2. Verify nodes are reachable from the hub machine: `curl http://<node-ip>:8585/api/ping`
3. Check `PIHUB_TIMEOUT` — increase if nodes are on a slow network
4. If nodes require auth tokens, verify they're set in `hub_nodes.json` or via `PUT /api/nodes/<nid>`

---

## Hub discovery finds nothing

- Confirm nodes are running: `systemctl status rpi-monitor` on each Pi
- Verify the subnet matches your network (e.g. `192.168.1.0/24` vs `10.0.0.0/24`)
- Check `PIHUB_DISCOVERY_PORT` matches `PIMONITOR_PORT` on nodes (both default to `8585`)
- Firewall: ensure port 8585 is open between the hub and the Pi subnet

---

## `release.sh` fails: "Working tree is dirty"

Commit or stash all changes before cutting a release:

```bash
git stash
./release.sh 2.1.0
git stash pop
```

Or use `--dry-run` to preview without the clean-tree requirement.

---

## `/proc/device-tree/model` not found

Normal on non-Pi hardware. `is_raspberry_pi` will be `false` and model-specific fields (`soc`, `gpu_mb`) will be `null`. All other monitoring features work normally.

---

## High memory usage on the hub

Each registered node keeps a cached status dict in memory — the hub is very lightweight. If you're seeing actual high memory, check for runaway Flask debug reloaders (`PIHUB_DEBUG=false`).

---

## Viewing live logs

```bash
# Node agent
journalctl -u rpi-monitor -f

# Hub
journalctl -u rpi-monitor-hub -f

# In-memory event log via API
curl http://localhost:8585/api/logs | python3 -m json.tool
```
