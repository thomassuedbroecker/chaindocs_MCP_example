from __future__ import annotations

import logging
from typing import Any, Callable

from .config import Settings, get_settings
from .document_store import DocumentStore
from .errors import LangChainDocumentsMCPError
from .logging_config import configure_logging

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - import errors handled at runtime
    FastMCP = None  # type: ignore[assignment]


def _handle_tool_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, LangChainDocumentsMCPError):
        return {"ok": False, "error": exc.to_payload()}
    logger.exception("Unexpected error while executing MCP tool", exc_info=exc)
    return {"ok": False, "error": {"code": "internal_error", "message": str(exc), "details": {}}}


def _safe_call(fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        payload = fn(*args, **kwargs)
        return {"ok": True, "result": payload}
    except Exception as exc:  # pragma: no cover - defensive wrapper
        return _handle_tool_error(exc)


def create_server(settings: Settings | None = None) -> Any:
    cfg = settings or get_settings()
    configure_logging(cfg.log_level)

    if FastMCP is None:
        raise RuntimeError("mcp package is not installed. Install dependencies first.")

    store = DocumentStore(settings=cfg)
    logger.info("Indexed documents", extra=store.reload())

    mcp = FastMCP(
        name="langchain-documents-mcp-server",
        host=cfg.mcp_host,
        port=cfg.mcp_port,
        log_level=cfg.log_level.upper(),
        streamable_http_path=cfg.mcp_streamable_http_path,
        stateless_http=cfg.mcp_stateless_http,
        json_response=cfg.mcp_json_response,
    )

    def server_info_tool() -> dict[str, Any]:
        return _safe_call(
            lambda: {
                "server": "langchain-documents-mcp-server",
                "settings": cfg.masked(),
                "transport": cfg.mcp_transport,
                "streamable_http_url": cfg.streamable_http_url,
                "indexed_documents": store.stats()["document_count"],
                "indexed_chunks": store.stats()["chunk_count"],
            }
        )

    def reload_documents_tool() -> dict[str, Any]:
        return _safe_call(store.reload)

    def list_documents_tool() -> dict[str, Any]:
        return _safe_call(store.list_documents)

    def search_documents_tool(query: str, limit: int = 5) -> dict[str, Any]:
        return _safe_call(store.search, query=query, limit=limit)

    def read_document_tool(source: str) -> dict[str, Any]:
        return _safe_call(store.read_document, source=source)

    def get_document_chunk_tool(chunk_id: str) -> dict[str, Any]:
        return _safe_call(store.get_chunk, chunk_id=chunk_id)

    mcp.tool(name="server_info")(server_info_tool)
    mcp.tool(name="reload_documents")(reload_documents_tool)
    mcp.tool(name="list_documents")(list_documents_tool)
    mcp.tool(name="search_documents")(search_documents_tool)
    mcp.tool(name="read_document")(read_document_tool)
    mcp.tool(name="get_document_chunk")(get_document_chunk_tool)
    return mcp


def run(settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    server = create_server(cfg)
    server.run(transport=cfg.mcp_transport)
