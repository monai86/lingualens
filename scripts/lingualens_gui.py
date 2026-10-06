#!/usr/bin/env python3
"""PasaScope (formerly LinguaLens) Desktop GUI Launcher compatibility stub."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pasascope_gui import main

if __name__ == "__main__":
    sys.exit(main())
