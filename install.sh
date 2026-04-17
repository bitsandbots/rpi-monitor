#!/usr/bin/env bash
# install.sh — RPiMonitor installer
# Usage:
#   sudo ./install.sh           # Install node agent only
#   sudo ./install.sh --hub     # Install node agent + hub
#   sudo ./install.sh --hub-only  # Install hub only
#   sudo ./install.sh --uninstall  # Remove everything
#
# CoreConduit Consulting Services — MIT License

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
INSTALL_DIR="/opt/rpi-monitor"
NODE_SERVICE="rpi-monitor"
HUB_SERVICE="rpi-monitor-hub"
NODE_PORT=8585
HUB_PORT=8686
PYTHON="${PYTHON:-python3}"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
BLU='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLU}[INFO]${NC}  $*"; }
ok()    { echo -e "${GRN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YLW}[WARN]${NC}  $*"; }
die()   { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

# ── Argument parsing ─────────────────────────────────────────────────────────
INSTALL_NODE=true
INSTALL_HUB=false
DO_UNINSTALL=false

for arg in "$@"; do
  case "$arg" in
    --hub)        INSTALL_HUB=true ;;
    --hub-only)   INSTALL_NODE=false; INSTALL_HUB=true ;;
    --uninstall)  DO_UNINSTALL=true ;;
    --help|-h)
      sed -n '2,10p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) die "Unknown argument: $arg. Use --help for usage." ;;
  esac
done

# ── Preflight ────────────────────────────────────────────────────────────────
preflight() {
  [[ $EUID -eq 0 ]] || die "Run as root: sudo $0 $*"

  command -v "$PYTHON" >/dev/null 2>&1 || die "python3 not found. Install with: apt install python3"
  command -v pip3     >/dev/null 2>&1 || die "pip3 not found. Install with: apt install python3-pip"
  command -v systemctl >/dev/null 2>&1 || die "systemctl not found — systemd required"

  PYVER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  PYMAJ=$(echo "$PYVER" | cut -d. -f1)
  PYMIN=$(echo "$PYVER" | cut -d. -f2)
  if [[ "$PYMAJ" -lt 3 || ("$PYMAJ" -eq 3 && "$PYMIN" -lt 11) ]]; then
    die "Python 3.11+ required, found $PYVER"
  fi

  ok "Preflight passed (Python $PYVER)"
}

# ── Uninstall ────────────────────────────────────────────────────────────────
do_uninstall() {
  info "Uninstalling RPiMonitor..."

  for svc in "$NODE_SERVICE" "$HUB_SERVICE"; do
    if systemctl is-active "$svc" &>/dev/null; then
      systemctl stop "$svc"
      ok "Stopped $svc"
    fi
    if systemctl is-enabled "$svc" &>/dev/null 2>&1; then
      systemctl disable "$svc"
      ok "Disabled $svc"
    fi
    if [[ -f "/etc/systemd/system/${svc}.service" ]]; then
      rm "/etc/systemd/system/${svc}.service"
      ok "Removed /etc/systemd/system/${svc}.service"
    fi
  done

  systemctl daemon-reload

  if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    ok "Removed $INSTALL_DIR"
  fi

  ok "RPiMonitor uninstalled."
}

# ── Install node agent ────────────────────────────────────────────────────────
install_node() {
  info "Installing RPiMonitor node agent → $INSTALL_DIR"

  mkdir -p "$INSTALL_DIR/templates"
  cp rpi_monitor.py "$INSTALL_DIR/"
  cp templates/index.html "$INSTALL_DIR/templates/"
  cp -r static "$INSTALL_DIR/" 2>/dev/null || true
  cp requirements.txt "$INSTALL_DIR/"
  [[ -f .env.example ]] && cp .env.example "$INSTALL_DIR/"

  pip3 install --quiet --break-system-packages -r requirements.txt
  ok "Dependencies installed"

  cp rpi-monitor.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable "$NODE_SERVICE"
  systemctl start  "$NODE_SERVICE"

  # Wait for service to come up
  local retries=10
  while [[ $retries -gt 0 ]]; do
    if curl -sf "http://localhost:${NODE_PORT}/api/ping" >/dev/null 2>&1; then
      ok "Node agent running at http://localhost:${NODE_PORT}"
      return 0
    fi
    retries=$((retries - 1))
    sleep 1
  done
  ok "Service started but health check didn't respond on :${NODE_PORT} — check: journalctl -u $NODE_SERVICE"
}

# ── Install hub ───────────────────────────────────────────────────────────────
install_hub() {
  info "Installing RPiMonitor Hub → $INSTALL_DIR/hub"

  mkdir -p "$INSTALL_DIR/hub/templates"
  cp hub/rpi_monitor_hub.py "$INSTALL_DIR/hub/"
  cp hub/templates/hub.html "$INSTALL_DIR/hub/templates/"
  cp -r static "$INSTALL_DIR/hub/" 2>/dev/null || true
  cp hub/requirements.txt "$INSTALL_DIR/hub/"
  [[ -f hub/HUB_README.md ]] && cp hub/HUB_README.md "$INSTALL_DIR/hub/"

  pip3 install --quiet --break-system-packages -r hub/requirements.txt
  ok "Hub dependencies installed"

  cp hub/rpi-monitor-hub.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable "$HUB_SERVICE"
  systemctl start  "$HUB_SERVICE"

  local retries=10
  while [[ $retries -gt 0 ]]; do
    if curl -sf "http://localhost:${HUB_PORT}/api/ping" >/dev/null 2>&1; then
      ok "Hub running at http://localhost:${HUB_PORT}"
      return 0
    fi
    retries=$((retries - 1))
    sleep 1
  done
  warn "Service started but health check didn't respond on :${HUB_PORT} — check: journalctl -u $HUB_SERVICE"
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo "  RPi|Monitor  Installer"
  echo "  CoreConduit Consulting Services"
  echo ""

  if $DO_UNINSTALL; then
    [[ $EUID -eq 0 ]] || die "Run as root: sudo $0 --uninstall"
    do_uninstall
    exit 0
  fi

  preflight

  $INSTALL_NODE && install_node
  $INSTALL_HUB  && install_hub

  echo ""
  ok "Installation complete."
  $INSTALL_NODE && echo "    Node agent  → http://$(hostname -I | awk '{print $1}'):${NODE_PORT}"
  $INSTALL_HUB  && echo "    Hub         → http://$(hostname -I | awk '{print $1}'):${HUB_PORT}"
  echo ""
}

main "$@"
