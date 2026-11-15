# The protocol, and the byte that blocks everyone

Bluetooth-only Tuya lights in the "Beacon Mesh P2" family never connect to anything.

- The phone app puts a 26-byte frame inside a BLE advertisement.
- Every bulb in range hears it; the one it is addressed to obeys.
- Nothing comes back.

## The advertisement

```
02 01 06            Flags element        <- required, see below
1b 03 <26 bytes>    the P2 frame, as a "16-bit service UUID list"
```

31 bytes, the maximum for a legacy advertisement.

**Without the Flags element the lamp ignores the command.**

- The frame can be byte-for-byte what the phone sends, right keys and sequence, and nothing happens. We lost a night to this.
- The reference write-up of the protocol does not include it.
- We found it reading the sending code of [SunsetLampHATuyaBridge](https://github.com/FinnGrndl/SunsetLampHATuyaBridge) (`expected_on_air_advertisement`).

## The frame

Byte layout: the docstring of [`tuyabeacon/p2.py`](../tuyabeacon/p2.py). In short:

- header, source, destination node, sequence, sub-command, CRC of the plaintext
- 16 bytes: the DP payload encrypted with XXTEA under the **localKey**, then XORed with the **beaconKey**
- CRC of the whole thing

**Why the beaconKey needs no cloud.** It is a plain XOR mask.

- One real frame with a known plaintext, plus the localKey, gives it back.
- Known plaintexts: ON is `01 11 01`, OFF is `01 11 00`.
- `derive` (and `login`) recover it from both and accept it only if the two agree.

**Sequence.** It must keep increasing per source address. We send from `0x8001`, so the phone app keeps its own counter and the two never collide.

## DP map (tested lamp)

| DP | type | meaning |
|---|---|---|
| 1 | bool | power |
| 2 | enum | 0 white, 1 colour |
| 3 | value 10..1000 | brightness in white mode |
| 4 | value 0..1000 | white temperature, warm to cold |
| 11 | raw: H (2 bytes), S, V | colour; V is the brightness in colour mode |

Other products may differ: [limits.md, "Different lamp?"](limits.md#tested-on-one-lamp).

## Further reading

- [universal_proxy's protocol notes](https://github.com/bbangert/universal_proxy/blob/main/docs/protocols/tuya_beacon_mesh.md): the most complete write-up of Tuya Beacon and Beacon Mesh, reverse-engineered from the app.
- [tuya-iotos-beacon-sdk-ak80x](https://github.com/tuya/tuya-iotos-beacon-sdk-ak80x): Tuya's SDK for the older, single-device Beacon flavour.
