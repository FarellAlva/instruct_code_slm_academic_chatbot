"""
_patch_refusal_penalty.py
==========================
Retroactively apply refusal penalty to existing CSV:
  - Set semantic_similarity = 0.0 for refusal answers
  - Set bert_f1 = 0.0 for refusal answers
  - Add 'refusal_detected' column for transparency

Then rebuild summary CSV and regenerate report.
"""
import os, sys, csv
sys.path.insert(0, 'd:\\LLM\\instruct')

CSV_PATH = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
RESULTS_DIR = 'd:\\LLM\\instruct\\eval\\results'

# Import refusal detection from evaluate module
from eval.evaluate import detect_refusal

# ── Load ──────────────────────────────────────────────────────────────────────
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

print(f"[Load] {len(rows)} rows loaded.\n")

# Add refusal_detected column if missing
if 'refusal_detected' not in fieldnames:
    fieldnames = list(fieldnames) + ['refusal_detected']

# ── Apply Refusal Penalty ─────────────────────────────────────────────────────
patched = 0
print("[Refusal Scan] Checking each answer for refusal patterns...\n")
for row in rows:
    model = row['model']
    qid   = row['question_id']
    answer = row.get('answer', '')
    is_refusal = detect_refusal(answer)
    row['refusal_detected'] = 'True' if is_refusal else 'False'

    if is_refusal:
        old_sem  = float(row.get('semantic_similarity', 0) or 0)
        old_bert = float(row.get('bert_f1', 0) or 0)
        row['semantic_similarity'] = 0.0
        row['bert_f1'] = 0.0
        patched += 1
        ans_preview = answer[:80].replace('\n', ' ')
        print(f"  [REFUSAL] {model:20s} Q{qid:02s}")
        print(f"           answer  : \"{ans_preview}...\"")
        print(f"           SemSim  : {old_sem:.4f} -> 0.0")
        print(f"           BERTScore: {old_bert:.4f} -> 0.0")
        print()

print(f"[Patch] {patched} refusal answers corrected.\n")

# ── Save patched CSV ──────────────────────────────────────────────────────────
with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"[Save] Patched CSV: {CSV_PATH}")

# ── Rebuild Summary ───────────────────────────────────────────────────────────
print("\n[Summary] Rebuilding summary CSV...")
import pandas as pd
df = pd.read_csv(CSV_PATH)

numeric_cols = [c for c in ['bert_f1','semantic_similarity','llm_judge_score','claude_judge_score',
                             'latency_s','throughput_tps','vram_peak_mb'] if c in df.columns]
agg = {c: 'mean' for c in numeric_cols}
agg['question_id'] = 'count'
summ = df.groupby('model').agg(agg).reset_index()
rename = {c: f"avg_{c}" for c in numeric_cols}
rename['question_id'] = 'num_questions'
summ.rename(columns=rename, inplace=True)

# context accuracy
ctx_pct = df.groupby('model')['context_has_answer'].apply(
    lambda x: round(x.astype(str).str.lower().eq('true').mean() * 100, 1)
).reset_index()
ctx_pct.columns = ['model', 'avg_context_precision_pct']
summ = summ.merge(ctx_pct, on='model')

summary_path = os.path.join(RESULTS_DIR, 'results_summary_20260526_013647.csv')
summ.to_csv(summary_path, index=False)
print(f"[Save] Summary: {summary_path}")

# ── Regenerate Report ─────────────────────────────────────────────────────────
print("\n[Report] Generating final report with refusal penalty applied...")
from eval.report import generate_report
from datetime import datetime

raw_rows_dict  = df.to_dict('records')
summ_dict      = summ.to_dict('records')
report_md      = generate_report(raw_rows_dict, summ_dict)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path  = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(report_md)

print(f"\n[Done] Report: {out_path}")

# ── Final Summary ──────────────────────────────────────────────────────────────
print("\n=== FINAL SUMMARY (with Refusal Penalty + XLM-RoBERTa) ===")
print(f"{'Model':<20} {'SemSim':>8} {'Gemini':>8} {'Claude':>8} {'BERTScore':>10} {'Refusals':>10}")
print("-" * 70)
refusal_counts = df[df['refusal_detected'].astype(str).str.lower() == 'true'].groupby('model').size().to_dict()
for r in summ_dict:
    g  = float(r.get('avg_llm_judge_score', -1))
    c  = float(r.get('avg_claude_judge_score', -1))
    s  = float(r.get('avg_semantic_similarity', 0))
    b  = float(r.get('avg_bert_f1', 0))
    rc = refusal_counts.get(r['model'], 0)
    print(f"{r['model']:<20} {s:>8.4f} {g:>8.1f} {c:>8.1f} {b:>10.4f} {rc:>10}")
