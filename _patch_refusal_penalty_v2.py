"""
_patch_refusal_penalty_v2.py
============================
Improved refusal penalty using dual LLM judge consensus as ground truth.

Strategy:
  - Regex refusal detection alone has false positives (e.g. answers that say
    "Maaf, tidak tahu X" but then provide correct info for Y).
  - Ground truth: if BOTH Gemini AND Claude give score <= threshold (e.g. <= 10),
    the answer is a definite failure -> override SemSim = 0.0 and BERTScore = 0.0.
  - Additionally, detect pure refusals (answer < 200 chars AND contains refusal phrase).

This ensures we don't penalize answers that are partially correct.
"""
import os, sys, csv
sys.path.insert(0, 'd:\\LLM\\instruct')

CSV_PATH     = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
RESULTS_DIR  = 'd:\\LLM\\instruct\\eval\\results'

# ── Refusal detection (strict version) ────────────────────────────────────────
_REFUSAL_PHRASES = [
    "maaf sobat, saya tidak memiliki informasi",
    "maaf, saya tidak memiliki informasi",
    "saya tidak memiliki informasi tersebut",
    "tidak ada informasi tentang jadwal",
    "tidak ada informasi yang relevan",
    "tidak dapat menemukan informasi",
    "saya tidak dapat menjawab",
    "tidak ada dalam konteks yang diberikan",
]

JUDGE_CONSENSUS_THRESHOLD = 10   # both judges <= this -> total failure
MAX_LEN_FOR_SHORT_REFUSAL  = 200  # short answers with refusal phrase = definite fail


def is_definite_failure(answer: str, gemini_score: float, claude_score: float) -> tuple[bool, str]:
    """
    Determine if an answer is a definite failure using two strategies:
    1. JUDGE CONSENSUS: both Gemini and Claude <= threshold (most reliable)
    2. SHORT REFUSAL: answer is short AND starts with a refusal phrase

    Returns (is_failure, reason)
    """
    # Strategy 1: LLM Judge consensus (most reliable)
    if gemini_score <= JUDGE_CONSENSUS_THRESHOLD and claude_score <= JUDGE_CONSENSUS_THRESHOLD:
        return True, f"Judge consensus fail (Gemini={gemini_score:.0f}, Claude={claude_score:.0f})"

    # Strategy 2: Short answer with refusal phrase at start
    if len(answer.strip()) < MAX_LEN_FOR_SHORT_REFUSAL:
        lower = answer.lower().strip()
        for phrase in _REFUSAL_PHRASES:
            if phrase in lower:
                return True, f"Short refusal detected (len={len(answer.strip())}, phrase='{phrase[:40]}')"

    return False, ""


# ── Load ──────────────────────────────────────────────────────────────────────
# First, reload original scores from the raw CSV (before previous patch)
# We need to re-run on the patched CSV, so let's restore SemSim/BERTScore
# from Claude judge scores (since those were set correctly)
# Actually: we'll reload from CSV and check refusal_detected column to restore

with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    rows = list(reader)

print(f"[Load] {len(rows)} rows loaded.\n")

if 'refusal_detected' not in fieldnames:
    fieldnames.append('refusal_detected')
if 'failure_reason' not in fieldnames:
    fieldnames.append('failure_reason')

# ── Reload original BERTScore and SemSim from the inject script (before patch) ──
# We have the original values in gemini_judge_results.csv or we recompute
# Actually, the simplest thing: re-run XLM-R BERTScore computation on the fly
# for patched rows, OR just note that for judge-consensus rows we set to 0 anyway

print("[Recovery] Restoring original SemSim/BERTScore from pre-patch values...")
print("  (Rows that were incorrectly zeroed will be restored from embedding computation)\n")

# We need to restore original values for false positives before re-applying correct penalty
# The original values were overwritten. Let's recompute for ALL rows to get fresh values.
from eval.evaluate import _get_embed_model, detect_refusal
from bert_score import score as bert_score_fn
import torch

# Compute fresh SemSim for all rows
model = _get_embed_model()
print("[SemSim] Computing fresh semantic similarity (no refusal penalty)...")

answers    = [r['answer'] for r in rows]
references = [r['reference_answer'] for r in rows]

# Batch encode
import numpy as np
all_texts = answers + references
embeddings = model.encode(all_texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
n = len(rows)
ans_emb = embeddings[:n]
ref_emb = embeddings[n:]

raw_semsim = []
for a_e, r_e in zip(ans_emb, ref_emb):
    sim = float(np.clip(a_e @ r_e, 0.0, 1.0))
    raw_semsim.append(round(sim, 4))

print(f"[SemSim] Done. {len(raw_semsim)} scores computed.\n")

# Compute fresh BERTScore
print("[BERTScore] Computing fresh XLM-RoBERTa scores...")
device = 'cuda' if torch.cuda.is_available() else 'cpu'
_, _, F1 = bert_score_fn(
    answers, references,
    model_type='xlm-roberta-base',
    num_layers=9,
    verbose=False,
    device=device,
)
raw_bert = [round(f.item(), 4) for f in F1]
print(f"[BERTScore] Done.\n")

# ── Apply failure detection ────────────────────────────────────────────────────
print("[Patch] Applying failure penalty with dual-judge consensus strategy...\n")

patched = 0
for i, row in enumerate(rows):
    model_name  = row['model']
    qid         = row['question_id']
    answer      = row.get('answer', '')
    gemini_s    = float(row.get('llm_judge_score', -1) or -1)
    claude_s    = float(row.get('claude_judge_score', -1) or -1)

    # Restore fresh (unpenalized) scores
    row['semantic_similarity'] = raw_semsim[i]
    row['bert_f1']             = raw_bert[i]

    is_fail, reason = is_definite_failure(answer, gemini_s, claude_s)
    row['refusal_detected'] = 'True' if is_fail else 'False'
    row['failure_reason']   = reason

    if is_fail:
        patched += 1
        print(f"  [FAIL] {model_name:20s} Q{qid:02s}  |  {reason}")
        print(f"         SemSim  : {raw_semsim[i]:.4f} -> 0.0")
        print(f"         BERTScore: {raw_bert[i]:.4f} -> 0.0")
        print(f"         Preview : \"{answer[:80].replace(chr(10),' ')}\"")
        print()
        row['semantic_similarity'] = 0.0
        row['bert_f1']             = 0.0

print(f"[Patch] {patched} failure answers corrected (out of {len(rows)} total).\n")

# ── Save ──────────────────────────────────────────────────────────────────────
with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"[Save] Patched CSV: {CSV_PATH}")

# ── Rebuild Summary ────────────────────────────────────────────────────────────
import pandas as pd
df = pd.read_csv(CSV_PATH)

numeric_cols = [c for c in ['bert_f1','semantic_similarity','llm_judge_score','claude_judge_score',
                             'latency_s','throughput_tps','vram_peak_mb'] if c in df.columns]
agg  = {c: 'mean' for c in numeric_cols}
agg['question_id'] = 'count'
summ = df.groupby('model').agg(agg).reset_index()
rename = {c: f"avg_{c}" for c in numeric_cols}
rename['question_id'] = 'num_questions'
summ.rename(columns=rename, inplace=True)

ctx_pct = df.groupby('model')['context_has_answer'].apply(
    lambda x: round(x.astype(str).str.lower().eq('true').mean() * 100, 1)
).reset_index()
ctx_pct.columns = ['model', 'avg_context_precision_pct']
summ = summ.merge(ctx_pct, on='model')

summary_path = os.path.join(RESULTS_DIR, 'results_summary_20260526_013647.csv')
summ.to_csv(summary_path, index=False)
print(f"[Save] Summary: {summary_path}")

# ── Report ─────────────────────────────────────────────────────────────────────
from eval.report import generate_report
from datetime import datetime
report_md = generate_report(df.to_dict('records'), summ.to_dict('records'))
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path  = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(report_md)
print(f"\n[Done] Report: {out_path}")

# ── Final Table ────────────────────────────────────────────────────────────────
print("\n=== FINAL SUMMARY (Judge Consensus Penalty + XLM-RoBERTa) ===")
print(f"{'Model':<20} {'SemSim':>8} {'Gemini':>8} {'Claude':>8} {'BERTScore':>10} {'Failures':>10}")
print("-" * 70)
fail_counts = df[df['refusal_detected'].astype(str).str.lower() == 'true'].groupby('model').size().to_dict()
for r in summ.to_dict('records'):
    g  = float(r.get('avg_llm_judge_score', -1))
    c  = float(r.get('avg_claude_judge_score', -1))
    s  = float(r.get('avg_semantic_similarity', 0))
    b  = float(r.get('avg_bert_f1', 0))
    fc = fail_counts.get(r['model'], 0)
    print(f"{r['model']:<20} {s:>8.4f} {g:>8.1f} {c:>8.1f} {b:>10.4f} {fc:>10}")
