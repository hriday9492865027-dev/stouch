"""
Win32 SendInput Dispatcher for Digital Touchpad (PRD v2.0 Section 10 & 12)
Directly interfaces with user32.dll for sub-millisecond mouse and keyboard simulation.
Includes mandatory Release-All safety watchdog (IN-008, AT-009).
"""

import ctypes
from ctypes import wintypes
import time
import threading

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

WHEEL_DELTA = 120

# Ctypes Struct Definitions for 64-bit Windows
ULONG_PTR = ctypes.c_ulonglong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("_u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_u", _INPUT_UNION),
    ]

user32 = ctypes.windll.user32
SendInput = user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


class InputDispatcher:
    def __init__(self):
        self._lock = threading.Lock()
        # Active held state tracking for release safety (AT-009)
        self.held_mouse_buttons = set()  # e.g. {'left', 'right'}
        self.held_keys = set()           # e.g. {0x11, 0x12}

    def _send_inputs(self, inputs):
        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        with self._lock:
            res = SendInput(n, arr, ctypes.sizeof(INPUT))
            return res == n

    def move_pointer(self, dx: int, dy: int):
        """Relative pointer movement with bounds checking."""
        # Clamp extreme values to prevent runaway pointer flood
        dx = max(-500, min(500, int(dx)))
        dy = max(-500, min(500, int(dy)))
        if dx == 0 and dy == 0:
            return

        inp = INPUT(type=INPUT_MOUSE)
        inp.mi.dx = dx
        inp.mi.dy = dy
        inp.mi.mouseData = 0
        inp.mi.dwFlags = MOUSEEVENTF_MOVE
        inp.mi.time = 0
        inp.mi.dwExtraInfo = 0
        self._send_inputs([inp])

    def set_button_state(self, button: str, state: str):
        """Handle button down, up, click, or double click."""
        button = button.lower()
        state = state.lower()

        flag_map = {
            'left': (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
            'right': (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
            'middle': (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)
        }

        if button not in flag_map:
            return

        down_flag, up_flag = flag_map[button]

        if state == 'down':
            inp = INPUT(type=INPUT_MOUSE)
            inp.mi.dwFlags = down_flag
            self._send_inputs([inp])
            self.held_mouse_buttons.add(button)

        elif state == 'up':
            inp = INPUT(type=INPUT_MOUSE)
            inp.mi.dwFlags = up_flag
            self._send_inputs([inp])
            self.held_mouse_buttons.discard(button)

        elif state == 'click':
            inp_down = INPUT(type=INPUT_MOUSE)
            inp_down.mi.dwFlags = down_flag
            inp_up = INPUT(type=INPUT_MOUSE)
            inp_up.mi.dwFlags = up_flag
            self._send_inputs([inp_down, inp_up])
            self.held_mouse_buttons.discard(button)

        elif state == 'double_click':
            inp1_down = INPUT(type=INPUT_MOUSE)
            inp1_down.mi.dwFlags = down_flag
            inp1_up = INPUT(type=INPUT_MOUSE)
            inp1_up.mi.dwFlags = up_flag

            inp2_down = INPUT(type=INPUT_MOUSE)
            inp2_down.mi.dwFlags = down_flag
            inp2_up = INPUT(type=INPUT_MOUSE)
            inp2_up.mi.dwFlags = up_flag

            self._send_inputs([inp1_down, inp1_up])
            time.sleep(0.04)
            self._send_inputs([inp2_down, inp2_up])
            self.held_mouse_buttons.discard(button)

    def scroll(self, dx: int, dy: int):
        """Vertical and horizontal wheel scrolling."""
        inputs = []
        if dy != 0:
            inp_v = INPUT(type=INPUT_MOUSE)
            inp_v.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp_v.mi.mouseData = int(dy * (WHEEL_DELTA / 6))
            inputs.append(inp_v)

        if dx != 0:
            inp_h = INPUT(type=INPUT_MOUSE)
            inp_h.mi.dwFlags = MOUSEEVENTF_HWHEEL
            inp_h.mi.mouseData = int(dx * (WHEEL_DELTA / 6))
            inputs.append(inp_h)

        if inputs:
            self._send_inputs(inputs)

    def send_key_combination(self, vk_codes):
        """Press and release a combination of virtual key codes in order."""
        press_inputs = []
        release_inputs = []

        for vk in vk_codes:
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki.wVk = vk
            inp_down.ki.dwFlags = KEYEVENTF_EXTENDEDKEY if vk in (0x5B, 0x5C) else 0
            press_inputs.append(inp_down)

        for vk in reversed(vk_codes):
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki.wVk = vk
            inp_up.ki.dwFlags = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if vk in (0x5B, 0x5C) else 0)
            release_inputs.append(inp_up)

        self._send_inputs(press_inputs)
        time.sleep(0.02)
        self._send_inputs(release_inputs)

    def release_all(self):
        """Safety release for all held buttons and keys (AT-009)."""
        inputs = []
        for btn in list(self.held_mouse_buttons):
            if btn == 'left':
                inp = INPUT(type=INPUT_MOUSE)
                inp.mi.dwFlags = MOUSEEVENTF_LEFTUP
                inputs.append(inp)
            elif btn == 'right':
                inp = INPUT(type=INPUT_MOUSE)
                inp.mi.dwFlags = MOUSEEVENTF_RIGHTUP
                inputs.append(inp)
            elif btn == 'middle':
                inp = INPUT(type=INPUT_MOUSE)
                inp.mi.dwFlags = MOUSEEVENTF_MIDDLEUP
                inputs.append(inp)
        self.held_mouse_buttons.clear()

        for vk in list(self.held_keys):
            inp = INPUT(type=INPUT_KEYBOARD)
            inp.ki.wVk = vk
            inp.ki.dwFlags = KEYEVENTF_KEYUP
            inputs.append(inp)
        self.held_keys.clear()

        if inputs:
            self._send_inputs(inputs)
            print(f"[InputDispatcher] Released all held inputs ({len(inputs)} items).")

