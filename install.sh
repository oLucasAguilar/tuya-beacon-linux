#!/bin/bash
# Installs the lampd service and the `lamp` command for the user who runs it with sudo.
#   sudo ./install.sh            daemon + lamp command
#   sudo ./install.sh --gnome    also the GNOME top-bar menu
set -euo pipefail

if [ "$(id -u)" -ne 0 ] || [ -z "${SUDO_USER:-}" ]; then
    echo "Run it with sudo from your own user: sudo ./install.sh" >&2
    exit 1
fi
ROOT="$(cd "$(dirname "$0")" && pwd)"
USER_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"

sed -e "s|@USER@|$SUDO_USER|g" -e "s|@ROOT@|$ROOT|g" \
    "$ROOT/systemd/lampd.service" > /etc/systemd/system/lampd.service
systemctl daemon-reload
systemctl enable lampd
systemctl restart lampd

sudo -u "$SUDO_USER" mkdir -p "$USER_HOME/.local/bin"
sudo -u "$SUDO_USER" ln -sf "$ROOT/bin/lamp" "$USER_HOME/.local/bin/lamp"
echo "lampd is running; 'lamp' is in ~/.local/bin."

if [ "${1:-}" = "--gnome" ]; then
    EXT="$USER_HOME/.local/share/gnome-shell/extensions/tuya-beacon@tuya-beacon-linux"
    sudo -u "$SUDO_USER" mkdir -p "$(dirname "$EXT")"
    sudo -u "$SUDO_USER" ln -sfn "$ROOT/gnome/tuya-beacon@tuya-beacon-linux" "$EXT"
    sudo -u "$SUDO_USER" gnome-extensions enable tuya-beacon@tuya-beacon-linux 2>/dev/null \
        || echo "Log out and back in, then: gnome-extensions enable tuya-beacon@tuya-beacon-linux"
    echo "GNOME menu installed. On Wayland it shows up after you log out and back in."
fi
