# Credits

- **[SunsetLampHATuyaBridge](https://github.com/FinnGrndl/SunsetLampHATuyaBridge)** (MIT): reading its sender is how we learned that the advertisement needs the Flags element, and that the beaconKey can be recovered from two real commands instead of the cloud. No code copied.
- **[universal_proxy](https://github.com/bbangert/universal_proxy)**: its protocol notes are the best description of Tuya Beacon Mesh P2 we found. We used them to understand the frame; no code or text from it is in this repository.
- **[beacon-cooked](https://github.com/MadeinTaly/beacon-cooked)** (MIT): the XXTEA and CRC routines in `tuyabeacon/crypto.py` and the HCI `Radio` in `tuyabeacon/radio.py` are adapted from it. Its license:

```
MIT License

Copyright (c) 2026 MadeinTaly

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
