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
    # `gnome-extensions enable` fails silently for an extension the running shell has not
    # loaded yet, so add it to the enabled list directly; the shell reads it at next login.
    sudo -u "$SUDO_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$SUDO_UID/bus" python3 - <<'PY'
import ast, subprocess
key = ["gsettings", "get", "org.gnome.shell", "enabled-extensions"]
now = ast.literal_eval(subprocess.run(key, capture_output=True, text=True, check=True).stdout.replace("@as ", ""))
if "tuya-beacon@tuya-beacon-linux" not in now:
    now.append("tuya-beacon@tuya-beacon-linux")
    subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", str(now)], check=True)
PY
    echo "GNOME menu installed. On Wayland it shows up after you log out and back in."
fi
