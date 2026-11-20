import sys
import csv
sys.path.insert(0, '.')
from rag.retriever import retrieve_context

with open('eval/ground_truth.csv', encoding='utf-8') as f:
    questions = list(csv.DictReader(f))

for q in questions:
    qid = int(q['id'])
    qtext = q['question']
    ref = q['reference_answer']
    res = retrieve_context(qtext, top_k=6)
    chunks = res['chunks']
    full_ctx = res['context'].lower()
    
    words = [w.lower().strip('.,():;"\'') for w in ref.split() if len(w) > 4]
    matched = [w for w in set(words) if w in full_ctx]
    coverage = len(matched) / len(set(words)) if words else 0
    
    print(f"=== Q{qid:02d}: {qtext} ===")
    print(f"Category: {q['category']} | Complexity: {q['complexity']}")
    print(f"Ref answer: {ref}")
    print(f"Coverage: {coverage:.1%} ({len(matched)}/{len(set(words))})")
    print(f"Missing key terms: {set(words) - set(matched)}")
    print("Retrieved chunks:")
    for i, c in enumerate(chunks, 1):
        first_line = c['text'].strip().split('\n')[0][:90]
        score = c.get('rerank_score', 0)
        src = c.get('source', '')
        print(f"  #{i} [score={score:.2f}] {src} -> {first_line}")
    print("-" * 60)
