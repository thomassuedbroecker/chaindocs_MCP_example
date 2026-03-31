from pathlib import Path

import pytest

from langchain_documents_mcp_server.config import Settings
from langchain_documents_mcp_server.errors import DocumentNotFoundError
from langchain_documents_mcp_server.server import create_server


class DummyFastMCP:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.tools: dict[str, object] = {}

    def tool(self, name: str):
        def decorator(fn):
            self.tools[name] = fn
            return fn

        return decorator


class DummyStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def reload(self) -> dict[str, int]:
        return {"document_count": 1, "chunk_count": 2}

    def stats(self) -> dict[str, int]:
        return {"document_count": 1, "chunk_count": 2}

    def list_documents(self) -> dict[str, object]:
        return {"items": [{"source": "guide.md"}], "count": 1}

    def search(self, query: str, limit: int) -> dict[str, object]:
        return {"items": [{"query": query, "limit": limit}], "count": 1}

    def read_document(self, source: str) -> dict[str, object]:
        raise DocumentNotFoundError(source)

    def get_chunk(self, chunk_id: str) -> dict[str, object]:
        raise RuntimeError("boom")


def test_create_server_registers_tools_and_wraps_errors(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(app_env="test", documents_path=tmp_path, mcp_transport="streamable-http")

    monkeypatch.setattr("langchain_documents_mcp_server.server.FastMCP", DummyFastMCP)
    monkeypatch.setattr("langchain_documents_mcp_server.server.DocumentStore", DummyStore)
    monkeypatch.setattr("langchain_documents_mcp_server.server.configure_logging", lambda level: None)

    server = create_server(settings)

    assert server.kwargs["name"] == "langchain-documents-mcp-server"
    assert server.kwargs["streamable_http_path"] == "/mcp"
    assert set(server.tools) == {
        "server_info",
        "reload_documents",
        "list_documents",
        "search_documents",
        "read_document",
        "get_document_chunk",
    }

    server_info = server.tools["server_info"]()
    assert server_info["ok"] is True
    assert server_info["result"]["indexed_documents"] == 1
    assert server_info["result"]["transport"] == "streamable-http"

    assert server.tools["reload_documents"]()["result"]["chunk_count"] == 2
    assert server.tools["list_documents"]()["result"]["count"] == 1
    assert server.tools["search_documents"]("setup", limit=2)["result"]["items"][0] == {
        "query": "setup",
        "limit": 2,
    }

    read_document = server.tools["read_document"]("missing.md")
    assert read_document["ok"] is False
    assert read_document["error"]["code"] == "document_not_found"

    get_chunk = server.tools["get_document_chunk"]("missing:0")
    assert get_chunk["ok"] is False
    assert get_chunk["error"]["code"] == "internal_error"
    assert get_chunk["error"]["message"] == "boom"


def test_create_server_requires_fastmcp(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(app_env="test", documents_path=tmp_path)

    monkeypatch.setattr("langchain_documents_mcp_server.server.FastMCP", None)

    with pytest.raises(RuntimeError, match="mcp package is not installed"):
        create_server(settings)
