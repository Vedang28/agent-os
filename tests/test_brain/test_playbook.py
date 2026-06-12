import pytest

from brain.obsidian import ObsidianVault
from brain.playbook import PLAYBOOK_TAG, get_all_playbooks, get_playbooks
from brain.schema import Note


@pytest.fixture()
def vault(tmp_path):
    return ObsidianVault(tmp_path / "vault")


def _write_playbook(vault, title, department, content="When X, do Y"):
    note = Note(
        title=title,
        content=content,
        tags=[PLAYBOOK_TAG, f"{PLAYBOOK_TAG}/{department}"],
    )
    vault.write_note(note)


class TestPlaybook:
    def test_get_playbooks_for_department(self, vault):
        _write_playbook(vault, "Playbook: eng tip", "engineering")
        _write_playbook(vault, "Playbook: intel tip", "intelligence")
        eng = get_playbooks("engineering", vault)
        assert len(eng) == 1
        assert "eng_tip" in eng[0].title

    def test_get_playbooks_nonexistent_department(self, vault):
        _write_playbook(vault, "Playbook: eng tip", "engineering")
        result = get_playbooks("nonexistent", vault)
        assert result == []

    def test_get_all_playbooks(self, vault):
        _write_playbook(vault, "Playbook: eng tip", "engineering")
        _write_playbook(vault, "Playbook: intel tip", "intelligence")
        all_pb = get_all_playbooks(vault)
        assert len(all_pb) == 2

    @pytest.mark.asyncio
    async def test_proposer_reads_playbooks(self, vault):
        _write_playbook(
            vault,
            "Playbook: engineering failure pattern",
            "engineering",
            content="When tests fail, check imports first.",
        )

        from agents.departments.engineering.architect import Architect

        architect = Architect(librarian=None, obsidian=vault)
        result = await architect.run({"request": "build feature"})
        assert len(result["brain_context"]) >= 1
        playbook_titles = [ctx["title"] for ctx in result["brain_context"]]
        assert any("failure_pattern" in t for t in playbook_titles)
