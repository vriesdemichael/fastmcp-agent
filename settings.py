from __future__ import annotations

from functools import cached_property
from pathlib import Path

from fastmcp.mcp_config import MCPConfig
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    app_name: str = "fastmcp-agent"
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    langfuse_public_key: str | None = Field(
        default=None, alias="LANGFUSE_PUBLIC_KEY"
    )
    langfuse_secret_key: str | None = Field(
        default=None, alias="LANGFUSE_SECRET_KEY"
    )
    langfuse_host: str | None = Field(default=None, alias="LANGFUSE_HOST")
    mcp_config_path: str = Field(default=".mcp.json", alias="MCP_CONFIG_PATH")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @cached_property
    def mcp_config(self) -> MCPConfig:
        """Return MCP configuration loaded from ``mcp_config_path``."""
        path = Path(self.mcp_config_path)
        if path.exists():
            try:
                return MCPConfig.from_file(path)
            except Exception:  # pragma: no cover - best effort
                return MCPConfig(mcpServers={})
        return MCPConfig(mcpServers={})
