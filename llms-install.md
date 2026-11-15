# Installing tuya-beacon-linux (instructions for an AI assistant)

You are helping a person control a Bluetooth-only Tuya lamp from their Linux PC.

- Some steps only they can do: the phone app, `sudo`. Do the rest yourself.
- One step at a time. Check each result before the next.
- Talk to them in their language. Start by telling them the path in four lines: capture, QR login, a test command, install.

## 0. Check the machine

- Linux with systemd, `python3 --version` 3.8 or newer.
- A Bluetooth adapter: `ls /sys/class/bluetooth` shows `hci0`. Another `hciN`? Export `TUYA_BEACON_ADAPTER=hciN` for every command below.
- The PC is in the same room as the lamp.
- Ask which phone app the lamp is paired in, and name that app in every later step:
    - **Tuya** (Google Play: *Tuya - Smart Life, Smart Living*, by Tuya Smart Inc.) or **Smart Life**: go on.
    - Another brand app: the QR login may not work. In step 3, use the website route.

If any of these fails, say which and stop.

## 1. Get the code

```bash
git clone https://github.com/oLucasAguilar/tuya-beacon-linux ~/tuya-beacon-linux
cd ~/tuya-beacon-linux && python3 -m unittest discover tests
```

All tests must pass.

## 2. Capture OFF and ON (they act, you watch)

`capture` needs `sudo`, which asks for their password. They run it, in Claude Code with a `!` prefix:

```
! sudo ~/tuya-beacon-linux/bin/tuya-beacon capture
```

- While it listens (60 s), they turn the lamp OFF, then ON, **in the phone app**, phone near the PC.
- Success prints `got OFF` and `got ON`.
- Nothing heard: phone and PC closer to the lamp, retry once.
- Still nothing: the lamp is probably not Beacon Mesh P2. Point them to `docs/alternatives.md` and stop.

## 3. The lamp's key, by QR code (they act)

Tell them why, in two lines: commands are encrypted with the lamp's key, which never goes over the air; `login` reads it once from their account in the app.

They run it in **their own terminal window**: it shows a QR code and waits, and a `!` command may not show it live (not tested).

```
~/tuya-beacon-linux/bin/tuya-beacon login
```

- First time: it offers to install Tuya's official SDK in `~/.cache/tuya-beacon-linux/venv`. They answer `y`.
    - Venv fails on Debian/Ubuntu: `sudo apt install python3-venv`.
- It asks for their **user code**: in the app, Me > Settings > Account and Security > User Code.
- They scan the QR with the same app (Me > scan icon) and confirm.
    - Warn them first: the app may say "Home Assistant". Why: `docs/limits.md`, "By design".
- Success: `The capture matches '<lamp name>'` and `beaconKey recovered and checked on two frames`. The key is saved; nothing else to do here.
- "None of the keys matches the capture": the lamp was paired again after the capture. Redo step 2, then this step.

**QR login fails** (Tuya refuses, or no device comes back with a key): website route.

1. Walk them through `docs/local-key.md`, one numbered step at a time.
2. Run `~/tuya-beacon-linux/bin/tuya-beacon derive <localKey>` yourself.
3. The localKey is a secret: never write it anywhere else, never repeat it back in full, never send it anywhere.

## 4. First real command (they act)

```
! sudo ~/tuya-beacon-linux/bin/tuya-beacon off
```

Ask: did the lamp turn off? Yes: `on` brings it back. No: "Lamp does not react" below.

## 5. Install the daemon and, if they want, the menu

Ask once: "Do you use GNOME and want a lamp menu in the top bar?"

```
! sudo ~/tuya-beacon-linux/install.sh --gnome     # or without --gnome
```

- Then, as their user, without sudo: `lamp color purple`.
- On Wayland the menu appears after logging out and back in.

## 6. Wrap up

Tell them:

- the commands: `lamp on | off | bright N | temp N | white [N] | color <name|hue>`
- re-pairing the lamp in the app means repeating steps 2 and 3
- wrong brightness or colour on their model: `docs/limits.md`, "Different lamp?"

## Lamp does not react

1. `sudo ~/tuya-beacon-linux/bin/tuya-beacon sniff` while they use the app. It decodes the app's commands? Then the keys are right.
2. ON/OFF work, brightness or colour do not: the DP numbers differ. Compare `sniff` with `tuyabeacon/lamp.py` and adjust `DP_*`.
3. Nothing at all: move the PC closer. Then open an issue with the product id (app: device, edit, device information) and what `sniff` shows, without the keys.
