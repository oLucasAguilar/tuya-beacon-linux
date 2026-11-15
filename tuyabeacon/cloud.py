"""Read the lamp's localKey from your Smart Life / Tuya account by QR code.

Uses Tuya's official tuya-device-sharing-sdk (MIT), the same login the Home
Assistant Tuya integration uses. Tuya only offers this QR login to registered
apps, so we use Home Assistant's public registration, as other community tools
do. Nothing is stored: the session ends when this function returns.
"""
import sys
import time

CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
SCHEMA = "haauthorize"


def account_keys(user_code, wait_seconds=240):
    """Show a QR code, wait for the app to scan it, return [(name, category, local_key)]."""
    import qrcode
    from tuya_sharing import LoginControl, Manager

    login = LoginControl()
    reply = login.qr_code(CLIENT_ID, SCHEMA, user_code)
    if not reply.get("success"):
        raise SystemExit(f"Tuya refused the user code ({reply.get('msg') or reply.get('code')}). "
                         "Check it in the app: Me > Settings > Account and Security > User Code.")
    token = reply["result"]["qrcode"]
    code = qrcode.QRCode(border=1)
    code.add_data(f"tuyaSmart--qrLogin?token={token}")
    code.print_ascii(out=sys.stdout, invert=True)
    print("Scan it with the same app where the lamp is paired (Tuya or Smart Life):")
    print("Me > scan icon (top corner), then confirm. The app may say 'Home Assistant':")
    print("this tool borrows Home Assistant's Tuya login. This code only reads the key and saves no login on this PC.",
          flush=True)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        ok, info = login.login_result(token, CLIENT_ID, user_code)
        if ok:
            break
        time.sleep(3)
    else:
        raise SystemExit("The QR code was not scanned in time. Run it again.")

    manager = Manager(CLIENT_ID, user_code, info["terminal_id"], info["endpoint"], info)
    manager.update_device_cache()
    return [(device.name, device.category, device.local_key)
            for device in manager.device_map.values()
            if len(getattr(device, "local_key", "") or "") in (16, 32)]
