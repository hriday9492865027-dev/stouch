"""
Pairing and Network Discovery Helper (PRD v2.0 Section 04 & 13)
Detects local LAN IPv4 address, Bluetooth Network Connection IP,
generates session tokens, and renders connection info.
"""

import socket
import secrets
import string
import subprocess
import re

def get_all_ips() -> dict:
    """Finds Wi-Fi, Ethernet, and Bluetooth network IPs."""
    ips = {
        "primary": "127.0.0.1",
        "wifi": None,
        "bluetooth": None,
        "all": []
    }

    # Primary routing IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ips["primary"] = s.getsockname()[0]
    except Exception:
        ips["primary"] = '127.0.0.1'
    finally:
        s.close()

    # Parse ipconfig to detect named adapters like Bluetooth
    try:
        out = subprocess.check_output("ipconfig", shell=True, text=True, errors="ignore")
        current_adapter = ""
        for line in out.splitlines():
            line_s = line.strip()
            if "adapter" in line:
                current_adapter = line_s.lower()
            elif "ipv4 address" in line_s:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line_s)
                if match:
                    ip_val = match.group(1)
                    ips["all"].append({"adapter": current_adapter, "ip": ip_val})
                    if "bluetooth" in current_adapter:
                        ips["bluetooth"] = ip_val
                    elif "wi-fi" in current_adapter or "wireless" in current_adapter:
                        ips["wifi"] = ip_val
    except Exception:
        pass

    return ips

def get_local_ip() -> str:
    """Returns primary LAN IP."""
    return get_all_ips().get("primary", "127.0.0.1")

def generate_pairing_pin() -> str:
    """Generates a secure short-lived 6-digit numeric PIN."""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def generate_session_token() -> str:
    """Generates a cryptographically strong session token."""
    return secrets.token_urlsafe(24)

def print_banner(port: int, pin: str):
    ip_info = get_all_ips()
    primary_ip = ip_info["primary"]
    bt_ip = ip_info.get("bluetooth")

    border = "=" * 65
    print(border)
    print("   DIGITAL TOUCHPAD - WINDOWS RECEIVER (v2.0)")
    print(border)
    print(f" * Wi-Fi / LAN URL:        http://{primary_ip}:{port}/")
    if bt_ip:
        print(f" * Bluetooth Network URL:  http://{bt_ip}:{port}/")
    else:
        print(f" * Bluetooth Network:      Ready (Connect via Windows BT settings)")
    print(f" * Pairing PIN:            {pin}")
    print(f" * Status:                 Ready for Wi-Fi and Bluetooth connections")
    print("")
    print(" Scan QR or open your mobile browser to connect:")
    print(f" >>> http://{primary_ip}:{port}/")
    print(border)
