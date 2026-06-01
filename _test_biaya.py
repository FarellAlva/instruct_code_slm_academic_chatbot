import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag.retriever import retrieve_context

print("=== TEST RAG: Biaya Information Technology ===")
r = retrieve_context("berapa biaya kuliah program studi information technology atau teknik informatika?", top_k=4)

print("\n--- RAG Context ---")
for chunk in r["chunks"]:
    print(f"Source: {chunk['source']} | Score: {chunk.get('rerank_score', 0)}")
    print(chunk["text"])
    print("-" * 50)
