package com.stouch.touchpad.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.util.Log
import java.util.concurrent.Executors

/**
 * Manages the native Android BluetoothHidDevice peripheral role (PRD Mode B).
 * Allows the phone to register as a genuine physical Bluetooth mouse for Windows.
 */
@SuppressLint("MissingPermission")
class BluetoothHidService(
    private val context: Context,
    private val onConnectionStateChanged: (Boolean, BluetoothDevice?) -> Unit
) {
    companion object {
        private const val TAG = "BluetoothHidService"
    }

    private val bluetoothAdapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    private var hidDevice: BluetoothHidDevice? = null
    var connectedHost: BluetoothDevice? = null
        private set

    var isRegistered = false
        private set

    private val serviceListener = object : BluetoothProfile.ServiceListener {
        override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
            if (profile == BluetoothProfile.HID_DEVICE) {
                Log.d(TAG, "Bluetooth HID Device profile proxy connected.")
                hidDevice = proxy as BluetoothHidDevice
                registerHidApp()
            }
        }

        override fun onServiceDisconnected(profile: Int) {
            if (profile == BluetoothProfile.HID_DEVICE) {
                Log.d(TAG, "Bluetooth HID Device profile proxy disconnected.")
                hidDevice = null
                isRegistered = false
                connectedHost = null
                onConnectionStateChanged(false, null)
            }
        }
    }

    private val hidCallback = object : BluetoothHidDevice.Callback() {
        override fun onAppStatusChanged(pluggedDevice: BluetoothDevice?, registered: Boolean) {
            super.onAppStatusChanged(pluggedDevice, registered)
            isRegistered = registered
            Log.d(TAG, "HID App registration status: $registered")
        }

        override fun onConnectionStateChanged(device: BluetoothDevice?, state: Int) {
            super.onConnectionStateChanged(device, state)
            when (state) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.d(TAG, "Connected to host: ${device?.name} (${device?.address})")
                    connectedHost = device
                    onConnectionStateChanged(true, device)
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d(TAG, "Disconnected from host: ${device?.name}")
                    if (connectedHost == device) {
                        connectedHost = null
                    }
                    onConnectionStateChanged(false, device)
                }
            }
        }
    }

    fun init(): Boolean {
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled) {
            Log.e(TAG, "Bluetooth adapter not enabled.")
            return false
        }
        return bluetoothAdapter.getProfileProxy(context, serviceListener, BluetoothProfile.HID_DEVICE)
    }

    private fun registerHidApp() {
        val sdp = BluetoothHidDeviceAppSdpSettings(
            "Digital Touchpad",
            "Wireless Touchpad Peripheral",
            "STouch",
            BluetoothHidDeviceAppSdpSettings.SUBCLASS1_COMBO,
            HidConsts.MOUSE_REPORT_DESCRIPTOR
        )

        hidDevice?.registerApp(
            sdp,
            null,
            null,
            Executors.newSingleThreadExecutor(),
            hidCallback
        )
    }

    fun sendMouseReport(dx: Int, dy: Int, buttons: Byte = HidConsts.BUTTON_NONE, wheel: Int = 0) {
        val host = connectedHost ?: return
        val device = hidDevice ?: return

        val clampedDx = dx.coerceIn(-127, 127).toByte()
        val clampedDy = dy.coerceIn(-127, 127).toByte()
        val clampedWheel = wheel.coerceIn(-127, 127).toByte()

        val report = byteArrayOf(buttons, clampedDx, clampedDy, clampedWheel)
        device.sendReport(host, HidConsts.MOUSE_REPORT_ID.toInt(), report)
    }

    fun releaseAll() {
        // Send report with zero buttons pressed
        sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
    }

    fun destroy() {
        releaseAll()
        if (hidDevice != null && isRegistered) {
            hidDevice?.unregisterApp()
        }
        if (bluetoothAdapter != null && hidDevice != null) {
            bluetoothAdapter.closeProfileProxy(BluetoothProfile.HID_DEVICE, hidDevice)
        }
        hidDevice = null
        connectedHost = null
    }
}

