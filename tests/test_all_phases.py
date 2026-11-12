"""
Comprehensive Test Suite for All Phases (PRD v2.0 Roadmap)
Validates Phase 0 (Spikes), Phase 1 (Core MVP), Phase 2 (Reliability & Diagnostics),
Phase 3 (Brightness & BT HID Contracts), and Phase 4 (Presenter Mode & Polish).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

from input_dispatcher import InputDispatcher
from action_handler import ActionHandler
from diagnostics import DiagnosticsManager, RECEIVER_VERSION

class TestAllPhases(unittest.TestCase):
    def setUp(self):
        self.dispatcher = InputDispatcher()
        self.action_handler = ActionHandler(self.dispatcher)
        self.diagnostics = DiagnosticsManager(self.dispatcher, self.action_handler)

    # ---------------- Phase 0 & 1: Core Input & Safety ----------------
    def test_phase1_pointer_and_clicks(self):
        # Bounded movements
        self.dispatcher.move_pointer(12, -8)
        self.dispatcher.move_pointer(9999, -9999) # Clamping test

        # Primary and secondary clicks
        self.dispatcher.set_button_state("left", "click")
        self.dispatcher.set_button_state("right", "click")
        self.dispatcher.set_button_state("middle", "click")
        self.dispatcher.set_button_state("left", "double_click")

    def test_phase1_release_all_watchdog(self):
        # Press button down
        self.dispatcher.set_button_state("left", "down")
        self.assertIn("left", self.dispatcher.held_mouse_buttons)
        # Release-all clears held state immediately
        self.dispatcher.release_all()
        self.assertEqual(len(self.dispatcher.held_mouse_buttons), 0)

    # ---------------- Phase 2: Reliability & Diagnostics ----------------
    def test_phase2_diagnostics_health_report(self):
        report = self.diagnostics.get_health_report()
        self.assertEqual(report["version"], RECEIVER_VERSION)
        self.assertEqual(report["status"], "healthy")
        self.assertIn("firewall_profile", report)
        self.assertIn("uptime_seconds", report)

    def test_phase2_redacted_export_at016(self):
        """AT-016: Diagnostic export must strictly redact sensitive usernames and userpaths."""
        export_data = self.diagnostics.generate_redacted_export()
        self.assertEqual(export_data["prd_version"], "2.0")
        self.assertIn("system", export_data)
        self.assertIn("receiver_metrics", export_data)

        # Ensure no personal username leaks
        user = os.getenv("USERNAME", "")
        if user and len(user) > 2:
            export_str = str(export_data)
            self.assertNotIn(f"\\Users\\{user}\\", export_str)

    # ---------------- Phase 3: Brightness & Advanced Controls ----------------
    def test_phase3_brightness_actions(self):
        res_up = self.action_handler.handle_action("brightness_up")
        self.assertEqual(res_up.get("status"), "executed")
        self.assertTrue(res_up.get("level") >= 10)

        res_down = self.action_handler.handle_action("brightness_down")
        self.assertEqual(res_down.get("status"), "executed")

    # ---------------- Phase 4: Presenter Mode & Media Deck ----------------
    def test_phase4_presenter_actions(self):
        res_next = self.action_handler.handle_action("presenter_next")
        self.assertEqual(res_next.get("status"), "executed")

        res_prev = self.action_handler.handle_action("presenter_prev")
        self.assertEqual(res_prev.get("status"), "executed")

        res_start = self.action_handler.handle_action("presenter_start")
        self.assertEqual(res_start.get("status"), "executed")

        res_black = self.action_handler.handle_action("presenter_black")
        self.assertEqual(res_black.get("status"), "executed")

        res_end = self.action_handler.handle_action("presenter_end")
        self.assertEqual(res_end.get("status"), "executed")

    def test_phase4_media_fullscreen_and_allowlist(self):
        res_fs = self.action_handler.handle_action("media_fullscreen")
        self.assertEqual(res_fs.get("status"), "executed")

        # Unknown actions are strictly blocked
        res_unknown = self.action_handler.handle_action("cmd.exe /c calc")
        self.assertEqual(res_unknown.get("status"), "unsupported")

if __name__ == "__main__":
    unittest.main()

