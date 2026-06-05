from infra.telemetry import get_logger

from brain.obsidian import ObsidianVault
from brain.qdrant import QdrantStore
from brain.schema import Note

logger = get_logger("brain.librarian")


class Librarian:
    def __init__(self, qdrant: QdrantStore, obsidian: ObsidianVault):
        self._qdrant = qdrant
        self._obsidian = obsidian

    def query(self, question: str, top_k: int = 5) -> list[Note]:
        results = self._qdrant.search(question, top_k=top_k)
        seen = {note.title for note in results}
        enriched = list(results)

        for note in results:
            for backlink_note in self._obsidian.find_backlinks(note.title):
                if backlink_note.title not in seen:
                    seen.add(backlink_note.title)
                    enriched.append(backlink_note)

        logger.info(
            "query returned %d notes (%d from search, %d from backlinks)",
            len(enriched),
            len(results),
            len(enriched) - len(results),
        )
        return enriched
