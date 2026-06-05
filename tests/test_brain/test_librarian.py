import pytest
from qdrant_client import QdrantClient

from brain.librarian import Librarian
from brain.obsidian import ObsidianVault
from brain.qdrant import QdrantStore
from brain.schema import Note


@pytest.fixture()
def brain(tmp_path):
    client = QdrantClient(location=":memory:")
    qdrant = QdrantStore(client=client, collection_name="test_lib")
    obsidian = ObsidianVault(vault_path=tmp_path)
    return Librarian(qdrant=qdrant, obsidian=obsidian), qdrant, obsidian


def test_query_returns_relevant_notes(brain):
    lib, qdrant, obsidian = brain
    note = Note(title="Python Guide", content="Python is a programming language")
    obsidian.write_note(note)
    qdrant.embed_note(note)

    results = lib.query("programming language")
    assert any(n.title == "Python Guide" for n in results)


def test_query_includes_backlinks(brain):
    lib, qdrant, obsidian = brain
    note_a = Note(title="NoteA", content="See [[NoteB]] for more")
    note_b = Note(title="NoteB", content="Core concepts here")
    obsidian.write_note(note_a)
    obsidian.write_note(note_b)
    qdrant.embed_note(note_a)
    qdrant.embed_note(note_b)

    results = lib.query("Core concepts")
    titles = {n.title for n in results}
    assert "NoteB" in titles
    assert "NoteA" in titles


def test_query_empty_brain(brain):
    lib, _, _ = brain
    results = lib.query("anything")
    assert results == []


def test_query_deduplicates(brain):
    lib, qdrant, obsidian = brain
    note = Note(title="Unique", content="Unique content with [[Unique]] self-ref")
    obsidian.write_note(note)
    qdrant.embed_note(note)

    results = lib.query("unique content")
    title_counts = [n.title for n in results].count("Unique")
    assert title_counts == 1
