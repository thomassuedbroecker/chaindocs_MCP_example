from pathlib import Path

from langchain_documents_mcp_server.config import Settings
from langchain_documents_mcp_server.document_store import DocumentStore, IndexedChunk, make_excerpt
from langchain_documents_mcp_server.errors import ChunkNotFoundError, DocumentNotFoundError
from langchain_documents_mcp_server.server import run


def _make_store(tmp_path: Path) -> DocumentStore:
    settings = Settings(app_env="test", documents_path=tmp_path)
    store = DocumentStore(settings)
    store._chunks = [
        IndexedChunk(
            chunk_id="guide.md:0",
            source="guide.md",
            title="guide",
            content="This guide explains MCP server setup with LangChain and local documents.",
            metadata={},
        ),
        IndexedChunk(
            chunk_id="notes.txt:0",
            source="notes.txt",
            title="notes",
            content="Random notes about another topic.",
            metadata={},
        ),
    ]
    store._documents = {
        "guide.md": {
            "source": "guide.md",
            "title": "guide",
            "absolute_path": str(tmp_path / "guide.md"),
            "chunk_count": 1,
        },
        "notes.txt": {
            "source": "notes.txt",
            "title": "notes",
            "absolute_path": str(tmp_path / "notes.txt"),
            "chunk_count": 1,
        },
    }
    return store


def test_search_returns_ranked_match(tmp_path: Path) -> None:
    store = _make_store(tmp_path)

    result = store.search("mcp setup", limit=1)

    assert result["count"] == 1
    assert result["items"][0]["source"] == "guide.md"


def test_read_document_returns_file_content(tmp_path: Path) -> None:
    target = tmp_path / "guide.md"
    target.write_text("# Guide\nhello", encoding="utf-8")
    store = _make_store(tmp_path)

    result = store.read_document("guide.md")

    assert result["content"] == "# Guide\nhello"


def test_read_document_raises_for_unknown_source(tmp_path: Path) -> None:
    store = _make_store(tmp_path)

    try:
        store.read_document("missing.md")
    except DocumentNotFoundError:
        pass
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("Expected DocumentNotFoundError")


def test_get_chunk_raises_for_unknown_chunk(tmp_path: Path) -> None:
    store = _make_store(tmp_path)

    try:
        store.get_chunk("missing:0")
    except ChunkNotFoundError:
        pass
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("Expected ChunkNotFoundError")


def test_make_excerpt_includes_match() -> None:
    excerpt = make_excerpt("Alpha beta gamma delta", ["gamma"], width=12)

    assert "gamma" in excerpt.lower()


def test_settings_normalize_http_streamable_alias(tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        documents_path=tmp_path,
        mcp_transport="http_streamable",
    )

    assert settings.mcp_transport == "streamable-http"
    assert settings.streamable_http_url == "http://127.0.0.1:8000/mcp"


def test_run_uses_configured_transport(monkeypatch, tmp_path: Path) -> None:
    class DummyServer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, None]] = []

        def run(self, transport: str, mount_path: None = None) -> None:
            self.calls.append((transport, mount_path))

    dummy = DummyServer()
    settings = Settings(app_env="test", documents_path=tmp_path, mcp_transport="streamable-http")

    monkeypatch.setattr(
        "langchain_documents_mcp_server.server.create_server",
        lambda settings=None: dummy,
    )

    run(settings)

    assert dummy.calls == [("streamable-http", None)]
