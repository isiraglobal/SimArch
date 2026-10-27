"""SimArch configuration management."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Global SimArch runtime configuration."""
    app_name: str = "SimArch"
    environment: str = Field(default_factory=lambda: os.getenv("SIMARCH_ENV", "development"))
    home_dir: Path = Field(default_factory=lambda: Path(os.getenv("SIMARCH_HOME", Path.cwd() / ".simarch")))
    db_path: Optional[Path] = None
    default_model: str = Field(default_factory=lambda: os.getenv("SIMARCH_DEFAULT_MODEL", "deterministic-local"))
    enable_dashboard: bool = True
    dashboard_port: int = 8400
    dashboard_host: str = "127.0.0.1"
    worker_lease_seconds: int = 30
    worker_heartbeat_interval: int = 5
    max_delegation_depth: int = 5
    max_retries: int = 3

    # API Keys (optional; platform works 100% locally with deterministic provider)
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))

    def get_db_path(self) -> Path:
        """Get or initialize database file path."""
        if self.db_path:
            return self.db_path
        self.home_dir.mkdir(parents=True, exist_ok=True)
        return self.home_dir / "simarch.db"

    def get_workspace_dir(self) -> Path:
        """Get root temporary workspace directory."""
        path = self.home_dir / "workspaces"
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> Settings:
    """Return default settings instance."""
    return Settings()
