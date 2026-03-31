# LangChain Documents MCP Server

Example MCP server that loads local `.md` and `.txt` files with LangChain, splits them into chunks, and exposes simple search tools over Streamable HTTP.

## Architecture Overview

`MCP Client -> FastMCP Server -> DocumentStore -> LangChain loaders/splitters -> Local documents`

Module responsibilities:
- `config.py`: typed settings loaded from `.env`.
- `document_store.py`: document loading, chunking, indexing, and search.
- `server.py`: FastMCP server creation and tool registration.
- `scripts/*`: setup, run, and test wrappers.

## Prerequisites

- Python 3.11+
- A client that can connect to Streamable HTTP MCP servers

## Quick Start

```bash
cd /Users/thomassuedbroecker/Documents/dev/gpt_codex/langchain-documents-mcp-server
./scripts/setup.sh
./scripts/run_local.sh
```

The first command creates `.venv`, installs dependencies, and creates `.env` from `.env.example` if needed.

## Configuration

Edit `.env` if you want to change the transport, endpoint, document directory, or chunking behavior:

- `MCP_TRANSPORT`: defaults to `streamable-http`
- `MCP_HOST`: bind host for the HTTP server
- `MCP_PORT`: bind port for the HTTP server
- `MCP_STREAMABLE_HTTP_PATH`: Streamable HTTP endpoint path
- `MCP_STATELESS_HTTP`: use stateless HTTP mode
- `MCP_JSON_RESPONSE`: use JSON responses instead of SSE framing
- `DOCUMENTS_PATH`: directory to scan for `.md` and `.txt` files
- `ALLOWED_EXTENSIONS`: comma-separated suffixes
- `CHUNK_SIZE`: LangChain chunk size
- `CHUNK_OVERLAP`: overlap between chunks
- `MAX_RESULTS`: default search limit

Default values point at `sample_documents/`, and the server listens on `http://127.0.0.1:8000/mcp` after setup.

## Run The Server

```bash
./scripts/run_local.sh
```

This starts the MCP server over Streamable HTTP.

You can also run the entrypoint directly:

```bash
source .venv/bin/activate
python -m langchain_documents_mcp_server.main
```

## Available MCP Tools

- `server_info()`
- `reload_documents()`
- `list_documents()`
- `search_documents(query, limit=5)`
- `read_document(source)`
- `get_document_chunk(chunk_id)`

## Example Client Command

If your MCP client accepts an HTTP MCP endpoint, point it at the default URL:

```bash
http://127.0.0.1:8000/mcp
```

If you prefer to set `MCP_TRANSPORT=http_streamable`, the config normalizes that alias to the SDK's `streamable-http` transport name.

## Test Commands

```bash
./scripts/test.sh
```

## Open-Source Dependencies

This example is intended for a public GitHub repository and is limited to open-source libraries.

Direct runtime dependencies currently used by the example:

- `mcp` - MIT
- `pydantic` - MIT
- `pydantic-settings` - MIT
- `langchain-core` - MIT
- `langchain-community` - MIT
- `langchain-text-splitters` - MIT

The repository itself is licensed under MIT in `LICENSE`.

To re-audit the environment locally:

```bash
source .venv/bin/activate
python scripts/check_licenses.py --scope all-installed
```

The audit uses installed package metadata and fails if a dependency cannot be verified as open source.

## Sample Workflow

1. Start the server with `./scripts/run_local.sh`.
2. Connect an MCP client.
3. Call `list_documents()`.
4. Call `search_documents(query="setup")`.
5. Call `read_document(source="getting-started.md")`.

## Troubleshooting

- Import errors:
  - Run `./scripts/setup.sh` and confirm `.venv` exists.
- Empty search results:
  - Confirm `DOCUMENTS_PATH` contains `.md` or `.txt` files.
- Config validation errors:
  - Verify the directory in `DOCUMENTS_PATH` exists.
