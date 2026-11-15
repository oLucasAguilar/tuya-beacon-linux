# Getting the lamp's key without the QR login

Only if `tuya-beacon login` does not work for you.

- This reads the same key (the 16-character localKey) through a free Tuya developer account.
- At the end you run `bin/tuya-beacon derive <localKey>`, after `capture`.
- The portal's menus change over time. Names below are from November 2026.

1. Sign up at https://platform.tuya.com (the old iot.tuya.com may not load).
2. **Cloud > Project Management > Create Cloud Project.**
    - Any name. Leave Industry and Development Method as they are.
    - **Data Center:** the one your app account lives in. Brazil was *Western America*. Wrong data center is the usual reason the lamp does not show up in step 5.
    - On "Authorize API Services", keep the preselected ones (IoT Core is the one that matters) and click Authorize.
3. In the project: **Devices > Link App Account > Add App Account.** A QR code appears.
4. In the Tuya or Smart Life app: **Me > scan icon (top corner)**, scan it and confirm.
5. **Devices > All Devices:** the lamp appears (*Offline* is fine). Copy its **Device ID**.
6. **Cloud > API Explorer > Query Device Details** (the one without "..." at the end), paste the Device ID, **Submit Request**. The response has `local_key`.

Keep the key private: it lets anyone in Bluetooth range control the lamp.
