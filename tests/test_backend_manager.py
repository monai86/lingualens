"""Tests for PasaScope Backend Server Manager and GUI integration."""

from __future__ import annotations

import gc
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from packages.gui.backend_manager import BackendServerManager
from packages.gui.app import PasaScopeGUIApp
from packages.tui.client import PasaScopeClient


@pytest.fixture
def tk_root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        except Exception:
            pass
        gc.collect()


def test_backend_manager_properties():
    mgr = BackendServerManager(base_url="http://127.0.0.1:8000/api/v1")
    assert mgr.host == "127.0.0.1"
    assert mgr.port == 8000
    assert not mgr.is_managed
    assert mgr.pid is None
    assert mgr.log_file_path.name == "backend.log"

    mgr_custom = BackendServerManager(base_url="http://localhost:9000/api/v1")
    assert mgr_custom.host == "127.0.0.1"
    assert mgr_custom.port == 9000


def test_backend_manager_check_health_offline():
    mgr = BackendServerManager(base_url="http://127.0.0.1:59999/api/v1")
    assert mgr.check_health(timeout=0.2) is False


def test_backend_manager_check_health_online():
    mgr = BackendServerManager(base_url="http://127.0.0.1:8000/api/v1")
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_open.return_value.__enter__.return_value = mock_resp
        assert mgr.check_health(timeout=1.0) is True


def test_backend_manager_start_already_running():
    mgr = BackendServerManager(base_url="http://127.0.0.1:8000/api/v1")
    with patch.object(mgr, "check_health", return_value=True):
        progress = []
        started = mgr.start(timeout=1.0, progress_cb=progress.append)
        assert started is True
        assert not mgr.is_managed
        assert any("already running" in p for p in progress)


def test_backend_manager_stop_lifecycle():
    mgr = BackendServerManager(base_url="http://127.0.0.1:8000/api/v1")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.pid = 12345
    mgr._process = mock_proc
    mgr._managed = True

    assert mgr.is_managed is True
    assert mgr.pid == 12345

    mgr.stop(timeout=1.0)
    assert mgr.is_managed is False
    assert mgr.pid is None
    mock_proc.terminate.assert_called()


def test_gui_app_backend_manager_wiring(tk_root):
    client = PasaScopeClient(mock_mode=True)
    app_default = PasaScopeGUIApp(tk_root, client=client)
    assert app_default.backend_manager is None

    mgr = BackendServerManager(base_url="http://127.0.0.1:8000/api/v1")
    app_custom = PasaScopeGUIApp(tk_root, client=client, backend_manager=mgr)
    assert app_custom.backend_manager is mgr
    assert app_custom.backend_manager.port == 8000


def test_gui_app_cleanup_stops_managed_backend(tk_root):
    client = PasaScopeClient(mock_mode=True)
    mgr = BackendServerManager(base_url=client.base_url)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.pid = 9999
    mgr._process = mock_proc
    mgr._managed = True

    app = PasaScopeGUIApp(tk_root, client=client, backend_manager=mgr)
    app._cleanup_timers()
    assert mgr.is_managed is False
    mock_proc.terminate.assert_called()


def test_gui_toggle_backend_prompts_and_starts(tk_root):
    client = PasaScopeClient(mock_mode=True)
    mock_mgr = MagicMock(spec=BackendServerManager)
    mock_mgr.port = 8000
    mock_mgr.pid = 7777
    mock_mgr.start.return_value = True

    app = PasaScopeGUIApp(tk_root, client=client, backend_manager=mock_mgr)

    with patch("tkinter.messagebox.askyesno", return_value=True), \
         patch("tkinter.messagebox.showinfo") as mock_info:
        app._toggle_backend_mode()
        mock_mgr.start.assert_called_once()
        assert app.client.mock_mode is False
        mock_info.assert_called()
