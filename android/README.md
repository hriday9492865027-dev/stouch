# Digital Touchpad - Native Android Bluetooth HID Module (PRD Mode B)

This native Android module turns your smartphone into a **hardware-recognized Bluetooth mouse** for Windows using Android's native `BluetoothHidDevice` API (API 28+).

### Key Features
* **Zero PC Software Required:** Windows natively pairs with your phone as a standard Bluetooth mouse.
* **USB-IF Standard Mouse Descriptor:** Emulates Left, Right, Middle clicks, relative $(dx, dy)$ pointer movement, and scroll wheel.
* **Jetpack Compose UI:** Touch surface matching the Web PWA design with haptic feedback.
* **Release-All Watchdog:** Automatically releases buttons on disconnect or backgrounding.

### Building and Running
1. Open this folder (`STouch/android`) in **Android Studio**.
2. Connect your Android phone with Developer Options & USB Debugging enabled.
3. Click **Run** (`Shift + F10`) to deploy the app to your phone.
4. On your Windows PC, go to **Settings &rarr; Bluetooth & devices &rarr; Add device**.
5. Select your phone to pair. Windows will now accept mouse inputs directly from your phone's screen!

