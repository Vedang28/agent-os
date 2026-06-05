import pytest

from brain.obsidian import ObsidianVault
from brain.schema import Note


@pytest.fixture()
def vault(tmp_path):
    return ObsidianVault(vault_path=tmp_path)


def test_write_and_read_note(vault):
    note = Note(title="Hello", content="World", tags=["test"])
    vault.write_note(note)
    result = vault.read_note("Hello")
    assert result.title == "Hello"
    assert result.content == "World"
    assert result.tags == ["test"]


def test_list_notes(vault):
    for title in ["A", "B", "C"]:
        vault.write_note(Note(title=title, content=f"content {title}"))
    titles = vault.list_notes()
    assert len(titles) == 3
    assert set(titles) == {"A", "B", "C"}


def test_read_missing_note_raises(vault):
    with pytest.raises(FileNotFoundError):
        vault.read_note("nonexistent")


def test_find_backlinks(vault):
    vault.write_note(Note(title="A", content="Links to [[B]] here"))
    vault.write_note(Note(title="B", content="No links"))
    backlinks = vault.find_backlinks("B")
    assert len(backlinks) == 1
    assert backlinks[0].title == "A"


def test_path_traversal_blocked(vault):
    with pytest.raises((PermissionError, ValueError)):
        vault.read_note("../../etc/passwd")


def test_write_creates_vault_dir(tmp_path):
    vault_dir = tmp_path / "new_vault"
    vault = ObsidianVault(vault_path=vault_dir)
    vault.write_note(Note(title="First", content="Created"))
    assert vault_dir.exists()
    result = vault.read_note("First")
    assert result.content == "Created"


def test_backlinks_extracted_from_content(vault):
    vault.write_note(Note(title="Note1", content="See [[Note2]] and [[Note3]]"))
    result = vault.read_note("Note1")
    assert set(result.backlinks) == {"Note2", "Note3"}
