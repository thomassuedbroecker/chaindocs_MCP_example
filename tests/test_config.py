from pathlib import Path

import pytest

from langchain_documents_mcp_server import config as config_module
from langchain_documents_mcp_server.config import Settings
from langchain_documents_mcp_server.errors import ConfigurationError


def test_settings_validation_errors(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="CHUNK_OVERLAP must be smaller than CHUNK_SIZE"):
        Settings(app_env="test", documents_path=tmp_path, chunk_size=100, chunk_overlap=100)

    with pytest.raises(ConfigurationError, match="MCP_STREAMABLE_HTTP_PATH must start with '/'"):
        Settings(app_env="test", documents_path=tmp_path, mcp_streamable_http_path="mcp")

    with pytest.raises(ConfigurationError, match="DOCUMENTS_PATH does not exist"):
        Settings(app_env="test", documents_path=tmp_path / "missing")

    with pytest.raises(ConfigurationError, match="DOCUMENTS_PATH must be a directory"):
        Settings(app_env="test", documents_path=file_path)


def test_settings_helpers_and_cache(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        documents_path=tmp_path,
        allowed_extensions="md, txt ,rst",
        mcp_stateless_http=False,
        mcp_json_response=False,
    )

    assert settings.normalized_extensions == (".md", ".txt", ".rst")
    assert settings.masked()["mcp_stateless_http"] == 0
    assert settings.masked()["mcp_json_response"] == 0

    config_module.get_settings.cache_clear()
    monkeypatch.setattr(config_module, "Settings", lambda: settings)

    assert config_module.get_settings() is settings
    assert config_module.get_settings() is settings

    config_module.get_settings.cache_clear()
