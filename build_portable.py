"""
Digital Touchpad Portable Packager (PRD v2.0 Section 10 & 18)
Creates a self-contained portable distribution zip ready to run on any Windows PC.
"""

import os
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
PORTABLE_FOLDER = os.path.join(DIST_DIR, "DigitalTouchpad_v2.0_Portable")
ZIP_NAME = os.path.join(DIST_DIR, "DigitalTouchpad_Windows_v2.0_Portable.zip")

def build_portable():
    print("Building Digital Touchpad Portable Distribution...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)

    os.makedirs(PORTABLE_FOLDER, exist_ok=True)

    # 1. Copy Server files
    shutil.copytree(
        os.path.join(BASE_DIR, "server"),
        os.path.join(PORTABLE_FOLDER, "server"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )

    # 2. Copy Client PWA files
    shutil.copytree(
        os.path.join(BASE_DIR, "client"),
        os.path.join(PORTABLE_FOLDER, "client")
    )

    # 3. Copy Launchers & Configs
    shutil.copy(os.path.join(BASE_DIR, "start_receiver.bat"), PORTABLE_FOLDER)
    shutil.copy(os.path.join(BASE_DIR, "start_receiver.ps1"), PORTABLE_FOLDER)
    shutil.copy(os.path.join(BASE_DIR, "setup_firewall.bat"), PORTABLE_FOLDER)
    shutil.copy(os.path.join(BASE_DIR, "setup_firewall.ps1"), PORTABLE_FOLDER)
    shutil.copy(os.path.join(BASE_DIR, "README.md"), PORTABLE_FOLDER)

    # 4. Create Zip Archive
    print(f"Compressing into {ZIP_NAME}...")
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PORTABLE_FOLDER):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, DIST_DIR)
                zf.write(abs_path, rel_path)

    print("Portable build completed successfully!")
    print(f"Archive created at: {ZIP_NAME}")

if __name__ == "__main__":
    build_portable()

