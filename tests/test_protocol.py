"""
Protocol & HTTP Endpoint Acceptance Tests
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

from app import CLIENT_DIR, dispatcher, action_handler

class TestProtocol(unittest.TestCase):
    def test_pwa_files_exist(self):
        """Verify that PWA files are all in place."""
        index_path = os.path.join(CLIENT_DIR, "index.html")
        manifest_path = os.path.join(CLIENT_DIR, "manifest.json")
        sw_path = os.path.join(CLIENT_DIR, "sw.js")

        self.assertTrue(os.path.exists(index_path), "index.html must exist")
        self.assertTrue(os.path.exists(manifest_path), "manifest.json must exist")
        self.assertTrue(os.path.exists(sw_path), "sw.js must exist")

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            self.assertIn("Digital Touchpad", html)
            self.assertIn("touchpadSurface", html)
            self.assertIn("manifest.json", html)

    def test_quick_action_allowlist(self):
        """Verify allowlist enforcement in action handler."""
        res = action_handler.handle_action("windows_search")
        self.assertEqual(res.get("status"), "executed")

        res_bad = action_handler.handle_action("malicious_shell")
        self.assertEqual(res_bad.get("status"), "unsupported")

if __name__ == "__main__":
    unittest.main()
