import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import get_settings


_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _collection_name(agent_id: str) -> str:
    return f"agent_{agent_id.replace('-', '_')}"


def get_or_create_collection(agent_id: str):
    client = get_chroma_client()
    name = _collection_name(agent_id)
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def add_memory(agent_id: str, text: str, metadata: dict = None, doc_id: str = None):
    import uuid
    collection = get_or_create_collection(agent_id)
    if doc_id is None:
        doc_id = str(uuid.uuid4())
    collection.upsert(
        documents=[text],
        metadatas=[metadata or {}],
        ids=[doc_id],
    )


def search_memory(agent_id: str, query: str, n_results: int = 5) -> List[str]:
    collection = get_or_create_collection(agent_id)
    count = collection.count()
    if count == 0:
        return []
    actual_n = min(n_results, count)
    results = collection.query(
        query_texts=[query],
        n_results=actual_n,
    )
    docs = results.get("documents", [[]])[0]
    return docs


def delete_agent_collection(agent_id: str):
    client = get_chroma_client()
    name = _collection_name(agent_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
