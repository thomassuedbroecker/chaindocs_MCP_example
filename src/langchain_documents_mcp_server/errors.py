class LangChainDocumentsMCPError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(LangChainDocumentsMCPError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("configuration_error", message, details)


class DocumentNotFoundError(LangChainDocumentsMCPError):
    def __init__(self, source: str) -> None:
        super().__init__("document_not_found", f"Document not found: {source}", {"source": source})


class ChunkNotFoundError(LangChainDocumentsMCPError):
    def __init__(self, chunk_id: str) -> None:
        super().__init__("chunk_not_found", f"Chunk not found: {chunk_id}", {"chunk_id": chunk_id})
