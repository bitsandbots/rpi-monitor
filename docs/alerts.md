# Hardware Alerts & System Health

v2.2.0 introduces real-time hardware monitoring with automated alerts for temperature, power issues, and system failures.

---

## Temperature Alerts

### Thresholds

| Level | Temperature | Action |
|-------|-------------|--------|
| **Normal** | < 70°C | No alert |
| **Warning** | 70°C - 79°C | Yellow alert card shown |
| **Critical** | 80°C - 84°C | Orange alert card shown |
| **Throttling** | ≥ 85°C | Red alert card shown + CPU frequency capped |

### Alert Message Examples

```
⚠️ Warning: CPU at 72°C — consider improving cooling
⚠️ Critical: CPU at 82°C — immediate action needed
⚠️ Throttling: CPU at 87°C — throttling active (CPU frequency capped)
```

---

## System Health Monitoring

### Critical Services Monitored

| Service | Purpose | Restart if down? |
|---------|---------|------------------|
| `systemd-journald` | System logging | No (auto-restart by systemd) |
| `dbus` | System message bus | No |
| `cron` | Scheduled tasks | No |
| `systemd-networkd` or `networking` | Network management | No |

### System Stability Checks

| Check | Detection Method | Severity |
|-------|------------------|----------|
| **OOM Events** | `journalctl -p err | grep "out of memory"` | Critical |
| **Kernel Errors** | `journalctl -p crit | tail -1` | Critical |
| **Service Restart Loops** | >5 restarts in 100 recent logs | Warning |

### Alert Examples

```
⚠️ System Health Alert:
  - Critical services down: dbus
  - Out of memory condition detected
  - Service restart loop detected (7 restarts)
```

---

## API Endpoints

### `GET /api/status`

Now includes `temperature_status` and `power_status` in the response:

```json
{
  "cpu": { "usage": 15.2, "cores": [12.3, 18.1, 14.0, 16.5], ... },
  "temperature": 52.3,
  "temperature_status": {
    "temp_c": 52.3,
    "level": "normal",
    "message": null,
    "color": "var(--green)"
  },
  "power_status": {
    "available": true,
    "undervoltage_occurred": false,
    "frequency_capped_occurred": false,
    "undervoltage_now": false,
    "frequency_capped_now": false,
    "throttled_now": false
  },
  "memory": { ... },
  "uptime": { ... }
}
```

### `GET /api/system-health`

Returns system health status and critical services status:

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
    { "type": "oom", "severity": "critical", "message": "Out of memory condition detected" }
  ],
  "critical_services_failed": [
    { "name": "dbus", "state": "inactive", "critical": true }
  ],
  "all_critical_ok": false
}
```

---

## Frontend Alert Cards

Three alert cards appear on the Overview tab when conditions warrant:

| Card ID | Color | Trigger |
|---------|-------|---------|
| `#power-alert-card` | Yellow/Orange/Red | Voltage or throttling issues |
| `#temp-alert-card` | Yellow/Orange/Red | Temperature warnings |
| `#health-alert-card` | Red | Service failures or system issues |

All cards clear automatically when conditions normalize.

---

## Configuration

Temperature thresholds are configurable in `sys_monitor.py`:

```python
TEMP_WARNING = 70   # °C - Start warning
TEMP_CRITICAL = 80  # °C - Red alert
TEMP_THROTTLE = 85  # °C - CPU throttles automatically
```

To modify, edit the values in the source file and restart the service.

---

## Testing Alerts

### Simulate Temperature Alert

```bash
# Create a fake high temperature for testing (not recommended on production)
echo "90000" | sudo tee /sys/class/thermal/thermal_zone0/temp
```


---

## Logging

All alert conditions are logged to the in-memory event log:

```
[14:22:01] Temperature alert: CPU at 72°C — consider improving cooling
[14:23:15] System health: Service failed: dbus
```

View with: `/api/logs?limit=100`
