package com.stouch.touchpad

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothProfile
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.util.Log
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import java.util.concurrent.Executors

@SuppressLint("MissingPermission", "ClickableViewAccessibility")
class TouchpadActivity : Activity() {

    companion object {
        private const val TAG = "STouch"
        private const val PERMISSION_REQUEST_CODE = 1001

        // USB-IF Standard HID Mouse Report Descriptor
        // Report ID 1: Buttons(1) + dX(1) + dY(1) + Wheel(1) = 4 bytes
        private val MOUSE_REPORT_DESCRIPTOR = byteArrayOf(
            0x05.toByte(), 0x01.toByte(), // Usage Page (Generic Desktop)
            0x09.toByte(), 0x02.toByte(), // Usage (Mouse)
            0xA1.toByte(), 0x01.toByte(), // Collection (Application)
            0x85.toByte(), 0x01.toByte(), //   Report ID (1)
            0x09.toByte(), 0x01.toByte(), //   Usage (Pointer)
            0xA1.toByte(), 0x00.toByte(), //   Collection (Physical)
            // 3 Buttons (Left, Right, Middle)
            0x05.toByte(), 0x09.toByte(), //     Usage Page (Buttons)
            0x19.toByte(), 0x01.toByte(), //     Usage Minimum (1)
            0x29.toByte(), 0x03.toByte(), //     Usage Maximum (3)
            0x15.toByte(), 0x00.toByte(), //     Logical Minimum (0)
            0x25.toByte(), 0x01.toByte(), //     Logical Maximum (1)
            0x95.toByte(), 0x03.toByte(), //     Report Count (3)
            0x75.toByte(), 0x01.toByte(), //     Report Size (1)
            0x81.toByte(), 0x02.toByte(), //     Input (Data, Variable, Absolute)
            // 5 Bits Padding
            0x95.toByte(), 0x01.toByte(), //     Report Count (1)
            0x75.toByte(), 0x05.toByte(), //     Report Size (5)
            0x81.toByte(), 0x03.toByte(), //     Input (Constant)
            // X, Y relative movement
            0x05.toByte(), 0x01.toByte(), //     Usage Page (Generic Desktop)
            0x09.toByte(), 0x30.toByte(), //     Usage (X)
            0x09.toByte(), 0x31.toByte(), //     Usage (Y)
            0x15.toByte(), 0x81.toByte(), //     Logical Minimum (-127)
            0x25.toByte(), 0x7F.toByte(), //     Logical Maximum (127)
            0x75.toByte(), 0x08.toByte(), //     Report Size (8)
            0x95.toByte(), 0x02.toByte(), //     Report Count (2)
            0x81.toByte(), 0x06.toByte(), //     Input (Data, Variable, Relative)
            // Wheel
            0x09.toByte(), 0x38.toByte(), //     Usage (Wheel)
            0x15.toByte(), 0x81.toByte(), //     Logical Minimum (-127)
            0x25.toByte(), 0x7F.toByte(), //     Logical Maximum (127)
            0x75.toByte(), 0x08.toByte(), //     Report Size (8)
            0x95.toByte(), 0x01.toByte(), //     Report Count (1)
            0x81.toByte(), 0x06.toByte(), //     Input (Data, Variable, Relative)
            0xC0.toByte(),                //   End Collection
            0xC0.toByte()                 // End Collection
        )

        private const val BUTTON_NONE: Byte = 0x00
        private const val BUTTON_LEFT: Byte = 0x01
        private const val BUTTON_RIGHT: Byte = 0x02
    }

    private var bluetoothAdapter: BluetoothAdapter? = null
    private var hidDevice: BluetoothHidDevice? = null
    private var connectedHost: BluetoothDevice? = null
    private var isRegistered = false
    private var vibrator: Vibrator? = null

    // UI
    private lateinit var statusDot: View
    private lateinit var statusText: TextView
    private lateinit var btnPairPC: Button
    private lateinit var touchpadSurface: View
    private lateinit var touchpadHint: TextView
    private lateinit var btnLeftClick: Button
    private lateinit var btnRightClick: Button

    // Touch tracking
    private var lastTouchX = 0f
    private var lastTouchY = 0f
    private var isTouchDown = false
    private var touchStartTime = 0L
    private var touchMoved = false

    // Two-finger scroll
    private var twoFingerActive = false
    private var lastTwoFingerY = 0f

    // BroadcastReceiver for Bluetooth bonding events
    private val bluetoothReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            if (BluetoothDevice.ACTION_BOND_STATE_CHANGED == action) {
                val device = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                }
                val bondState = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, BluetoothDevice.BOND_NONE)
                if (bondState == BluetoothDevice.BOND_BONDED && device != null) {
                    Log.d(TAG, "Device bonded: ${device.name}. Initiating HID connection...")
                    runOnUiThread {
                        Toast.makeText(this@TouchpadActivity, "Paired with ${device.name}! Connecting...", Toast.LENGTH_SHORT).show()
                    }
                    connectToHost(device)
                }
            }
        }
    }

    // ---- Bluetooth HID Callbacks ----

    private val serviceListener = object : BluetoothProfile.ServiceListener {
        override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
            if (profile == BluetoothProfile.HID_DEVICE) {
                Log.d(TAG, "HID Device profile proxy connected")
                hidDevice = proxy as BluetoothHidDevice
                registerHidApp()
            }
        }

        override fun onServiceDisconnected(profile: Int) {
            if (profile == BluetoothProfile.HID_DEVICE) {
                Log.d(TAG, "HID Device profile proxy disconnected")
                hidDevice = null
                isRegistered = false
                connectedHost = null
                runOnUiThread { updateUI(false, null) }
            }
        }
    }

    private val hidCallback = object : BluetoothHidDevice.Callback() {
        override fun onAppStatusChanged(pluggedDevice: BluetoothDevice?, registered: Boolean) {
            super.onAppStatusChanged(pluggedDevice, registered)
            isRegistered = registered
            Log.d(TAG, "HID App registration: $registered, pluggedDevice: ${pluggedDevice?.name}")
            if (registered) {
                runOnUiThread {
                    Toast.makeText(this@TouchpadActivity, "✓ Bluetooth HID Mouse ready", Toast.LENGTH_SHORT).show()
                }
                // If there's already a plugged device or paired device, try to connect
                if (pluggedDevice != null) {
                    connectToHost(pluggedDevice)
                } else {
                    autoConnectPairedHost()
                }
            }
        }

        override fun onConnectionStateChanged(device: BluetoothDevice?, state: Int) {
            super.onConnectionStateChanged(device, state)
            when (state) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.d(TAG, "Connected to: ${device?.name} (${device?.address})")
                    connectedHost = device
                    runOnUiThread {
                        Toast.makeText(this@TouchpadActivity, "Connected to ${device?.name ?: "PC"}!", Toast.LENGTH_SHORT).show()
                        updateUI(true, device)
                    }
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d(TAG, "Disconnected from: ${device?.name}")
                    if (connectedHost == device) connectedHost = null
                    runOnUiThread { updateUI(false, null) }
                }
                BluetoothProfile.STATE_CONNECTING -> {
                    runOnUiThread {
                        statusText.text = "Connecting to ${device?.name ?: "PC"}..."
                    }
                }
            }
        }

        override fun onGetReport(device: BluetoothDevice?, type: Byte, id: Byte, bufferSize: Int) {
            super.onGetReport(device, type, id, bufferSize)
            if (device != null) {
                if (type == BluetoothHidDevice.REPORT_TYPE_INPUT && id == 1.toByte()) {
                    hidDevice?.replyReport(device, type, id, byteArrayOf(0, 0, 0, 0))
                } else {
                    hidDevice?.reportError(device, BluetoothHidDevice.ERROR_RSP_UNSUPPORTED_REQ)
                }
            }
        }

        override fun onSetReport(device: BluetoothDevice?, type: Byte, id: Byte, data: ByteArray?) {
            super.onSetReport(device, type, id, data)
            if (device != null) {
                hidDevice?.reportError(device, BluetoothHidDevice.ERROR_RSP_SUCCESS)
            }
        }

        override fun onSetProtocol(device: BluetoothDevice?, protocol: Byte) {
            super.onSetProtocol(device, protocol)
            Log.d(TAG, "onSetProtocol: $protocol")
        }
    }

    // ---- Lifecycle ----

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_touchpad)

        vibrator = getSystemService(VIBRATOR_SERVICE) as? Vibrator
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()

        // Bind UI
        statusDot = findViewById(R.id.statusDot)
        statusText = findViewById(R.id.statusText)
        btnPairPC = findViewById(R.id.btnPairPC)
        touchpadSurface = findViewById(R.id.touchpadSurface)
        touchpadHint = findViewById(R.id.touchpadHint)
        btnLeftClick = findViewById(R.id.btnLeftClick)
        btnRightClick = findViewById(R.id.btnRightClick)

        btnPairPC.setOnClickListener {
            handleConnectButtonClick()
        }

        btnLeftClick.setOnClickListener {
            vibrate(15)
            sendMouseReport(0, 0, BUTTON_LEFT, 0)
            sendMouseReport(0, 0, BUTTON_NONE, 0)
        }

        btnRightClick.setOnClickListener {
            vibrate(20)
            sendMouseReport(0, 0, BUTTON_RIGHT, 0)
            sendMouseReport(0, 0, BUTTON_NONE, 0)
        }

        setupTouchpad()
        registerReceiver(bluetoothReceiver, IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED))
        checkAndRequestPermissions()
    }

    private fun handleConnectButtonClick() {
        if (connectedHost != null) {
            // Already connected -> Disconnect
            hidDevice?.disconnect(connectedHost)
            connectedHost = null
            updateUI(false, null)
            return
        }

        val bonded = bluetoothAdapter?.bondedDevices?.toList() ?: emptyList()
        if (bonded.isEmpty()) {
            Toast.makeText(this, "No paired PC found. Please pair with Windows first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS))
            return
        }

        // Show paired devices dialog
        val deviceNames = bonded.map { it.name ?: it.address }.toTypedArray()
        val options = deviceNames + "➕ Pair New Device..."

        AlertDialog.Builder(this)
            .setTitle("Select your PC to Connect")
            .setItems(options) { _, which ->
                if (which < bonded.size) {
                    val target = bonded[which]
                    connectToHost(target)
                } else {
                    startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS))
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun connectToHost(device: BluetoothDevice) {
        val hid = hidDevice
        if (hid == null) {
            Toast.makeText(this, "Bluetooth HID not ready yet. Please wait.", Toast.LENGTH_SHORT).show()
            return
        }
        statusText.text = "Connecting to ${device.name}..."
        val initiated = hid.connect(device)
        Log.d(TAG, "hid.connect(${device.name}) initiated: $initiated")
        if (!initiated) {
            Toast.makeText(this, "Connecting to ${device.name}...", Toast.LENGTH_SHORT).show()
        }
    }

    private fun autoConnectPairedHost() {
        val bonded = bluetoothAdapter?.bondedDevices ?: return
        for (device in bonded) {
            val name = (device.name ?: "").uppercase()
            // Look for typical computer names
            if (name.contains("DESKTOP") || name.contains("LAPTOP") || name.contains("PC") || name.contains("WINDOWS")) {
                Log.d(TAG, "Auto-connecting to paired PC: ${device.name}")
                connectToHost(device)
                break
            }
        }
    }

    private fun setupTouchpad() {
        touchpadSurface.setOnTouchListener { _, event ->
            when (event.actionMasked) {

                MotionEvent.ACTION_DOWN -> {
                    lastTouchX = event.x
                    lastTouchY = event.y
                    isTouchDown = true
                    touchStartTime = System.currentTimeMillis()
                    touchMoved = false
                    twoFingerActive = false
                    true
                }

                MotionEvent.ACTION_POINTER_DOWN -> {
                    if (event.pointerCount == 2) {
                        twoFingerActive = true
                        lastTwoFingerY = (event.getY(0) + event.getY(1)) / 2f
                    }
                    true
                }

                MotionEvent.ACTION_MOVE -> {
                    if (twoFingerActive && event.pointerCount >= 2) {
                        // Two-finger scroll
                        val avgY = (event.getY(0) + event.getY(1)) / 2f
                        val scrollDelta = (lastTwoFingerY - avgY) * 0.35f
                        val wheel = scrollDelta.toInt().coerceIn(-127, 127)
                        if (wheel != 0) {
                            sendMouseReport(0, 0, BUTTON_NONE, wheel)
                        }
                        lastTwoFingerY = avgY
                    } else if (event.pointerCount == 1) {
                        // Single-finger cursor movement
                        val dx = ((event.x - lastTouchX) * 1.5f).toInt()
                        val dy = ((event.y - lastTouchY) * 1.5f).toInt()
                        if (dx != 0 || dy != 0) {
                            touchMoved = true
                            sendMouseReport(dx, dy, BUTTON_NONE, 0)
                        }
                        lastTouchX = event.x
                        lastTouchY = event.y
                    }
                    true
                }

                MotionEvent.ACTION_POINTER_UP -> {
                    if (twoFingerActive && event.pointerCount <= 2) {
                        // Two-finger tap = Right Click
                        val elapsed = System.currentTimeMillis() - touchStartTime
                        if (elapsed < 300 && !touchMoved) {
                            vibrate(20)
                            sendMouseReport(0, 0, BUTTON_RIGHT, 0)
                            sendMouseReport(0, 0, BUTTON_NONE, 0)
                        }
                        twoFingerActive = false
                    }
                    true
                }

                MotionEvent.ACTION_UP -> {
                    val elapsed = System.currentTimeMillis() - touchStartTime
                    if (!touchMoved && !twoFingerActive && elapsed < 250) {
                        // Single tap = Left Click
                        vibrate(15)
                        sendMouseReport(0, 0, BUTTON_LEFT, 0)
                        sendMouseReport(0, 0, BUTTON_NONE, 0)
                    }
                    isTouchDown = false
                    twoFingerActive = false
                    true
                }

                MotionEvent.ACTION_CANCEL -> {
                    isTouchDown = false
                    twoFingerActive = false
                    true
                }

                else -> false
            }
        }
    }

    // ---- Bluetooth Init ----

    private fun checkAndRequestPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val needed = arrayOf(
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_ADVERTISE,
                Manifest.permission.BLUETOOTH_SCAN
            ).filter {
                checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
            }
            if (needed.isNotEmpty()) {
                requestPermissions(needed.toTypedArray(), PERMISSION_REQUEST_CODE)
            } else {
                initBluetoothHid()
            }
        } else {
            initBluetoothHid()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                initBluetoothHid()
            } else {
                Toast.makeText(this, "Bluetooth permissions are required", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun initBluetoothHid() {
        val adapter = bluetoothAdapter
        if (adapter == null || !adapter.isEnabled) {
            Toast.makeText(this, "Please enable Bluetooth first", Toast.LENGTH_LONG).show()
            return
        }
        val success = adapter.getProfileProxy(this, serviceListener, BluetoothProfile.HID_DEVICE)
        if (!success) {
            Toast.makeText(this, "Bluetooth HID Device role is not supported on this phone", Toast.LENGTH_LONG).show()
        }
    }

    private fun registerHidApp() {
        val sdp = BluetoothHidDeviceAppSdpSettings(
            "Digital Touchpad",
            "Wireless Touchpad Peripheral",
            "STouch",
            BluetoothHidDevice.SUBCLASS1_MOUSE,
            MOUSE_REPORT_DESCRIPTOR
        )
        hidDevice?.registerApp(sdp, null, null, Executors.newSingleThreadExecutor(), hidCallback)
    }

    // ---- Mouse Reports ----

    private fun sendMouseReport(dx: Int, dy: Int, buttons: Byte, wheel: Int) {
        val host = connectedHost ?: return
        val device = hidDevice ?: return
        val report = byteArrayOf(
            buttons,
            dx.coerceIn(-127, 127).toByte(),
            dy.coerceIn(-127, 127).toByte(),
            wheel.coerceIn(-127, 127).toByte()
        )
        device.sendReport(host, 1, report)
    }

    // ---- UI Updates ----

    private fun updateUI(connected: Boolean, device: BluetoothDevice?) {
        if (connected) {
            statusDot.setBackgroundResource(R.drawable.status_dot_green)
            statusText.text = device?.name ?: device?.address ?: "Connected"
            btnPairPC.text = "Disconnect"
            btnPairPC.visibility = View.VISIBLE
            touchpadHint.text = "Touchpad Active — glide finger to move cursor"
        } else {
            statusDot.setBackgroundResource(R.drawable.status_dot_red)
            statusText.text = "Not Connected (Bluetooth)"
            btnPairPC.text = "Connect PC"
            btnPairPC.visibility = View.VISIBLE
            touchpadHint.text = "Tap 'Connect PC' above to connect to your PC"
        }
    }

    // ---- Haptics ----

    private fun vibrate(ms: Long) {
        vibrator?.let {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                it.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                it.vibrate(ms)
            }
        }
    }

    // ---- Cleanup ----

    override fun onDestroy() {
        super.onDestroy()
        try {
            unregisterReceiver(bluetoothReceiver)
        } catch (_: Exception) {}
        sendMouseReport(0, 0, BUTTON_NONE, 0)
        hidDevice?.let {
            if (isRegistered) it.unregisterApp()
            bluetoothAdapter?.closeProfileProxy(BluetoothProfile.HID_DEVICE, it)
        }
    }
}
