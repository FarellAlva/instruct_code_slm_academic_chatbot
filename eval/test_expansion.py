import sys
sys.path.insert(0, '.')
from rag.retriever import retrieve_context

print("=== Testing Q15 with 'student boarding house cluster alloggio' ===")
q15 = "Apakah ada asrama atau tempat tinggal yang disediakan oleh Pradita University untuk mahasiswanya? student boarding house cluster alloggio"
res15 = retrieve_context(q15, top_k=6)
for i, c in enumerate(res15["chunks"], 1):
    score = c.get("rerank_score", 0)
    first_line = c["text"].strip().split("\n")[0][:60]
    print(f"#{i} [{score:.2f}] {c.get('source')}: {first_line}")
    if "allog" in c["text"].lower():
        print(f"   -> FOUND ALLOGGIO IN CHUNK #{i}!")

print("\n=== Testing Q01 with 'scientia business park menara satu gading serpong kelapa gading' ===")
q01 = "Di mana lokasi kampus Pradita University? alamat scientia business park tower 1 menara satu gading serpong kelapa gading"
res01 = retrieve_context(q01, top_k=6)
for i, c in enumerate(res01["chunks"], 1):
    score = c.get("rerank_score", 0)
    first_line = c["text"].strip().split("\n")[0][:60]
    print(f"#{i} [{score:.2f}] {c.get('source')}: {first_line}")
    if "scientia" in c["text"].lower() or "menara satu" in c["text"].lower():
        print(f"   -> FOUND ADDRESS IN CHUNK #{i}!")
