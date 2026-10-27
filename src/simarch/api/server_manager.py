"""SimArch localhost dashboard server manager.

Controls on-demand dynamic startup and shutdown of the local HTTP dashboard.
By default, localhost remains LOCKED and dormant with zero listening ports.
The AI agent or user can decide when/if to spin up the dashboard on loopback.
"""

import threading
import time
from typing import Any, Dict, Optional
import uvicorn
from simarch.core.config import get_settings


class DashboardServerManager:
    """Thread-safe background controller for the local dashboard server."""

    _instance: Optional["DashboardServerManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.server: Optional[uvicorn.Server] = None
        self.thread: Optional[threading.Thread] = None
        self.host: str = "127.0.0.1"
        self.port: int = 8400
        self._is_running: bool = False

    @classmethod
    def get_instance(cls) -> "DashboardServerManager":
        """Get or create singleton manager instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def is_running(self) -> bool:
        """Check if local HTTP server is currently active and listening."""
        return self._is_running and self.server is not None and self.server.started

    def start(self, host: str = "127.0.0.1", port: int = 8400) -> Dict[str, Any]:
        """Start local dashboard server in a daemon thread.

        Security guard: Forces loopback (127.0.0.1) unless explicitly overridden,
        keeping localhost locked away from external network interfaces.
        """
        with self._lock:
            if self.is_running():
                return {
                    "status": "already_running",
                    "url": f"http://{self.host}:{self.port}",
                    "host": self.host,
                    "port": self.port
                }

            self.host = host
            self.port = port

            # Configure uvicorn server programmatically
            config = uvicorn.Config(
                app="simarch.api.app:app",
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False
            )
            self.server = uvicorn.Server(config)

            # Run in daemon thread so it doesn't block caller
            self.thread = threading.Thread(target=self.server.run, daemon=True)
            self.thread.start()

            # Wait briefly for server startup
            for _ in range(25):
                if self.server.started:
                    break
                time.sleep(0.08)

            self._is_running = True
            url = f"http://{self.host}:{self.port}"
            return {
                "status": "started",
                "url": url,
                "host": self.host,
                "port": self.port,
                "message": f"SimArch dashboard unlocked and active at {url}"
            }

    def stop(self) -> Dict[str, Any]:
        """Stop running local dashboard server and lock localhost."""
        with self._lock:
            if not self.is_running():
                return {
                    "status": "not_running",
                    "message": "Localhost is already locked and dormant."
                }

            if self.server:
                self.server.should_exit = True
                self._is_running = False

            return {
                "status": "stopped",
                "message": "SimArch dashboard stopped. Localhost port released and locked."
            }

    def get_status(self) -> Dict[str, Any]:
        """Return operational state of the localhost server."""
        active = self.is_running()
        return {
            "active": active,
            "url": f"http://{self.host}:{self.port}" if active else None,
            "host": self.host,
            "port": self.port,
            "locked": not active
        }


# Global singleton access
dashboard_manager = DashboardServerManager.get_instance()
