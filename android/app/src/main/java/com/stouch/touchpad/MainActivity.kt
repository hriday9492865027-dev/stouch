package com.stouch.touchpad

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Vibrator
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import com.stouch.touchpad.bluetooth.BluetoothHidService
import com.stouch.touchpad.ui.TouchpadScreen

class MainActivity : ComponentActivity() {

    private lateinit var hidService: BluetoothHidService
    private var vibrator: Vibrator? = null

    private var isConnectedState = mutableStateOf(false)
    private var connectedHostName = mutableStateOf<String?>(null)

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            initBluetoothHid()
        } else {
            Toast.makeText(this, "Bluetooth permissions are required for wireless HID mouse", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        vibrator = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator

        hidService = BluetoothHidService(this) { connected, device ->
            runOnUiThread {
                isConnectedState.value = connected
                connectedHostName.value = device?.name ?: device?.address
            }
        }

        checkAndRequestPermissions()

        setContent {
            val isConnected by isConnectedState
            val deviceName by connectedHostName

            TouchpadScreen(
                hidService = hidService,
                isConnected = isConnected,
                deviceName = deviceName,
                vibrator = vibrator,
                onScanRequested = {
                    val intent = Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
                    startActivity(intent)
                }
            )
        }
    }

    private fun checkAndRequestPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val needed = listOf(
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_ADVERTISE,
                Manifest.permission.BLUETOOTH_SCAN
            ).filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }

            if (needed.isNotEmpty()) {
                permissionLauncher.launch(needed.toTypedArray())
            } else {
                initBluetoothHid()
            }
        } else {
            initBluetoothHid()
        }
    }

    private fun initBluetoothHid() {
        val success = hidService.init()
        if (!success) {
            Toast.makeText(this, "Bluetooth not ready or HID Device role not supported on this phone.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        hidService.destroy()
    }
}

