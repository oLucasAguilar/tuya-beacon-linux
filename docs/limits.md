# Limits

## Tested on one lamp

| | |
|---|---|
| Lamp | Tuya "dj" light, product `heflj0rj`, module "8003 pwmRGBCW", Beacon Mesh P2 |
| Phone app | Tuya (Tuya Smart Inc.) |
| PC | Ubuntu 24.04, kernel 7.0, Intel AX211 Bluetooth (`hci0`) |
| Desktop | GNOME Shell 46 (Wayland). The extension declares 45 to 48; only 46 was tried. |
| Python | 3.12 |

**Different lamp?**

- On/off is the same across P2 lights.
- Brightness and colour may use other DP numbers. To find them:
    1. `sudo bin/tuya-beacon sniff`, and use the app while it listens.
    2. Change the `DP_*` numbers at the top of `tuyabeacon/lamp.py`.
- Worked or not? Open an issue with the product id: it helps the next person.

## By design

- **Bluetooth range.** Same room worked; through walls was not tested.
- **One-way.** The lamp never answers. The menu shows the last command sent, not the real state: the wall switch or the app can change the lamp without the menu knowing.
- **One lamp.** One lamp per setup for now.
    - Each lamp's files already live apart (`lamps/<name>/`), so a second one is interface work: [issue #1](https://github.com/oLucasAguilar/tuya-beacon-linux/issues/1).
- **Root once.** `install.sh` gives `CAP_NET_RAW` and `CAP_NET_ADMIN` to the `lampd` service only. `lamp` and the menu run as you.
- **Re-pairing changes the key.** Pair the lamp again in the app, and repeat `capture` and `login`.
- **The cloud, once.** `login` reads the lamp's key from your app account. After that, everything is local.
- **"Home Assistant" on the phone.** Tuya only offers QR login to registered apps.
    - `login` borrows the registration of Home Assistant's Tuya integration, like other community tools do.
    - It only reads the key, and saves no login on your PC.
    - If Tuya ever blocks it, the website route still works: [local-key.md](local-key.md).
- **QR login was tested on one account.** Another tool (tuya-local-key) says Bluetooth-only devices come back without a key. Ours came back with it. If yours does not, use the website route.

## Not tested

- Group addresses (one command to several lamps at once): the protocol has them, this code does not send them.
- Other Bluetooth adapters, other distributions, X11.
- Other software advertising over BlueZ at the same time.
