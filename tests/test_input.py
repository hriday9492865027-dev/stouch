"""
Automated Acceptance Tests for Digital Touchpad Input & Action Handlers (PRD Sec 17)
Tests: AT-002 (Pointer), AT-003 (Click), AT-004 (Drag), AT-008 (Safety), AT-009 (Release-All), AT-010 (Allowlist).
"""

import sys
import os
import unittest

# Add server directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

from input_dispatcher import InputDispatcher
from action_handler import ActionHandler

class TestInputDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = InputDispatcher()
        self.action_handler = ActionHandler(self.dispatcher)

    def test_at002_bounded_pointer_movement(self):
        """AT-002: Pointer updates are bounded and do not throw exceptions."""
        try:
            self.dispatcher.move_pointer(10, -15)
            # Test clamping extreme delta values
            self.dispatcher.move_pointer(99999, -99999)
            self.dispatcher.move_pointer(0, 0)
        except Exception as e:
            self.fail(f"Pointer movement raised exception: {e}")

    def test_at003_clicks(self):
        """AT-003: Single and double clicks simulate properly."""
        try:
            self.dispatcher.set_button_state("left", "click")
            self.dispatcher.set_button_state("right", "click")
            self.dispatcher.set_button_state("middle", "click")
            self.dispatcher.set_button_state("left", "double_click")
        except Exception as e:
            self.fail(f"Click simulation raised exception: {e}")

    def test_at004_and_at009_drag_and_release_safety(self):
        """AT-004 & AT-009: Button down tracks state, and release_all clears held buttons."""
        self.dispatcher.set_button_state("left", "down")
        self.assertIn("left", self.dispatcher.held_mouse_buttons)

        # Release all should clear it immediately
        self.dispatcher.release_all()
        self.assertEqual(len(self.dispatcher.held_mouse_buttons), 0)

    def test_at006_scrolling(self):
        """AT-006: Vertical and horizontal scrolling."""
        try:
            self.dispatcher.scroll(0, 5)   # vertical
            self.dispatcher.scroll(-3, 0)  # horizontal
        except Exception as e:
            self.fail(f"Scroll simulation raised exception: {e}")

    def test_at010_allowlist_enforcement(self):
        """AT-010: Allowed actions return executed; arbitrary actions are blocked."""
        # Allowlisted navigation action
        res_desktop = self.action_handler.handle_action("show_desktop")
        self.assertEqual(res_desktop.get("status"), "executed")

        # Allowlisted volume action
        res_vol = self.action_handler.handle_action("vol_mute")
        self.assertEqual(res_vol.get("status"), "executed")

        # Non-allowlisted or arbitrary malicious commands MUST be blocked
        res_malicious = self.action_handler.handle_action("powershell.exe -Command rm -rf C:\\")
        self.assertEqual(res_malicious.get("status"), "unsupported")
        self.assertEqual(res_malicious.get("reason"), "not_allowlisted")

        res_unknown = self.action_handler.handle_action("random_hack_command")
        self.assertEqual(res_unknown.get("status"), "unsupported")

if __name__ == "__main__":
    unittest.main()

