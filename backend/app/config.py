"""Configuration management for the backend."""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings."""

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # Snapshot storage
    snapshot_storage_dir: str = "snapshots"

    # Git repository path (for git-based snapshots)
    repo_path: str = ""

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def snapshot_storage_path(self) -> str:
        """Absolute path where snapshot metadata is stored."""
        return os.path.abspath(self.snapshot_storage_dir)


settings = Settings()
