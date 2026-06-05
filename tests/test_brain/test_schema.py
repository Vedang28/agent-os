from datetime import datetime, timezone

from brain.schema import Note


def test_note_creation():
    note = Note(title="Test", content="Hello world", tags=["a", "b"])
    assert note.title == "Test"
    assert note.content == "Hello world"
    assert note.tags == ["a", "b"]


def test_note_defaults():
    note = Note(title="T", content="C")
    assert note.tags == []
    assert note.backlinks == []
    assert note.embedding is None


def test_note_created_at_default():
    before = datetime.now(timezone.utc)
    note = Note(title="T", content="C")
    after = datetime.now(timezone.utc)
    assert before <= note.created_at <= after


def test_note_with_embedding():
    note = Note(title="T", content="C", embedding=[0.1, 0.2, 0.3])
    assert note.embedding == [0.1, 0.2, 0.3]
