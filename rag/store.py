"""
rag/store.py — ChromaDB persistence layer.

Handles creating/loading the vector collection and ingesting chunks.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any

from config import CHROMA_DIR, CHROMA_COLLECTION
from .embedder import get_embedding_function

# Module-level singleton — client and collection created only once per process
_chroma_client = None
_chroma_collection = None

def get_chroma_collection(persist_dir: str = CHROMA_DIR):
    """
    Return (or create) a persistent ChromaDB collection.

    The collection uses our local embedding function so queries
    and documents are always embedded with the same model.

    Singleton pattern: client and collection are created once per process
    to avoid reconnection overhead on every retrieval call.
    """
    global _chroma_client, _chroma_collection

    if _chroma_collection is not None:
        return _chroma_collection

    embedding_fn = get_embedding_function()

    _chroma_client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )

    _chroma_collection = _chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    print(
        f"[Store] ✅ Collection '{CHROMA_COLLECTION}' ready "
        f"| docs stored: {_chroma_collection.count()}"
    )
    return _chroma_collection


def add_documents_to_db(
    chunks: List[Dict[str, Any]],
    collection=None,
    batch_size: int = 64,
) -> None:
    """
    Upsert a list of chunk dicts into the ChromaDB collection.

    Duplicate chunk_ids are silently overwritten (upsert semantics).
    """
    if collection is None:
        collection = get_chroma_collection()

    total = len(chunks)
    print(f"[Store] 📥 Inserting {total} chunks in batches of {batch_size}…")

    # Metadata fields to persist (beyond source/page) for pre-retrieval filtering
    _META_KEYS = ("prodi", "prodi_full", "semester", "hari",
                  "mata_kuliah", "dosen_names", "doc_type", "suspicious")

    from rag.sanitize import sanitize_context_chunk

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        metadatas = []
        clean_docs = []
        for c in batch:
            clean_text, is_suspicious, reasons = sanitize_context_chunk(c["text"])
            clean_docs.append(clean_text)

            meta = {
                "source": c["source"],
                "page": c["page"],
                "suspicious": "true" if is_suspicious else "false",
            }
            if is_suspicious:
                print(f"[Store] ⚠️ Ingested chunk flagged suspicious ({reasons}): {c.get('source')}")

            for key in _META_KEYS:
                if key in c and c[key] and key != "suspicious":
                    value = str(c[key])
                    # Store dosen_names lowercased for case-insensitive filtering
                    if key == "dosen_names":
                        value = value.lower()
                    meta[key] = value
            metadatas.append(meta)

        collection.upsert(
            ids        = [c["chunk_id"] for c in batch],
            documents  = clean_docs,
            metadatas  = metadatas,
        )
        print(f"[Store] ✅ Batch {i // batch_size + 1}: inserted {len(batch)} chunks.")

    print(f"[Store] 🎉 Done. Total docs in collection: {collection.count()}")


def clear_collection(collection=None) -> None:
    """Remove all documents from the collection (developer utility)."""
    if collection is None:
        collection = get_chroma_collection()
    ids = collection.get()["ids"]
    if ids:
        collection.delete(ids=ids)
        print(f"[Store] 🗑 Deleted {len(ids)} documents.")
    else:
        print("[Store] Collection is already empty.")
