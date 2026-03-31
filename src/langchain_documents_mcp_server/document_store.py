from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .errors import ChunkNotFoundError, DocumentNotFoundError

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(slots=True)
class IndexedChunk:
    chunk_id: str
    source: str
    title: str
    content: str
    metadata: dict[str, Any]


class DocumentStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chunks: list[IndexedChunk] = []
        self._documents: dict[str, dict[str, Any]] = {}

    def reload(self) -> dict[str, int]:
        documents = self._load_langchain_documents()
        split_documents = self._split_documents(documents)

        chunks: list[IndexedChunk] = []
        documents_index: dict[str, dict[str, Any]] = {}

        for index, document in enumerate(split_documents):
            source = str(document.metadata.get("source", "unknown"))
            title = Path(source).stem.replace("-", " ").replace("_", " ").strip() or source
            chunk = IndexedChunk(
                chunk_id=f"{source}:{index}",
                source=source,
                title=title,
                content=document.page_content,
                metadata=dict(document.metadata),
            )
            chunks.append(chunk)

            record = documents_index.setdefault(
                source,
                {
                    "source": source,
                    "title": title,
                    "absolute_path": document.metadata.get("absolute_path", ""),
                    "chunk_count": 0,
                },
            )
            record["chunk_count"] += 1

        self._chunks = chunks
        self._documents = documents_index

        return {
            "document_count": len(self._documents),
            "chunk_count": len(self._chunks),
        }

    def list_documents(self) -> dict[str, Any]:
        items = sorted(self._documents.values(), key=lambda item: item["source"])
        return {"items": items, "count": len(items)}

    def stats(self) -> dict[str, int]:
        return {
            "document_count": len(self._documents),
            "chunk_count": len(self._chunks),
        }

    def search(self, query: str, limit: int | None = None) -> dict[str, Any]:
        query_terms = tokenize(query)
        max_results = limit or self.settings.max_results

        scored: list[tuple[int, IndexedChunk]] = []
        for chunk in self._chunks:
            score = score_chunk(chunk, query_terms, query)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].source, item[1].chunk_id))
        items = [
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "title": chunk.title,
                "score": score,
                "excerpt": make_excerpt(chunk.content, query_terms),
            }
            for score, chunk in scored[:max_results]
        ]
        return {"items": items, "count": len(items), "query": query}

    def read_document(self, source: str) -> dict[str, Any]:
        if source not in self._documents:
            raise DocumentNotFoundError(source)
        path = self._resolve_source_path(source)
        content = path.read_text(encoding="utf-8")
        return {
            "source": source,
            "absolute_path": str(path),
            "content": content,
            "chunk_ids": [chunk.chunk_id for chunk in self._chunks if chunk.source == source],
        }

    def get_chunk(self, chunk_id: str) -> dict[str, Any]:
        for chunk in self._chunks:
            if chunk.chunk_id == chunk_id:
                return {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "title": chunk.title,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                }
        raise ChunkNotFoundError(chunk_id)

    def _resolve_source_path(self, source: str) -> Path:
        base = self.settings.documents_path.resolve()
        candidate = (base / source).resolve()
        if candidate.parent != base and base not in candidate.parents:
            raise DocumentNotFoundError(source)
        if not candidate.exists() or not candidate.is_file():
            raise DocumentNotFoundError(source)
        return candidate

    def _load_langchain_documents(self) -> list[Any]:
        try:
            from langchain_community.document_loaders import TextLoader
        except Exception as exc:  # pragma: no cover - depends on optional runtime install
            raise RuntimeError(
                "langchain-community is not installed. Run scripts/setup.sh first."
            ) from exc

        documents: list[Any] = []
        for path in self._iter_source_files():
            loader = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True)
            for document in loader.load():
                document.metadata["source"] = str(path.relative_to(self.settings.documents_path))
                document.metadata["absolute_path"] = str(path.resolve())
                documents.append(document)
        return documents

    def _split_documents(self, documents: list[Any]) -> list[Any]:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except Exception as exc:  # pragma: no cover - depends on optional runtime install
            raise RuntimeError(
                "langchain-text-splitters is not installed. Run scripts/setup.sh first."
            ) from exc

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        return splitter.split_documents(documents)

    def _iter_source_files(self) -> list[Path]:
        files = []
        for path in sorted(self.settings.documents_path.rglob("*")):
            if path.is_file() and path.suffix.lower() in self.settings.normalized_extensions:
                files.append(path)
        return files


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def score_chunk(chunk: IndexedChunk, query_terms: list[str], raw_query: str) -> int:
    if not query_terms:
        return 0

    source = chunk.source.lower()
    title = chunk.title.lower()
    content = chunk.content.lower()
    phrase = raw_query.strip().lower()

    score = 0
    for term in query_terms:
        score += source.count(term) * 4
        score += title.count(term) * 6
        score += content.count(term) * 2

    if phrase and phrase in content:
        score += 10
    if phrase and phrase in title:
        score += 12
    return score


def make_excerpt(content: str, query_terms: list[str], width: int = 220) -> str:
    collapsed = " ".join(content.split())
    lower = collapsed.lower()
    position = 0
    match_length = 0

    for term in query_terms:
        found = lower.find(term)
        if found >= 0:
            position = found
            match_length = len(term)
            break

    if width <= 0:
        return ""

    if match_length and width < match_length:
        width = match_length

    start = max(position - max((width - match_length) // 2, 0), 0)
    end = min(max(start + width, position + match_length), len(collapsed))
    if end - start < width and start > 0:
        start = max(end - width, 0)

    excerpt = collapsed[start:end]

    if start > 0:
        excerpt = f"... {excerpt}"
    if end < len(collapsed):
        excerpt = f"{excerpt} ..."
    return excerpt
