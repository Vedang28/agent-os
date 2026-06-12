from brain.obsidian import ObsidianVault
from brain.schema import Note
from infra.telemetry import get_logger

logger = get_logger("brain.playbook")

PLAYBOOK_TAG = "playbook"


def get_playbooks(department: str, obsidian: ObsidianVault) -> list[Note]:
    tag = f"{PLAYBOOK_TAG}/{department}"
    results = []
    for title in obsidian.list_notes():
        if not title.startswith("Playbook_"):
            continue
        try:
            note = obsidian.read_note(title)
            if tag in note.tags:
                results.append(note)
        except Exception:
            logger.warning("skipping malformed playbook note: %s", title)
    return results


def get_all_playbooks(obsidian: ObsidianVault) -> list[Note]:
    results = []
    for title in obsidian.list_notes():
        if not title.startswith("Playbook_"):
            continue
        try:
            note = obsidian.read_note(title)
            if PLAYBOOK_TAG in note.tags:
                results.append(note)
        except Exception:
            logger.warning("skipping malformed playbook note: %s", title)
    return results
