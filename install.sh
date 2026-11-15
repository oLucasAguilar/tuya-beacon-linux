#!/bin/bash
# Installs the lampd service and the `lamp` command for the user who runs it with sudo.
#   sudo ./install.sh            daemon + lamp command
#   sudo ./install.sh --gnome    also the GNOME top-bar menu
# The code is copied to /opt/tuya-beacon-linux, owned by root, because lampd runs it with
# CAP_NET_RAW: code the user can edit must not run with that. After changing the code
# here, run this again.
set -euo pipefail

if [ "$(id -u)" -ne 0 ] || [ -z "${SUDO_USER:-}" ]; then
    echo "Run it with sudo from your own user: sudo ./install.sh" >&2
    exit 1
fi
SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT=/opt/tuya-beacon-linux
USER_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"

# A symlink in the clone would make /opt point back at files the user can edit.
LINKS="$(find "$SRC/bin" "$SRC/tuyabeacon" "$SRC/gnome" -type l)"
if [ -n "$LINKS" ]; then
    echo "Refusing to install: symlinks in the source, which lampd would run with privilege:" >&2
    echo "$LINKS" >&2
    exit 1
fi

if [ -d "$ROOT" ]; then
    rm -r --one-file-system "$ROOT"
fi
install -d -m 755 -o root -g root "$ROOT"
cp -r "$SRC/bin" "$SRC/tuyabeacon" "$SRC/gnome" "$ROOT/"
find "$ROOT" -name __pycache__ -prune -exec rm -r {} +
chown -R root:root "$ROOT"
chmod -R u=rwX,go=rX "$ROOT"

sed -e "s|@USER@|$SUDO_USER|g" -e "s|@ROOT@|$ROOT|g" \
    "$SRC/systemd/lampd.service" > /etc/systemd/system/lampd.service
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
