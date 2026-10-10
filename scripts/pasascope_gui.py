#!/usr/bin/env python3
"""PasaScope (ภาษา-สโคป) Desktop GUI Launcher.

Launches the native graphical desktop interface for clinicians.
Supports seamless co-launching of the FastAPI backend server alongside the GUI.
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

from packages.gui.app import PasaScopeGUIApp
from packages.gui.backend_manager import BackendServerManager
from packages.tui.client import DEFAULT_API_URL, PasaScopeClient


def main() -> int:
    parser = argparse.ArgumentParser(description="PasaScope (ภาษา-สโคป) Desktop GUI Application")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base URL of PasaScope Backend API")
    parser.add_argument("--mock", action="store_true", help="Force offline mock mode without starting backend")
    parser.add_argument(
        "--no-backend",
        action="store_true",
        help="Do not automatically start backend server if it is offline",
    )
    parser.add_argument(
        "--with-backend",
        "-b",
        action="store_true",
        help="Explicitly auto-start backend server (default when not in mock mode)",
    )
    parser.add_argument(
        "--backend-reload",
        action="store_true",
        help="Enable uvicorn auto-reload on backend server (for development)",
    )
    parser.add_argument("--seed-demo", action="store_true", help="Pre-populate demo cases for demonstration")
    args = parser.parse_args()

    mock_mode = args.mock
    seed_demo = args.seed_demo
    backend_manager: BackendServerManager | None = None

    if not mock_mode:
        backend_manager = BackendServerManager(base_url=args.api_url, root_dir=ROOT)
        is_healthy = backend_manager.check_health()

        if is_healthy:
            print(f"[✓] Connected to existing PasaScope backend at {args.api_url}")
            mock_mode = False
        elif not args.no_backend:
            # Auto-launch backend server alongside GUI
            print(f"[*] PasaScope backend is not running at {args.api_url}.")
            print("[*] Automatically launching backend server (uvicorn app.main:app)...")
            started = backend_manager.start(
                timeout=12.0,
                reload=args.backend_reload,
                progress_cb=lambda msg: print(f"    {msg}"),
            )
            if started:
                print(
                    f"[✓] Backend server is ready (PID: {backend_manager.pid}). Launching GUI in Live API mode."
                )
                mock_mode = False
            else:
                print(
                    "⚠️ Could not start backend server. Launching in Offline Research Mock Mode with demo data.\n"
                    f"    Check log file: {backend_manager.log_file_path}"
                )
                mock_mode = True
                seed_demo = True
        else:
            print(
                f"[*] Notice: Backend API ({args.api_url}) is offline and --no-backend was specified.\n"
                f"    Launching in Offline Research Mock Mode with demo data."
            )
            mock_mode = True
            seed_demo = True

    client = PasaScopeClient(base_url=args.api_url, mock_mode=mock_mode, seed_demo=seed_demo)

    root = tk.Tk()
    app = PasaScopeGUIApp(root, client=client, backend_manager=backend_manager)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return 0
    finally:
        if backend_manager and backend_manager.is_managed:
            print("[*] Shutting down managed PasaScope backend server...")
            backend_manager.stop()
            print("[✓] Backend server stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
