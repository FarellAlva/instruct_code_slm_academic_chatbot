import sys
sys.path.insert(0, '.')
from rag.store import get_chroma_collection

col = get_chroma_collection()
print(f"Total docs in collection: {col.count()}")

for term in ['Scientia', 'Allog', 'Menara Satu', 'Conceptual Study']:
    res = col.get(where_document={"$contains": term})
    docs = res["documents"]
    metas = res["metadatas"]
    ids = res["ids"]
    print(f"\n--- Term: '{term}' (found {len(docs)} chunks) ---")
    for doc_id, doc, meta in zip(ids, docs, metas):
        src = meta.get("source", "unknown")
        first_line = doc.strip().split("\n")[0][:80]
        print(f"ID: {doc_id} | src: {src}")
        print(f"Snippet: {first_line}")
        print(f"Length: {len(doc)} chars")
