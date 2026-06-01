import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import _expand_query

test_queries = [
    "where does pradita located in?",
    "what is the tuition fee?",
    "how to register at pradita?",
    "ada berapa jurusan di pradita?",      # Indonesia — should NOT expand
    "siapa dosen informatika?",             # Indonesia — should NOT expand
    "what facilities does pradita have?",
    "is there a dormitory near campus?",
    "who is the lecturer for this class?",
    "scholarship available?",
]

for q in test_queries:
    expanded = _expand_query(q)
    changed = "✅ expanded" if expanded != q else "➖ unchanged"
    print(f"\n{changed}: {q!r}")
    if expanded != q:
        print(f"  → '{expanded}'")
