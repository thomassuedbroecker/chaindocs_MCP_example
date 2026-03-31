from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from langchain_documents_mcp_server.config import Settings
from langchain_documents_mcp_server.document_store import (
    DocumentStore,
    IndexedChunk,
    make_excerpt,
    score_chunk,
    tokenize,
)
from langchain_documents_mcp_server.errors import DocumentNotFoundError


def test_reload_builds_index_and_returns_chunk_details(tmp_path: Path, monkeypatch) -> None:
    store = DocumentStore(Settings(app_env="test", documents_path=tmp_path))

    split_documents = [
        SimpleNamespace(
            page_content="Alpha beta",
            metadata={"source": "guide.md", "absolute_path": str(tmp_path / "guide.md")},
        ),
        SimpleNamespace(
            page_content="Gamma delta",
            metadata={"source": "guide.md", "absolute_path": str(tmp_path / "guide.md")},
        ),
        SimpleNamespace(
            page_content="Notes",
            metadata={"source": "notes.txt", "absolute_path": str(tmp_path / "notes.txt")},
        ),
    ]

    monkeypatch.setattr(store, "_load_langchain_documents", lambda: ["raw"])
    monkeypatch.setattr(store, "_split_documents", lambda documents: split_documents)

    result = store.reload()

    assert result == {"document_count": 2, "chunk_count": 3}
    assert store.stats() == result
    assert store.list_documents()["count"] == 2
    assert store.get_chunk("guide.md:1")["content"] == "Gamma delta"


def test_iter_source_files_and_load_langchain_documents(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()

    guide = tmp_path / "guide.md"
    guide.write_text("# Guide\nhello", encoding="utf-8")
    notes = nested / "notes.txt"
    notes.write_text("nested text", encoding="utf-8")
    ignored = tmp_path / "image.png"
    ignored.write_bytes(b"not-text")

    store = DocumentStore(Settings(app_env="test", documents_path=tmp_path, allowed_extensions="md,txt"))

    files = store._iter_source_files()
    assert [path.relative_to(tmp_path).as_posix() for path in files] == ["guide.md", "nested/notes.txt"]

    documents = store._load_langchain_documents()
    assert [doc.metadata["source"] for doc in documents] == ["guide.md", "nested/notes.txt"]
    assert documents[0].metadata["absolute_path"].endswith("guide.md")


def test_split_documents_and_resolve_source_guard(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("guide text", encoding="utf-8")

    store = DocumentStore(Settings(app_env="test", documents_path=tmp_path, chunk_size=100, chunk_overlap=10))
    split = store._split_documents(
        [Document(page_content="A" * 250, metadata={"source": "guide.md", "absolute_path": str(guide)})]
    )

    assert len(split) >= 3
    assert split[0].metadata["source"] == "guide.md"

    with pytest.raises(DocumentNotFoundError):
        store._resolve_source_path("../outside.txt")


def test_helper_functions_cover_phrase_scoring_and_excerpt_edges() -> None:
    chunk = IndexedChunk(
        chunk_id="guide.md:0",
        source="guide.md",
        title="Guide Setup",
        content="This guide setup explains the search flow in detail.",
        metadata={},
    )

    tokens = tokenize("Guide setup!")
    assert tokens == ["guide", "setup"]
    assert score_chunk(chunk, tokens, "guide setup") > score_chunk(chunk, ["guide"], "guide")
    assert make_excerpt("Alpha beta gamma delta epsilon", ["gamma"], width=0) == ""

    excerpt = make_excerpt("Alpha beta gamma delta epsilon", ["gamma"], width=4)
    assert "gamma" in excerpt.lower()
