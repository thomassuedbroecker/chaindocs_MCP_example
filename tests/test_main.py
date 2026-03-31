import runpy


def test_main_module_calls_run(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("langchain_documents_mcp_server.server.run", lambda: calls.append("run"))

    runpy.run_module("langchain_documents_mcp_server.main", run_name="__main__")

    assert calls == ["run"]
