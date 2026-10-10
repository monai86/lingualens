"""PasaScope Backend Server Process Manager.

Manages the lifecycle of the local FastAPI uvicorn backend server
allowing seamless co-launch and termination alongside the Desktop GUI.
"""

from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

logger = logging.getLogger("pasascope.backend_manager")


class BackendServerManager:
    """Controls the background uvicorn FastAPI process for PasaScope."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000/api/v1",
        root_dir: Path | None = None,
        log_file: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.root_dir = root_dir or Path(__file__).resolve().parents[2]
        self._process: subprocess.Popen[bytes] | None = None
        self._managed: bool = False
        self._log_file_path = log_file or (self.root_dir / ".local" / "logs" / "backend.log")
        self._log_fp: Any = None
        self._atexit_registered: bool = False

    @property
    def host(self) -> str:
        parsed = urllib.parse.urlparse(self.base_url)
        h = parsed.hostname or "127.0.0.1"
        return "127.0.0.1" if h == "localhost" else h

    @property
    def port(self) -> int:
        parsed = urllib.parse.urlparse(self.base_url)
        return parsed.port or 8000

    @property
    def log_file_path(self) -> Path:
        return self._log_file_path

    @property
    def is_managed(self) -> bool:
        """True if the backend was spawned by this manager instance and is currently active."""
        return self._managed and self._process is not None and self._process.poll() is None

    @property
    def pid(self) -> int | None:
        if self._process and self._process.poll() is None:
            return self._process.pid
        return None

    def check_health(self, timeout: float = 1.0) -> bool:
        """Check if backend is healthy and responding to requests."""
        endpoints = [
            f"{self.base_url}/health",
            f"http://{self.host}:{self.port}/api/v1/health",
            f"http://{self.host}:{self.port}/health",
        ]
        for url in endpoints:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "PasaScope-Probe/1.0"},
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
        return False

    def start(
        self,
        timeout: float = 12.0,
        reload: bool = False,
        progress_cb: Callable[[str], None] | None = None,
    ) -> bool:
        """Start backend process if not already running.

        Returns True if backend is healthy and ready.
        """
        # If already running externally or internally, nothing to do
        if self.check_health(timeout=1.0):
            if progress_cb:
                progress_cb("Backend is already running and reachable.")
            return True

        if progress_cb:
            progress_cb(f"Starting PasaScope FastAPI backend on port {self.port}...")

        # Ensure log directory exists
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._log_fp = open(self._log_file_path, "a", encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not open log file %s: %s", self._log_file_path, exc)
            self._log_fp = subprocess.DEVNULL

        # Environment setup: include apps/api, root, and src
        env = dict(os.environ)
        apps_api = str(self.root_dir / "apps" / "api")
        src_dir = str(self.root_dir / "src")
        root_dir_str = str(self.root_dir)
        existing_pythonpath = env.get("PYTHONPATH", "")
        new_pythonpath = os.pathsep.join(
            [p for p in [apps_api, root_dir_str, src_dir, existing_pythonpath] if p]
        )
        env["PYTHONPATH"] = new_pythonpath
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]
        if reload:
            cmd.append("--reload")

        cwd = str(self.root_dir / "apps" / "api")
        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=self._log_fp,
                stderr=self._log_fp,
                start_new_session=True if os.name == "posix" else False,
            )
            self._managed = True
        except Exception as exc:
            logger.error("Failed to spawn uvicorn backend: %s", exc)
            if progress_cb:
                progress_cb(f"Failed to spawn backend process: {exc}")
            if self._log_fp and self._log_fp != subprocess.DEVNULL:
                try:
                    self._log_fp.close()
                except Exception:
                    pass
                self._log_fp = None
            return False

        if not self._atexit_registered:
            atexit.register(self.stop)
            self._atexit_registered = True

        # Poll until healthy
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._process.poll() is not None:
                rc = self._process.returncode
                logger.error("Backend process exited prematurely with code %s", rc)
                if progress_cb:
                    progress_cb(
                        f"Backend exited prematurely with code {rc}. See {self._log_file_path}"
                    )
                self._managed = False
                self._process = None
                return False

            if self.check_health(timeout=0.5):
                if progress_cb:
                    progress_cb(
                        f"Backend started successfully (PID: {self._process.pid})."
                    )
                return True

            time.sleep(0.2)

        # Timeout reached
        logger.warning("Backend startup timed out after %.1fs", timeout)
        if progress_cb:
            progress_cb(f"Timed out waiting for backend to become ready after {timeout:.1f}s.")
        self.stop()
        return False

    def stop(self, timeout: float = 3.0) -> None:
        """Stop the managed backend process cleanly."""
        if not self._managed or self._process is None:
            return

        proc = self._process
        self._managed = False
        self._process = None

        if self._log_fp and self._log_fp != subprocess.DEVNULL:
            try:
                self._log_fp.close()
            except Exception:
                pass
            self._log_fp = None

        if proc.poll() is not None:
            return

        try:
            if os.name == "posix":
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except Exception:
                    proc.terminate()
            else:
                proc.terminate()

            proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, Exception):
            try:
                if os.name == "posix":
                    try:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except Exception:
                        proc.kill()
                else:
                    proc.kill()
                proc.wait(timeout=1.0)
            except Exception:
                pass
