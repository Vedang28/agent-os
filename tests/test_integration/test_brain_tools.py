import asyncio

import pytest
from qdrant_client import QdrantClient

from brain.librarian import Librarian
from brain.obsidian import ObsidianVault
from brain.qdrant import QdrantStore
from brain.schema import Note
from core.state import AgentState
from tools.base import set_permission_checker
from tools.bash import BashTool
from tools.file import FileTool
from tools.permissions import default_checker


@pytest.fixture(autouse=True)
def _reset_checker():
    set_permission_checker(None)
    yield
    set_permission_checker(None)


@pytest.fixture()
def brain(tmp_path):
    vault_path = tmp_path / "vault"
    client = QdrantClient(location=":memory:")
    qdrant = QdrantStore(client=client, collection_name="integration")
    obsidian = ObsidianVault(vault_path=vault_path)
    return Librarian(qdrant=qdrant, obsidian=obsidian), qdrant, obsidian


def test_agent_queries_brain_and_calls_tool(brain, tmp_path):
    lib, qdrant, obsidian = brain

    note = Note(title="Config", content="Database host is localhost port 5432")
    obsidian.write_note(note)
    qdrant.embed_note(note)

    context = lib.query("database connection")
    assert len(context) >= 1

    state: AgentState = {
        "request": "get db config",
        "brain_context": [n.model_dump(mode="json") for n in context],
    }
    assert len(state["brain_context"]) >= 1
    assert state["brain_context"][0]["title"] == "Config"

    file_tool = FileTool(allowed_root=tmp_path / "output")
    result = asyncio.run(
        file_tool.execute(
            operation="write",
            path="result.txt",
            content=state["brain_context"][0]["content"],
        )
    )
    assert "written" in result

    read_back = asyncio.run(
        file_tool.execute(operation="read", path="result.txt")
    )
    assert "localhost" in read_back


def test_permission_gate_blocks_shell():
    set_permission_checker(default_checker)
    bash = BashTool()
    with pytest.raises(PermissionError):
        asyncio.run(bash.execute(command="echo hello"))


def test_permission_gate_allows_with_custom_checker():
    set_permission_checker(lambda tool: True)
    bash = BashTool()
    result = asyncio.run(bash.execute(command="echo approved"))
    assert "approved" in result
