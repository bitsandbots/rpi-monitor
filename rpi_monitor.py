#!/usr/bin/env python3
"""
RPiMonitor — Raspberry Pi System Monitor & Service Control Console
A lightweight Flask-based dashboard for monitoring and managing Raspberry Pi
and Linux devices. Reads live data from /proc, /sys, and systemctl.

CoreConduit Consulting Services — https://coreconduit.io
License: MIT
"""

import json
import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)

VERSION = "2.0.0"

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════
CONFIG = {
    "host": os.getenv("PIMONITOR_HOST", "0.0.0.0"),
    "port": int(os.getenv("PIMONITOR_PORT", "8585")),
    "debug": os.getenv("PIMONITOR_DEBUG", "false").lower() == "true",
    "auth_token": os.getenv("PIMONITOR_TOKEN", ""),
    "services": [
        s.strip()
        for s in os.getenv(
            "PIMONITOR_SERVICES",
            "ssh,nginx,docker,ollama,mosquitto,chromadb,nodered,grafana-server,cron,avahi-daemon",
        ).split(",")
        if s.strip()
    ],
    "refresh_interval": int(os.getenv("PIMONITOR_REFRESH", "2")),
}

# ═══════════════════════════════════════════════════════════════════════════
# Service List Persistence
# ═══════════════════════════════════════════════════════════════════════════
_SERVICES_FILE = Path(
    os.getenv(
        "PIMONITOR_SERVICES_FILE",
        str(Path(__file__).parent / "services.json"),
    )
)


def _load_services():
    """Load the persisted service list, falling back to CONFIG defaults."""
    if _SERVICES_FILE.exists():
        try:
            data = json.loads(_SERVICES_FILE.read_text())
            if isinstance(data, list) and all(isinstance(s, str) for s in data):
                CONFIG["services"] = [s.strip() for s in data if s.strip()]
                return
        except (json.JSONDecodeError, OSError):
            pass


def _save_services():
    """Persist the current service list to disk."""
    try:
        _SERVICES_FILE.write_text(json.dumps(CONFIG["services"], indent=2) + "\n")
    except OSError as e:
        log_event(f"Failed to save services config: {e}", "error")


# Load persisted services on import (works under WSGI and __main__)
_load_services()

# ═══════════════════════════════════════════════════════════════════════════
# Boot-time Pi Detection (runs once at startup)
# ═══════════════════════════════════════════════════════════════════════════
_BOOT_INFO = {}


def detect_pi():
    """Detect hardware at startup and cache the result."""
    global _BOOT_INFO
    model = _read_file("/proc/device-tree/model", "").rstrip("\x00")
    revision = ""
    serial = ""
    hardware = ""

    for line in _read_file("/proc/cpuinfo").splitlines():
        if line.startswith("Revision"):
            revision = line.split(":")[-1].strip()
        elif line.startswith("Serial"):
            serial = line.split(":")[-1].strip()
        elif line.startswith("Hardware"):
            hardware = line.split(":")[-1].strip()
        elif line.startswith("Model"):
            model = model or line.split(":")[-1].strip()

    is_pi = bool(model and ("raspberry" in model.lower() or "bcm" in hardware.lower()))

    # SoC detection from revision code
    soc_map = {
        "0": "BCM2835",
        "1": "BCM2836",
        "2": "BCM2837",
        "3": "BCM2711",
        "4": "BCM2712",
    }
    soc = ""
    if len(revision) >= 6:
        try:
            proc_id = str((int(revision, 16) >> 12) & 0xF)
            soc = soc_map.get(proc_id, f"BCM_unknown({proc_id})")
        except ValueError:
            pass

    # GPU memory (Pi-specific)
    gpu_mem = _run("vcgencmd get_mem gpu 2>/dev/null | grep -oP '\\d+'")

    # System identity
    kernel = _run("uname -r")
    arch = _run("uname -m")
    hostname = _run("hostname")
    os_name = _run("lsb_release -ds 2>/dev/null")
    if not os_name:
        for line in _read_file("/etc/os-release").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[-1].strip('"')
                break

    # CPU info
    cpu_model = ""
    for line in _read_file("/proc/cpuinfo").splitlines():
        if "model name" in line.lower():
            cpu_model = line.split(":")[-1].strip()
            break
    cpu_max_freq = _read_file(
        "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", ""
    )
    if cpu_max_freq:
        cpu_max_freq = f"{int(cpu_max_freq) // 1000} MHz"

    python_ver = _run("python3 --version 2>&1 | awk '{print $2}'")

    _BOOT_INFO = {
        "is_raspberry_pi": is_pi,
        "model": model or "Generic Linux",
        "revision": revision,
        "serial": serial[-8:] if serial else "",
        "hardware": hardware,
        "soc": soc,
        "gpu_mb": int(gpu_mem) if gpu_mem else None,
        "hostname": hostname,
        "kernel": kernel,
        "architecture": arch,
        "os": os_name or "Unknown",
        "cpu_model": cpu_model,
        "cpu_max_freq": cpu_max_freq,
        "python": python_ver,
        "boot_time": datetime.now().isoformat(timespec="seconds"),
    }
    return _BOOT_INFO


# ═══════════════════════════════════════════════════════════════════════════
# Auth Middleware
# ═══════════════════════════════════════════════════════════════════════════
def require_auth(f):
    """Optional bearer-token authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = CONFIG["auth_token"]
        if token:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                abort(401, description="Unauthorized")
        return f(*args, **kwargs)

    return decorated


# ═══════════════════════════════════════════════════════════════════════════
# Low-level Helpers
# ═══════════════════════════════════════════════════════════════════════════
def _read_file(path: str, default: str = "") -> str:
    """Safely read a system file."""
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return default


def _run(cmd: str, timeout: int = 5) -> str:
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# CPU — Differential Sampling
# ═══════════════════════════════════════════════════════════════════════════
_cpu_prev = {"total": {}, "per_core": {}}


def _parse_proc_stat():
    """Parse /proc/stat into per-cpu dicts of {user, nice, system, idle, ...}."""
    result = {}
    for line in _read_file("/proc/stat").splitlines():
        if not line.startswith("cpu"):
            continue
        parts = line.split()
        name = parts[0]  # 'cpu' or 'cpu0', 'cpu1', ...
        vals = [int(v) for v in parts[1:]]
        # user, nice, system, idle, iowait, irq, softirq, steal
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals)
        result[name] = {"idle": idle, "total": total}
    return result


def get_cpu_usage() -> dict:
    """CPU usage via differential /proc/stat sampling."""
    global _cpu_prev
    current = _parse_proc_stat()

    def calc_pct(name):
        prev = _cpu_prev.get(name)
        cur = current.get(name)
        if not prev or not cur:
            return 0.0
        d_total = cur["total"] - prev["total"]
        d_idle = cur["idle"] - prev["idle"]
        if d_total <= 0:
            return 0.0
        return round((1.0 - d_idle / d_total) * 100, 1)

    usage = calc_pct("cpu")
    cores = []
    i = 0
    while f"cpu{i}" in current:
        cores.append(calc_pct(f"cpu{i}"))
        i += 1

    _cpu_prev = current

    # Load averages
    load_parts = _read_file("/proc/loadavg").split()
    load_avg = [float(x) for x in load_parts[:3]] if len(load_parts) >= 3 else [0, 0, 0]

    # Current frequency
    cur_freq = _read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "")
    freq_mhz = int(cur_freq) // 1000 if cur_freq else None

    return {
        "usage": usage,
        "cores": cores,
        "core_count": len(cores) or 1,
        "load_avg": load_avg,
        "freq_mhz": freq_mhz,
    }


def get_cpu_temperature() -> float:
    """CPU temperature in °C."""
    temp_str = _read_file("/sys/class/thermal/thermal_zone0/temp", "0")
    try:
        return round(int(temp_str) / 1000.0, 1)
    except ValueError:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Memory
# ═══════════════════════════════════════════════════════════════════════════
def get_memory() -> dict:
    """Memory stats from /proc/meminfo."""
    info = {}
    for line in _read_file("/proc/meminfo").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            info[parts[0].rstrip(":")] = int(parts[1])

    total = info.get("MemTotal", 0)
    free = info.get("MemFree", 0)
    available = info.get("MemAvailable", 0)
    buffers = info.get("Buffers", 0)
    cached = info.get("Cached", 0)
    used = total - free - buffers - cached

    swap_total = info.get("SwapTotal", 0)
    swap_free = info.get("SwapFree", 0)

    return {
        "total_mb": round(total / 1024, 1),
        "used_mb": round(max(used, 0) / 1024, 1),
        "free_mb": round(free / 1024, 1),
        "available_mb": round(available / 1024, 1),
        "cached_mb": round(cached / 1024, 1),
        "buffers_mb": round(buffers / 1024, 1),
        "swap_total_mb": round(swap_total / 1024, 1),
        "swap_used_mb": round((swap_total - swap_free) / 1024, 1),
        "gpu_mb": _BOOT_INFO.get("gpu_mb"),
        "percent": round(max(used, 0) / total * 100, 1) if total > 0 else 0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Storage
# ═══════════════════════════════════════════════════════════════════════════
def get_storage() -> list:
    """Mounted filesystem usage via df."""
    output = _run(
        "df -BM --output=source,target,size,used,avail,pcent,fstype "
        "-x devtmpfs -x squashfs -x overlay -x tmpfs 2>/dev/null"
    )
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 7 and not parts[1].startswith("/snap"):
            devices.append(
                {
                    "device": parts[0],
                    "mount": parts[1],
                    "total_mb": int(parts[2].rstrip("M")),
                    "used_mb": int(parts[3].rstrip("M")),
                    "avail_mb": int(parts[4].rstrip("M")),
                    "percent": int(parts[5].rstrip("%")),
                    "fstype": parts[6],
                }
            )
    return devices


# ═══════════════════════════════════════════════════════════════════════════
# Network — Rate Tracking
# ═══════════════════════════════════════════════════════════════════════════
_net_lock = threading.Lock()
_net_prev = {}
_net_prev_time = 0.0


def get_network() -> dict:
    """Network interfaces with throughput rates (bytes/sec)."""
    global _net_prev, _net_prev_time
    now = time.time()

    interfaces = []
    rates = {}

    net_path = Path("/sys/class/net")
    if not net_path.exists():
        return {"interfaces": [], "rates": {}}

    with _net_lock:
        elapsed = now - _net_prev_time if _net_prev_time > 0 else 1.0
        _net_prev_time = now

        for iface_dir in sorted(net_path.iterdir()):
            name = iface_dir.name
            if name == "lo":
                continue

            state = _read_file(f"/sys/class/net/{name}/operstate", "unknown")
            mac = _read_file(f"/sys/class/net/{name}/address", "—")
            ip_out = _run(
                f"ip -4 addr show {name} 2>/dev/null | grep -oP 'inet \\K[\\d.]+'"
            )
            rx = int(_read_file(f"/sys/class/net/{name}/statistics/rx_bytes", "0"))
            tx = int(_read_file(f"/sys/class/net/{name}/statistics/tx_bytes", "0"))

            prev = _net_prev.get(name, {"rx": rx, "tx": tx})
            rx_rate = max(0, round((rx - prev["rx"]) / elapsed)) if elapsed > 0 else 0
            tx_rate = max(0, round((tx - prev["tx"]) / elapsed)) if elapsed > 0 else 0
            _net_prev[name] = {"rx": rx, "tx": tx}

            interfaces.append(
                {
                    "name": name,
                    "state": state,
                    "mac": mac,
                    "ip": ip_out or "—",
                    "rx_bytes": rx,
                    "tx_bytes": tx,
                    "rx_mb": round(rx / (1024 * 1024), 2),
                    "tx_mb": round(tx / (1024 * 1024), 2),
                }
            )
            rates[name] = {"rx_rate": rx_rate, "tx_rate": tx_rate}

    return {"interfaces": interfaces, "rates": rates}


# ═══════════════════════════════════════════════════════════════════════════
# Processes
# ═══════════════════════════════════════════════════════════════════════════
def get_top_processes(limit: int = 12) -> list:
    """Top processes by CPU usage."""
    output = _run(f"ps aux --sort=-%cpu | head -n {limit + 1}")
    processes = []
    for line in output.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            processes.append(
                {
                    "user": parts[0],
                    "pid": int(parts[1]),
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "command": parts[10][:140],
                }
            )
    return processes


def kill_process(pid: int, sig: int = 15) -> dict:
    """Send a signal to a process. Default SIGTERM (15), or SIGKILL (9)."""
    if pid <= 1:
        return {"success": False, "error": "Refusing to signal PID <= 1"}
    allowed_signals = {9, 15}
    if sig not in allowed_signals:
        return {"success": False, "error": f"Signal {sig} not allowed"}
    try:
        os.kill(pid, sig)
        return {"success": True, "pid": pid, "signal": sig}
    except ProcessLookupError:
        return {"success": False, "error": f"PID {pid} not found"}
    except PermissionError:
        # Fall back to sudo kill
        result = subprocess.run(
            ["sudo", "kill", f"-{sig}", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            "success": result.returncode == 0,
            "pid": pid,
            "signal": sig,
            "stderr": result.stderr.strip(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Uptime
# ═══════════════════════════════════════════════════════════════════════════
def get_uptime() -> dict:
    """System uptime."""
    raw = _read_file("/proc/uptime")
    if raw:
        seconds = int(float(raw.split()[0]))
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        m = (seconds % 3600) // 60
        return {
            "seconds": seconds,
            "formatted": f"{d}d {h}h {m}m",
            "days": d,
            "hours": h,
            "minutes": m,
        }
    return {"seconds": 0, "formatted": "unknown", "days": 0, "hours": 0, "minutes": 0}


# ═══════════════════════════════════════════════════════════════════════════
# Service Management
# ═══════════════════════════════════════════════════════════════════════════
def get_services() -> list:
    """Get status of configured services."""
    services = []
    for svc in CONFIG["services"]:
        active_raw = _run(f"systemctl is-active {svc} 2>/dev/null")
        enabled_raw = _run(f"systemctl is-enabled {svc} 2>/dev/null")
        desc = _run(f"systemctl show {svc} --property=Description --value 2>/dev/null")
        services.append(
            {
                "name": svc,
                "active": active_raw == "active",
                "active_state": active_raw or "unknown",
                "enabled": enabled_raw == "enabled",
                "enabled_state": enabled_raw or "unknown",
                "description": desc or svc,
            }
        )
    return services


def control_service(name: str, action: str) -> dict:
    """Control a systemd service."""
    if name not in CONFIG["services"]:
        return {"success": False, "error": f"Service '{name}' not in allowed list"}

    valid_actions = {"start", "stop", "restart", "enable", "disable"}
    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action: {action}"}

    try:
        result = subprocess.run(
            ["sudo", "systemctl", action, name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "service": name,
            "action": action,
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout: systemctl {action} {name}"}


# ═══════════════════════════════════════════════════════════════════════════
# Power Controls
# ═══════════════════════════════════════════════════════════════════════════
def system_power(action: str) -> dict:
    """Reboot or shutdown."""
    if action == "reboot":
        subprocess.Popen(
            ["sudo", "reboot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return {"success": True, "action": "reboot"}
    elif action == "shutdown":
        subprocess.Popen(
            ["sudo", "shutdown", "-h", "now"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"success": True, "action": "shutdown"}
    return {"success": False, "error": "Invalid power action"}


# ═══════════════════════════════════════════════════════════════════════════
# Event Log (in-memory ring buffer)
# ═══════════════════════════════════════════════════════════════════════════
_log_lock = threading.Lock()
_event_log = []
LOG_MAX = 200


def log_event(msg: str, level: str = "info"):
    """Append an event to the in-memory log."""
    with _log_lock:
        _event_log.append(
            {
                "ts": datetime.now().strftime("%H:%M:%S"),
                "msg": msg,
                "level": level,
            }
        )
        if len(_event_log) > LOG_MAX:
            del _event_log[: len(_event_log) - LOG_MAX]


def get_log(limit: int = 100) -> list:
    with _log_lock:
        return list(_event_log[-limit:])


# ═══════════════════════════════════════════════════════════════════════════
# API Routes
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html", config=CONFIG, boot=_BOOT_INFO)


@app.route("/api/ping")
def api_ping():
    """Health check for connection-lost detection."""
    return jsonify({"ok": True, "ts": time.time()})


@app.route("/api/boot")
@require_auth
def api_boot():
    """Static boot-time hardware detection info."""
    return jsonify(_BOOT_INFO)


@app.route("/api/status")
@require_auth
def api_status():
    """Primary polling endpoint — fast-changing metrics."""
    net = get_network()
    return jsonify(
        {
            "cpu": get_cpu_usage(),
            "temperature": get_cpu_temperature(),
            "memory": get_memory(),
            "uptime": get_uptime(),
            "network_rates": net["rates"],
            "timestamp": time.time(),
        }
    )


@app.route("/api/storage")
@require_auth
def api_storage():
    return jsonify(get_storage())


@app.route("/api/network")
@require_auth
def api_network():
    return jsonify(get_network())


@app.route("/api/processes")
@require_auth
def api_processes():
    limit = request.args.get("limit", 12, type=int)
    return jsonify(get_top_processes(limit=min(limit, 50)))


@app.route("/api/processes/<int:pid>", methods=["DELETE"])
@require_auth
def api_kill_process(pid):
    sig = request.args.get("signal", 15, type=int)
    result = kill_process(pid, sig)
    if result["success"]:
        log_event(f"Killed PID {pid} (signal {sig})", "warning")
    return jsonify(result), 200 if result["success"] else 400


@app.route("/api/services")
@require_auth
def api_services():
    return jsonify(get_services())


@app.route("/api/services/<name>/<action>", methods=["POST"])
@require_auth
def api_service_control(name, action):
    result = control_service(name, action)
    level = "success" if result["success"] else "error"
    log_event(
        f"Service {action}: {name} — {'OK' if result['success'] else result.get('error','failed')}",
        level,
    )
    return jsonify(result), 200 if result["success"] else 400


# ── Service List CRUD ──
@app.route("/api/services/config", methods=["GET"])
@require_auth
def api_services_config():
    """Return the raw list of configured service names."""
    return jsonify(CONFIG["services"])


@app.route("/api/services/config", methods=["POST"])
@require_auth
def api_services_add():
    """Add a service to the monitored list."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Service name required"}), 400
    if not re.match(r"^[a-zA-Z0-9@._:-]+$", name):
        return jsonify({"success": False, "error": "Invalid service name"}), 400
    if name in CONFIG["services"]:
        return jsonify({"success": False, "error": f"'{name}' already monitored"}), 409
    CONFIG["services"].append(name)
    _save_services()
    log_event(f"Service added to monitor list: {name}", "success")
    return (
        jsonify({"success": True, "service": name, "services": CONFIG["services"]}),
        201,
    )


@app.route("/api/services/config/<svc>", methods=["DELETE"])
@require_auth
def api_services_remove(svc):
    """Remove a service from the monitored list."""
    if svc not in CONFIG["services"]:
        return jsonify({"success": False, "error": f"'{svc}' not in list"}), 404
    CONFIG["services"].remove(svc)
    _save_services()
    log_event(f"Service removed from monitor list: {svc}", "warning")
    return jsonify({"success": True, "service": svc, "services": CONFIG["services"]})


@app.route("/api/services/config/<svc>", methods=["PUT"])
@require_auth
def api_services_rename(svc):
    """Rename/replace a service entry in the monitored list."""
    data = request.get_json(silent=True) or {}
    new_name = data.get("name", "").strip()
    if not new_name:
        return jsonify({"success": False, "error": "New name required"}), 400
    if not re.match(r"^[a-zA-Z0-9@._:-]+$", new_name):
        return jsonify({"success": False, "error": "Invalid service name"}), 400
    if svc not in CONFIG["services"]:
        return jsonify({"success": False, "error": f"'{svc}' not in list"}), 404
    if new_name in CONFIG["services"]:
        return jsonify({"success": False, "error": f"'{new_name}' already exists"}), 409
    idx = CONFIG["services"].index(svc)
    CONFIG["services"][idx] = new_name
    _save_services()
    log_event(f"Service renamed: {svc} -> {new_name}", "success")
    return jsonify(
        {"success": True, "old": svc, "new": new_name, "services": CONFIG["services"]}
    )


@app.route("/api/power/<action>", methods=["POST"])
@require_auth
def api_power(action):
    if action not in ("reboot", "shutdown"):
        return jsonify({"success": False, "error": "Invalid action"}), 400
    log_event(f"Power: {action} initiated", "warning")
    result = system_power(action)
    return jsonify(result)


@app.route("/api/logs")
@require_auth
def api_logs():
    limit = request.args.get("limit", 100, type=int)
    return jsonify(get_log(limit))


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    info = detect_pi()

    # Seed the CPU differential sampler
    _parse_proc_stat()
    time.sleep(0.1)

    log_event("RPiMonitor starting...")
    log_event(f"Detected: {info['model']}")
    if info["soc"]:
        log_event(f"SoC: {info['soc']} | Arch: {info['architecture']}")
    log_event(f"Hostname: {info['hostname']} | Kernel: {info['kernel']}")
    log_event(f"Services configured: {len(CONFIG['services'])}")
    log_event(f"Listening on http://{CONFIG['host']}:{CONFIG['port']}")
    log_event("RPiMonitor ready.", "success")

    marker = "PI" if info["is_raspberry_pi"] else "LINUX"

    print(f"""
\033[36m╔══════════════════════════════════════════════════╗
║   RPi\033[33mMonitor\033[36m · v2.0.0                              ║
║   CoreConduit Consulting Services                 ║
╠══════════════════════════════════════════════════╣\033[0m
  Device:   {info['model']} [{marker}]
  SoC:      {info.get('soc') or '—'}
  Kernel:   {info['kernel']}
  Auth:     {'ENABLED' if CONFIG['auth_token'] else 'DISABLED'}
  Services: {len(CONFIG['services'])} configured
  Listen:   http://{CONFIG['host']}:{CONFIG['port']}
\033[36m╚══════════════════════════════════════════════════╝\033[0m
""")

    app.run(host=CONFIG["host"], port=CONFIG["port"], debug=CONFIG["debug"])
