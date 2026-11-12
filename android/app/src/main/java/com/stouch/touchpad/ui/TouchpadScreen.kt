package com.stouch.touchpad.ui

import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.stouch.touchpad.bluetooth.BluetoothHidService
import com.stouch.touchpad.bluetooth.HidConsts

@Composable
fun TouchpadScreen(
    hidService: BluetoothHidService,
    isConnected: Boolean,
    deviceName: String?,
    vibrator: Vibrator?,
    onScanRequested: () -> Unit
) {
    val bgPrimary = Color(0xFF0F172A)
    val bgSecondary = Color(0xFF1E293B)
    val accentCyan = Color(0xFF38BDF8)
    val accentGreen = Color(0xFF10B981)
    val accentRed = Color(0xFFEF4444)

    fun vibrate(ms: Long = 15) {
        vibrator?.let {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                it.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                it.vibrate(ms)
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(bgPrimary)
            .padding(16.dp)
    ) {
        // Status Bar
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = bgSecondary),
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(
                                color = if (isConnected) accentGreen else accentRed,
                                shape = androidx.compose.foundation.shape.CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isConnected) (deviceName ?: "Connected Host") else "Not Connected (Bluetooth)",
                        color = Color.White,
                        fontSize = 14.sp
                    )
                }

                if (!isConnected) {
                    Button(
                        onClick = onScanRequested,
                        colors = ButtonDefaults.buttonColors(containerColor = accentCyan),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
                    ) {
                        Text("Pair PC", color = bgPrimary, fontSize = 12.sp)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Main Touch Surface
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(Color(0xFF131D33), shape = RoundedCornerShape(16.dp))
                .pointerInput(isConnected) {
                    if (!isConnected) return@pointerInput
                    detectTransformGestures { _, pan, _, _ ->
                        val dx = (pan.x * 1.5f).toInt()
                        val dy = (pan.y * 1.5f).toInt()
                        hidService.sendMouseReport(dx, dy, HidConsts.BUTTON_NONE, 0)
                    }
                }
                .pointerInput(isConnected) {
                    if (!isConnected) return@pointerInput
                    detectTapGestures(
                        onTap = {
                            vibrate(15)
                            // Left Click
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_LEFT, 0)
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
                        },
                        onDoubleTap = {
                            vibrate(25)
                            // Double Click
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_LEFT, 0)
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_LEFT, 0)
                            hidService.sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
                        }
                    )
                },
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = if (isConnected) "Touchpad Active" else "Pair Windows in Bluetooth Settings",
                    color = Color(0xFF64748B),
                    fontSize = 14.sp
                )
                Text(
                    text = "Tap: Left Click • Double Tap: Open",
                    color = Color(0xFF475569),
                    fontSize = 11.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Explicit Physical Buttons
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = {
                    vibrate(15)
                    hidService.sendMouseReport(0, 0, HidConsts.BUTTON_LEFT, 0)
                    hidService.sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
                },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = bgSecondary)
            ) {
                Text("Left Click", color = Color.White)
            }

            Button(
                onClick = {
                    vibrate(20)
                    hidService.sendMouseReport(0, 0, HidConsts.BUTTON_RIGHT, 0)
                    hidService.sendMouseReport(0, 0, HidConsts.BUTTON_NONE, 0)
                },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = bgSecondary)
            ) {
                Text("Right Click", color = Color.White)
            }
        }
    }
}

