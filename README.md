# Digital Touchpad (v2.0)

Turn any smartphone (Android or iOS) into a wireless touchpad and control surface for your Windows laptop or desktop via a high-performance **Progressive Web App (PWA)** and **Windows Companion Receiver**.

Based on the [Digital Touchpad PRD v2.0](Digital_Touchpad_PRD_Windows_v2_0.pdf).

---

## Highlights

* **Multi-Connection Architecture:**
  * **Wi-Fi / Local Network Mode (Mode A):** High-frequency WebSocket input via PWA.
  * **Direct Bluetooth Tethering / PAN (Zero Wi-Fi):** Connect over Bluetooth network without needing a router or internet.
  * **Native Bluetooth HID Peripheral (Mode B):** Standalone native Android module using `BluetoothHidDevice` that turns your phone into a driverless hardware Bluetooth mouse for Windows (no PC software needed).
* **Zero App Store Installs (PWA Mode):** Open the URL on your mobile browser (Chrome/Safari) and tap **"Add to Home Screen"** to run it as a standalone, fullscreen PWA.
* **120Hz Low Latency:** High-frequency touch processing using `PointerEvents` with coalescing over local WebSocket connections.
* **Full Multi-Touch Gesture Engine:**
  * **1-Finger Move:** Smooth relative cursor navigation with acceleration ballistics.
  * **1-Finger Tap:** Primary Left Click (with $\le 10$px deadzone to eliminate jitter).
  * **Double Tap:** Double Click.
  * **Tap-and-Hold Drag:** Hold $\ge 350$ms to engage drag $\to$ move to drag $\to$ lift to release.
  * **2-Finger Tap:** Secondary Right Click (Context Menu).
  * **2-Finger Drag:** Smooth vertical and horizontal wheel scrolling (configurable natural direction).
  * **3-Finger Swipes:** Swipe Up for Task View (`Win+Tab`), Swipe Down for Desktop (`Win+D`), Swipe Left/Right for App Switch (`Alt+Tab`).
  * **Pinch-to-Zoom:** Zoom in/out via `Ctrl + Wheel`.
* **Hardware & System Safety:**
  * **Watchdog Release-All:** If the connection drops or the browser tab closes, all held mouse buttons and keys are automatically released immediately (P0 safety requirement IN-008 & AT-009).
  * **Strict Allowlist:** Arbitrary commands and scripts are strictly rejected.
  * **Power Action Guardrails:** Sleep, Restart, and Shutdown require confirmation with a 10-second cancellable countdown.
* **Mobile Enhancements:**
  * **Screen Wake Lock:** Prevents the mobile screen from sleeping while using the touchpad.
  * **Haptic Feedback:** Subtle vibration pulses on clicks, drag locks, and gestures.

---

## Architecture Overview

```
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│     Mobile Phone / Tablet       │               │        Windows PC Host          │
│   (Standalone PWA Client)       │               │      (Companion Receiver)       │
│                                 │               │                                 │
│  ┌───────────────────────────┐  │  WebSocket    │  ┌───────────────────────────┐  │
│  │ Touch Surface & Gestures  │──┼───(/ws)───────┼─>│ Input Dispatcher          │  │
│  │ - 1-Finger / 2-Finger     │  │  Low Latency  │  │ - Win32 SendInput         │  │
│  │ - Tap-Hold Drag           │  │               │  │ - Release-All Watchdog    │  │
│  └───────────────────────────┘  │               │  └─────────────┬─────────────┘  │
│  ┌───────────────────────────┐  │               │                ▼                │
│  │ Quick Actions Dock        │──┼───────────────┼─>┌───────────────────────────┐  │
│  │ - Volume / Media / Apps   │  │               │  │ Action Handler (Allowlist)│  │
│  │ - 10s Power Countdown     │  │               │  └─────────────┬─────────────┘  │
│  └───────────────────────────┘  │               │                ▼                │
│  ┌───────────────────────────┐  │  HTTP Static  │  ┌───────────────────────────┐  │
│  │ Offline Service Worker    │<─┼───(Port 8000)─┼──│ Embedded Web Server       │  │
│  └───────────────────────────┘  │               │  └───────────────────────────┘  │
└─────────────────────────────────┘               └─────────────────────────────────┘
```

---

## Project Structure

```
STouch/
├── client/                      # Modern PWA Client
│   ├── index.html               # Main Touchpad UI & Docks (PRD Fig 2)
│   ├── manifest.json            # PWA Web App Manifest
│   ├── sw.js                    # Service Worker (Offline caching)
│   ├── css/
│   │   └── style.css            # Dark-theme responsive styling
│   ├── js/
│   │   ├── app.js               # UI coordination, WakeLock, PWA
│   │   ├── gesture-engine.js    # Multi-touch state machine & ballistics
│   │   ├── protocol.js          # Versioned JSON envelopes & heartbeats
│   │   └── quick-actions.js     # Allowlisted shortcuts & power modals
│   └── icons/                   # 192x192 and 512x512 app icons
├── server/                      # Windows Companion Receiver
│   ├── app.py                   # FastAPI + Uvicorn server (HTTP + WebSocket)
│   ├── input_dispatcher.py      # Win32 SendInput (ctypes / user32.dll)
│   ├── action_handler.py        # Allowlisted system shortcuts & media
│   ├── pairing.py               # Local LAN IP detection & PIN helper
│   └── requirements.txt         # Server dependencies
├── tests/                       # Automated Acceptance Tests
│   ├── test_input.py            # Unit tests for SendInput & allowlists
│   └── test_protocol.py         # Protocol envelope tests
├── start_receiver.bat           # 1-Click launcher for Windows
├── start_receiver.ps1           # PowerShell launcher
└── README.md                    # Documentation
```

---

## Getting Started

### 1. Requirements
* Windows 10 (22H2+) or Windows 11
* Python 3.10+ (with `fastapi`, `uvicorn`, `pywin32`)

### 2. Start the Windows Companion Receiver
Double-click `start_receiver.bat` or run:

```powershell
python server\app.py
```

The receiver will print:
```
============================================================
   DIGITAL TOUCHPAD - WINDOWS RECEIVER (v2.0)
============================================================
 * Local Server URL:  http://192.168.1.XX:8000/
 * Pairing PIN:       123456
 * Status:            Ready for phone connection

 Open your phone camera or browser and navigate to:
 >>> http://192.168.1.XX:8000/
============================================================
```

### 3. Connect from Your Phone
1. Ensure your phone is connected to the same Wi-Fi network (or phone hotspot).
2. Open Chrome (Android) or Safari (iOS) and go to the printed URL (e.g. `http://192.168.1.XX:8000`).
3. Tap **"Add to Home Screen"** or **"Install App"** to install it as a standalone PWA.
4. Use your phone as a trackpad!

---

## Running the Acceptance Tests

Verify that mouse input injection, bounded coordinates, and allowlist security pass:

```powershell
python tests/test_input.py
python tests/test_protocol.py
```

