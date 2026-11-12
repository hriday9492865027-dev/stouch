"""
Allowlisted Action and Shortcut Handler (PRD v2.0 Section 09 & 13)
Executes strictly allowlisted system shortcuts, media commands, presenter deck,
brightness adjustments, and guarded power actions.
Rejects any arbitrary command strings or paths.
"""

import ctypes
import subprocess
import time
from input_dispatcher import InputDispatcher

# Virtual Key Codes
VK_LWIN = 0x5B
VK_TAB = 0x09
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21  # Page Up
VK_NEXT = 0x22   # Page Down
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_S = 0x53
VK_D = 0x44
VK_E = 0x45
VK_B = 0x42
VK_F = 0x46
VK_F5 = 0x74

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

user32 = ctypes.windll.user32

class ActionHandler:
    def __init__(self, input_dispatcher: InputDispatcher):
        self.dispatcher = input_dispatcher
        self.current_brightness = 70

    def adjust_brightness(self, delta: int) -> int:
        self.current_brightness = max(10, min(100, self.current_brightness + delta))
        try:
            cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {self.current_brightness})"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=2)
        except Exception as e:
            print(f"[ActionHandler] Brightness WMI notice: {e}")
        return self.current_brightness

    def handle_action(self, action_id: str, params: dict = None) -> dict:
        """Execute allowlisted actions only. Return status dict."""
        params = params or {}
        action_id = (action_id or '').lower().strip()

        # 1. Desktop & System Shortcuts
        if action_id == 'task_view':
            self.dispatcher.send_key_combination([VK_LWIN, VK_TAB])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'show_desktop':
            self.dispatcher.send_key_combination([VK_LWIN, VK_D])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'app_switch':
            self.dispatcher.send_key_combination([VK_MENU, VK_TAB])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'windows_search':
            self.dispatcher.send_key_combination([VK_LWIN, VK_S])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'task_manager':
            self.dispatcher.send_key_combination([VK_CONTROL, VK_SHIFT, VK_ESCAPE])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'file_explorer':
            self.dispatcher.send_key_combination([VK_LWIN, VK_E])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'screenshot':
            self.dispatcher.send_key_combination([VK_LWIN, VK_SHIFT, VK_S])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'lock_workstation':
            user32.LockWorkStation()
            return {"action": action_id, "status": "executed"}

        # 2. Volume and Media Keys
        elif action_id == 'vol_up':
            self.dispatcher.send_key_combination([VK_VOLUME_UP])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'vol_down':
            self.dispatcher.send_key_combination([VK_VOLUME_DOWN])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'vol_mute':
            self.dispatcher.send_key_combination([VK_VOLUME_MUTE])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_playpause':
            self.dispatcher.send_key_combination([VK_MEDIA_PLAY_PAUSE])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_next':
            self.dispatcher.send_key_combination([VK_MEDIA_NEXT_TRACK])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_prev':
            self.dispatcher.send_key_combination([VK_MEDIA_PREV_TRACK])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_fullscreen':
            self.dispatcher.send_key_combination([VK_F])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_seek_fwd':
            self.dispatcher.send_key_combination([VK_RIGHT])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'media_seek_back':
            self.dispatcher.send_key_combination([VK_LEFT])
            return {"action": action_id, "status": "executed"}

        # 3. Presenter Mode Actions (PRD Sec 08 & 18)
        elif action_id == 'presenter_next':
            self.dispatcher.send_key_combination([VK_NEXT])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'presenter_prev':
            self.dispatcher.send_key_combination([VK_PRIOR])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'presenter_start':
            self.dispatcher.send_key_combination([VK_F5])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'presenter_black':
            self.dispatcher.send_key_combination([VK_B])
            return {"action": action_id, "status": "executed"}

        elif action_id == 'presenter_end':
            self.dispatcher.send_key_combination([VK_ESCAPE])
            return {"action": action_id, "status": "executed"}

        # 4. Display Brightness Actions (PRD Sec 09)
        elif action_id == 'brightness_up':
            new_val = self.adjust_brightness(10)
            return {"action": action_id, "status": "executed", "level": new_val}

        elif action_id == 'brightness_down':
            new_val = self.adjust_brightness(-10)
            return {"action": action_id, "status": "executed", "level": new_val}

        # 5. Guarded Power Actions (PRD Sec 09)
        elif action_id == 'system_power':
            power_type = params.get('type', '').lower()
            if power_type == 'sleep':
                ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
                return {"action": action_id, "status": "executed", "type": "sleep"}
            elif power_type == 'restart':
                subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
                return {"action": action_id, "status": "executed", "type": "restart"}
            elif power_type == 'shutdown':
                subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
                return {"action": action_id, "status": "executed", "type": "shutdown"}
            else:
                return {"action": action_id, "status": "denied", "reason": "unrecognized_power_type"}

        # Any unauthorized action is rejected
        print(f"[ActionHandler] Rejected non-allowlisted action: {action_id}")
        return {"action": action_id, "status": "unsupported", "reason": "not_allowlisted"}
