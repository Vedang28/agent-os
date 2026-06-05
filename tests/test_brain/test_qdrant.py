import math

from qdrant_client import QdrantClient

from brain.qdrant import QdrantStore, hash_embed
from brain.schema import Note


def _make_store():
    client = QdrantClient(location=":memory:")
    return QdrantStore(client=client, collection_name="test_notes")


def test_embed_and_search():
    store = _make_store()
    note = Note(title="Python", content="Python is a programming language")
    store.embed_note(note)
    results = store.search("programming language", top_k=5)
    assert len(results) >= 1
    assert results[0].title == "Python"


def test_search_returns_top_k():
    store = _make_store()
    for i in range(10):
        store.embed_note(Note(title=f"Note{i}", content=f"topic number {i} content"))
    results = store.search("topic", top_k=3)
    assert len(results) == 3


def test_search_empty_collection():
    store = _make_store()
    results = store.search("anything")
    assert results == []


def test_embed_overwrites():
    store = _make_store()
    store.embed_note(Note(title="Same", content="old content about cats"))
    store.embed_note(Note(title="Same", content="new content about dogs"))
    results = store.search("dogs", top_k=1)
    assert len(results) == 1
    assert "dogs" in results[0].content


def test_hash_embed_deterministic():
    a = hash_embed("hello world")
    b = hash_embed("hello world")
    assert a == b


def test_hash_embed_normalized():
    vec = hash_embed("test embedding normalization")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6
