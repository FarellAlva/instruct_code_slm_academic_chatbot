import sys
sys.path.insert(0, '.')
from rag.retriever import retrieve_context

print("--- Test top_k=8 on Q01 ---")
res8 = retrieve_context("Di mana lokasi kampus Pradita University?", top_k=8)
for i, c in enumerate(res8["chunks"], 1):
    score = c.get("rerank_score", 0)
    src = c.get("source", "")
    first_line = c["text"].strip().split("\n")[0][:60]
    print(f"#{i} [{score:.2f}] {src}: {first_line}")
    if "scientia" in c["text"].lower() or "menara satu" in c["text"].lower():
        print(f"   -> FOUND LOCATION IN CHUNK #{i}!")

print("\n--- Test top_k=8 on Q15 (Asrama) ---")
res15 = retrieve_context("Apakah ada asrama atau tempat tinggal yang disediakan oleh Pradita University untuk mahasiswanya?", top_k=8)
for i, c in enumerate(res15["chunks"], 1):
    score = c.get("rerank_score", 0)
    src = c.get("source", "")
    first_line = c["text"].strip().split("\n")[0][:60]
    print(f"#{i} [{score:.2f}] {src}: {first_line}")
    if "allog" in c["text"].lower() or "asrama" in c["text"].lower() or "tempat tinggal" in c["text"].lower():
        print(f"   -> FOUND HOUSING IN CHUNK #{i}!")
