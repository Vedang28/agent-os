import hashlib
import math
import uuid
from collections.abc import Callable

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from infra.telemetry import get_logger

from brain.schema import Note

logger = get_logger("brain.qdrant")

EmbedFn = Callable[[str], list[float]]

NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def hash_embed(text: str, dim: int = 128) -> list[float]:
    tokens = text.lower().split() or [""]
    vector = [0.0] * dim
    for token in tokens:
        raw = b""
        counter = 0
        while len(raw) < dim:
            raw += hashlib.sha256(f"{token}:{counter}".encode()).digest()
            counter += 1
        for i in range(dim):
            vector[i] += (raw[i] / 127.5) - 1.0
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


class QdrantStore:
    def __init__(
        self,
        client: QdrantClient | None = None,
        collection_name: str = "brain_notes",
        embed_fn: EmbedFn = hash_embed,
        vector_size: int = 128,
    ):
        self._client = client or QdrantClient(url="localhost", port=6333)
        self._collection = collection_name
        self._embed_fn = embed_fn
        self._vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self._client.get_collections().collections]
        if self._collection not in collections:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )
            logger.info("created collection: %s", self._collection)

    def embed_note(self, note: Note) -> None:
        vector = self._embed_fn(note.content)
        point_id = str(uuid.uuid5(NAMESPACE, note.title))
        payload = {
            "title": note.title,
            "content": note.content,
            "tags": note.tags,
            "backlinks": note.backlinks,
            "created_at": note.created_at.isoformat(),
        }
        self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        logger.info("embedded note: %s", note.title)

    def search(self, query: str, top_k: int = 5) -> list[Note]:
        vector = self._embed_fn(query)
        results = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
        )
        notes = []
        for point in results.points:
            p = point.payload
            notes.append(
                Note(
                    title=p["title"],
                    content=p["content"],
                    tags=p.get("tags", []),
                    backlinks=p.get("backlinks", []),
                    created_at=p.get("created_at"),
                )
            )
        return notes
