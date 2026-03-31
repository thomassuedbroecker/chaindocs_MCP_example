from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigurationError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["local", "dev", "test"] = "local"
    log_level: str = "INFO"
    mcp_transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    mcp_streamable_http_path: str = "/mcp"
    mcp_stateless_http: bool = True
    mcp_json_response: bool = True
    documents_path: Path = Field(default=Path("sample_documents"))
    allowed_extensions: str = Field(default=".md,.txt")
    chunk_size: int = Field(default=600, ge=100, le=4000)
    chunk_overlap: int = Field(default=100, ge=0, le=1000)
    max_results: int = Field(default=5, ge=1, le=20)

    @field_validator("documents_path", mode="before")
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser()

    @field_validator("mcp_transport", mode="before")
    @classmethod
    def _normalize_transport(cls, value: str) -> str:
        normalized = value.strip().lower()
        aliases = {
            "http_streamable": "streamable-http",
            "streamable_http": "streamable-http",
            "http-streamable": "streamable-http",
        }
        return aliases.get(normalized, normalized)

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ConfigurationError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if not self.mcp_streamable_http_path.startswith("/"):
            raise ConfigurationError("MCP_STREAMABLE_HTTP_PATH must start with '/'")
        if not self.documents_path.exists():
            raise ConfigurationError(
                "DOCUMENTS_PATH does not exist",
                {"documents_path": str(self.documents_path)},
            )
        if not self.documents_path.is_dir():
            raise ConfigurationError(
                "DOCUMENTS_PATH must be a directory",
                {"documents_path": str(self.documents_path)},
            )
        return self

    @property
    def normalized_extensions(self) -> tuple[str, ...]:
        values = []
        for item in self.allowed_extensions.split(","):
            value = item.strip().lower()
            if not value:
                continue
            if not value.startswith("."):
                value = f".{value}"
            values.append(value)
        return tuple(values)

    def masked(self) -> dict[str, str | int]:
        return {
            "app_env": self.app_env,
            "log_level": self.log_level,
            "mcp_transport": self.mcp_transport,
            "mcp_host": self.mcp_host,
            "mcp_port": self.mcp_port,
            "mcp_streamable_http_path": self.mcp_streamable_http_path,
            "mcp_stateless_http": int(self.mcp_stateless_http),
            "mcp_json_response": int(self.mcp_json_response),
            "documents_path": str(self.documents_path),
            "allowed_extensions": self.allowed_extensions,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "max_results": self.max_results,
        }

    @property
    def streamable_http_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}{self.mcp_streamable_http_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
