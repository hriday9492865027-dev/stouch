"""
Digital Touchpad Diagnostics & Health Subsystem (PRD v2.0 Section 15 & AT-016)
Collects technical diagnostic signals and generates user-consented, redacted telemetry bundles.
Strictly redacts sensitive user paths, local usernames, and raw input history.
"""

import os
import sys
import platform
import socket
import time
import subprocess
import re

RECEIVER_VERSION = "2.0.0"

class DiagnosticsManager:
    def __init__(self, dispatcher, action_handler):
        self.dispatcher = dispatcher
        self.action_handler = action_handler
        self.start_time = time.time()
        self.packet_count = 0
        self.error_count = 0
        self.recent_errors = []

    def log_error(self, err_msg: str):
        self.error_count += 1
        self.recent_errors.append({
            "timestamp": time.time(),
            "message": str(err_msg)[:200]
        })
        if len(self.recent_errors) > 20:
            self.recent_errors.pop(0)

    def get_firewall_status(self) -> str:
        """Check if Windows Firewall allows inbound connections."""
        try:
            res = subprocess.run(
                ["netsh", "advfirewall", "show", "currentprofile"],
                capture_output=True, text=True, timeout=2
            )
            if "State" in res.stdout:
                for line in res.stdout.splitlines():
                    if "State" in line:
                        return line.strip()
            return "Active"
        except Exception:
            return "Unknown"

    def get_health_report(self) -> dict:
        uptime = round(time.time() - self.start_time, 1)
        return {
            "version": RECEIVER_VERSION,
            "status": "healthy",
            "uptime_seconds": uptime,
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "python_version": platform.python_version(),
            "firewall_profile": self.get_firewall_status(),
            "held_buttons_count": len(self.dispatcher.held_mouse_buttons),
            "held_keys_count": len(self.dispatcher.held_keys),
            "supported_actions_count": 16,
            "error_count": self.error_count
        }

    def generate_redacted_export(self) -> dict:
        """Export redacted bundle for troubleshooting (AT-016)."""
        raw_report = self.get_health_report()

        # Sanitize personal username from paths
        username = os.getenv("USERNAME", "user")
        userprofile = os.getenv("USERPROFILE", "")

        def redact_string(s: str) -> str:
            if not isinstance(s, str):
                return s
            if username and username.lower() != "user":
                s = re.sub(re.escape(username), "<REDACTED_USER>", s, flags=re.IGNORECASE)
            if userprofile:
                s = re.sub(re.escape(userprofile), "<REDACTED_PATH>", s, flags=re.IGNORECASE)
            # Redact full IP addresses to subnet only
            s = re.sub(r"\b(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}\b", r"\1x.x", s)
            return s

        redacted_report = {
            "app": "Digital Touchpad Receiver",
            "prd_version": "2.0",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system": {
                "os": redact_string(raw_report["os"]),
                "python": raw_report["python_version"],
                "firewall": raw_report["firewall_profile"],
                "uptime": raw_report["uptime_seconds"]
            },
            "receiver_metrics": {
                "version": raw_report["version"],
                "held_inputs": raw_report["held_buttons_count"] + raw_report["held_keys_count"],
                "errors_total": raw_report["error_count"],
                "recent_errors": [
                    {"time": e["timestamp"], "msg": redact_string(e["message"])}
                    for e in self.recent_errors
                ]
            }
        }
        return redacted_report

