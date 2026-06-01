"""
_recompute_indobert.py
======================
Recompute BERTScore dari existing raw CSV menggunakan IndoBERT
(indobenchmark/indobert-base-p1) sebagai pengganti roberta-large.

Alasan penggantian:
  - roberta-large dilatih pada corpus English, sehingga memberi skor tinggi
    bahkan untuk jawaban "Maaf saya tidak tahu" vs referensi lengkap dalam BI.
  - IndoBERT dilatih pada Wikipedia + Common Crawl Bahasa Indonesia,
    sehingga lebih sensitif terhadap perbedaan semantik kalimat BI.

Setelah recompute, script akan regenerate report.md.
"""

import os, sys, csv
sys.path.insert(0, 'd:\\LLM\\instruct')

from bert_score import score as bert_score_fn
import torch

CSV_PATH = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
RESULTS_DIR = 'd:\\LLM\\instruct\\eval\\results'

def cuda_available():
    try:
        return torch.cuda.is_available()
    except Exception:
        return False

# ── Load existing CSV ──────────────────────────────────────────────────────────
print("[Load] Reading CSV...")
with open(CSV_PATH, encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())
print(f"[Load] {len(rows)} rows loaded.")

# Check if claude columns exist; if not add them
if 'claude_judge_score' not in fieldnames:
    fieldnames.extend(['claude_judge_score', 'claude_judge_reasoning'])

# ── Compute IndoBERT BERTScore ─────────────────────────────────────────────────
print("[BERTScore] Computing with XLM-RoBERTa-base (multilingual, termasuk Bahasa Indonesia)...")
print("  Model: xlm-roberta-base — dilatih pada CC-100 (100 bahasa incl. Indonesian)")
print("  Lebih akurat untuk BI vs roberta-large (English-only)")
print("  Kompatibel dengan torch 2.5.x (safetensors format)\n")

hypotheses = [row['answer'] for row in rows]
references  = [row['reference_answer'] for row in rows]

valid_indices = [i for i, h in enumerate(hypotheses) if h and not h.startswith('[ERROR')]
invalid_indices = [i for i in range(len(rows)) if i not in valid_indices]

print(f"  Valid: {len(valid_indices)}, Invalid/Empty: {len(invalid_indices)}")

valid_hyps = [hypotheses[i] for i in valid_indices]
valid_refs  = [references[i]  for i in valid_indices]

device = 'cuda' if cuda_available() else 'cpu'
print(f"  Device: {device}\n")

P, R, F1 = bert_score_fn(
    valid_hyps,
    valid_refs,
    model_type='xlm-roberta-base',
    num_layers=9,   # penultimate layer (XLM-R base has 12 layers)
    verbose=True,
    device=device,
)

# ── Write results back ──────────────────────────────────────────────────────────
indobert_scores = {i: -1.0 for i in range(len(rows))}
for rank, orig_i in enumerate(valid_indices):
    indobert_scores[orig_i] = round(F1[rank].item(), 4)

print("\n[Write] Updating bert_f1 with IndoBERT scores...")
for i, row in enumerate(rows):
    old = float(row.get('bert_f1', -1) or -1)
    new = indobert_scores[i]
    row['bert_f1'] = new
    model = row['model']
    qid   = row['question_id']
    if abs(old - new) > 0.02:  # print only significant changes
        print(f"  {model:20s} Q{qid:02s}: roberta={old:.4f} -> xlm-r={new:.4f}  d={new-old:+.4f}")

with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n[Save] Updated CSV: {CSV_PATH}")

# ── Print comparison by model ───────────────────────────────────────────────────
print("\n=== BERTScore IndoBERT Summary (per model) ===")
from collections import defaultdict
model_scores = defaultdict(list)
for i, row in enumerate(rows):
    s = indobert_scores[i]
    if s >= 0:
        model_scores[row['model']].append(s)

for model, scores in sorted(model_scores.items()):
    avg = sum(scores) / len(scores)
    print(f"  {model:20s} avg IndoBERT F1: {avg:.4f}  (n={len(scores)})")

# ── Rebuild summary CSV ─────────────────────────────────────────────────────────
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
# compute context accuracy
ctx_pct = df.groupby('model')['context_has_answer'].apply(
    lambda x: round(x.astype(str).str.lower().eq('true').mean() * 100, 1)
).reset_index()
ctx_pct.columns = ['model', 'avg_context_precision_pct']
summ = summ.merge(ctx_pct, on='model')

summary_path = os.path.join(RESULTS_DIR, 'results_summary_20260526_013647.csv')
summ.to_csv(summary_path, index=False)
print(f"[Save] Summary CSV: {summary_path}")

# ── Regenerate report ───────────────────────────────────────────────────────────
print("\n[Report] Generating final report with dual judge + IndoBERT...")
from eval.report import generate_report
from datetime import datetime

raw_rows_dict = df.to_dict('records')
summ_dict = summ.to_dict('records')
report_md = generate_report(raw_rows_dict, summ_dict)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(report_md)

print(f"\n[Done] Report generated: {out_path}")
print("\n=== FINAL DUAL JUDGE + IndoBERT SUMMARY ===")
print(f"{'Model':<20} {'SemSim':>8} {'Gemini':>8} {'Claude':>8} {'IndoBERT':>10}")
print("-" * 60)
for r in summ_dict:
    g = float(r.get('avg_llm_judge_score', -1))
    c = float(r.get('avg_claude_judge_score', -1))
    s = float(r.get('avg_semantic_similarity', 0))
    b = float(r.get('avg_bert_f1', 0))
    print(f"{r['model']:<20} {s:>8.4f} {g:>8.1f} {c:>8.1f} {b:>10.4f}")
