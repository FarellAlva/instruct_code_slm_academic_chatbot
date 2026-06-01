import csv

rows = list(csv.DictReader(open('eval/results/results_raw_20260531_222243.csv', encoding='utf-8')))
llama = [r for r in rows if r['model'] == 'llama3.2:1b']
print("=== llama3.2:1b answers (new run) ===")
for r in llama:
    ans = r['answer'].replace('\n',' ').strip()[:150]
    ss = float(r['semantic_similarity'])
    qid = r['question_id']
    print(f"Q{qid:>2} | SemSim={ss:.4f} | {ans}")
