#!/usr/bin/env python3
"""PasaScope (ภาษา-สโคป) Desktop GUI Launcher.

Launches the native graphical desktop interface for clinicians.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tkinter as tk

# Ensure root directory is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.tui.client import PasaScopeClient, DEFAULT_API_URL
from packages.gui.app import PasaScopeGUIApp


def main() -> int:
    parser = argparse.ArgumentParser(description="PasaScope (ภาษา-สโคป) Desktop GUI Application")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base URL of PasaScope Backend API")
    parser.add_argument("--mock", action="store_true", help="Force offline mock mode")
    parser.add_argument("--seed-demo", action="store_true", help="Pre-populate demo cases for demonstration")
    args = parser.parse_args()

    client = PasaScopeClient(base_url=args.api_url, mock_mode=args.mock, seed_demo=args.seed_demo)

    root = tk.Tk()
    app = PasaScopeGUIApp(root, client=client)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
