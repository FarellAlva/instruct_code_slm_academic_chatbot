"""
eval/evaluate.py
================
Script evaluasi multi-model RAG untuk chatbot akademik Pradita University.
Mengikuti metodologi paper Hendra Lijaya et al. (SISFOKOM 2025):

Metrik:
  - Semantic Similarity (cosine similarity via embeddings)
  - LLM-as-a-Judge     (skor 0-100 dari Ollama LLM judge)
  - RAG Context Diagnostics (context_has_answer, context_similarity)
  - Latency   (detik per inference)
  - Throughput (token/detik dari Ollama API)
  - VRAM peak (MB, dari nvidia-smi)

Model yang dievaluasi:
  - gemma2:2b
  - qwen3:1.7B
  - llama3.2:1b  (alias: meta-llama/Llama-3.2-1B-Instruct @ Ollama)

Output:
  - eval/results/results_raw.csv   — data mentah per (model, pertanyaan)
  - eval/results/results_summary.csv — rata-rata per model

Referensi:
  Hendra Lijaya et al., "Comparative Analysis of RAG-Based Open-Source LLMs
  for Indonesian Banking Customer Service Optimization Using Simulated Data",
  Jurnal SISFOKOM, Vol.14, No.03, 2025.
"""

import os, sys, csv, time, json, subprocess, re
from datetime import datetime

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(EVAL_DIR)
sys.path.insert(0, PROJECT_DIR)

RESULTS_DIR = os.path.join(EVAL_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MODELS = [
    "gemma2:2b",
    "qwen3:1.7B",
    "llama3.2:1b",
]

# LLM Judge model — uses the best available local model for judging
LLM_JUDGE_MODEL = "llama3.2:1b"

# Ollama inference params shared
TEMPERATURE = 0.1    # sangat rendah untuk jawaban deterministik
TOP_P       = 0.9

# Per-model overrides
MODEL_CONFIG: dict[str, dict] = {
    "gemma2:2b":   {"num_predict": 2048},
    "qwen3:1.7B":  {"num_predict": 2048},
    "llama3.2:1b": {"num_predict": 2048},
}

OLLAMA_API  = "http://localhost:11434"

# ─── Imports ─────────────────────────────────────────────────────────────────
print("[Setup] Loading evaluation libraries...")

from rag.retriever import retrieve_context

print("[Setup] All libraries loaded.\n")

# ─── Embedding Model for Semantic Similarity ──────────────────────────────────
_EMBED_MODEL = None

def _get_embed_model():
    """Lazy-load the embedding model (same as RAG pipeline)."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        from config import EMBEDDING_MODEL
        print(f"[SemSim] Loading embedding model: {EMBEDDING_MODEL}")
        _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL)
    return _EMBED_MODEL


# ─── Refusal Detection ────────────────────────────────────────────────────────
# Embedding-based metrics (SemSim, BERTScore) cannot distinguish between
# "I don't know" and an actual answer because they measure topical proximity,
# not factual completeness. A refusal and its reference both share the same
# topic embedding space → inflated scores.
#
# Fix: detect refusal patterns and override scores to 0.0.

_REFUSAL_PHRASES = [
    "maaf sobat, saya tidak memiliki informasi",
    "maaf, saya tidak memiliki informasi",
    "saya tidak memiliki informasi tersebut",
    "saya tidak memiliki informasi",
    "tidak ada informasi yang relevan",
    "tidak dapat menemukan informasi",
    "tidak memiliki cukup informasi",
    "informasi tidak tersedia",
    "maaf, tidak ada data",
    "saya tidak dapat menjawab",
    "tidak tersedia dalam konteks",
    "tidak ada dalam konteks",
    "tidak ada dalam dokumen",
    "tidak ada informasi tentang",
]


def detect_refusal(answer: str) -> bool:
    """
    Detect if the model answered with a refusal/"I don't know" response.
    Returns True if a known refusal pattern is found.

    Why this matters:
      BERTScore and SemSim measure embedding proximity, not factual accuracy.
      A refusal like 'Maaf saya tidak tahu jadwal' still scores ~0.90 SemSim
      against the schedule reference because both texts share the same TOPIC.
      Detecting refusals lets us assign the correct score of 0.0.
    """
    if not answer:
        return True  # empty answer is always a refusal
    lower = answer.lower().strip()
    for phrase in _REFUSAL_PHRASES:
        if phrase in lower:
            return True
    return False


def compute_semantic_similarity(text_a: str, text_b: str, penalize_refusal: bool = True) -> float:
    """
    Compute cosine similarity between two texts using the project's
    embedding model (intfloat/multilingual-e5-base).

    Following the paper methodology (Section E, lines 397-445):
    'Unlike traditional metrics based on n-grams or word overlap (such as
    BLEU or ROUGE), the semantic similarity approach captures semantic
    nuances and contextual alignment.'

    IMPORTANT: Embedding-based metrics measure *topical proximity*, not
    factual correctness. A refusal answer ("Maaf, saya tidak tahu") can
    still score high because it shares the same topic as the reference.
    When penalize_refusal=True (default), refusals are assigned 0.0.

    Returns float 0.0 - 1.0
    """
    if not text_a or not text_b:
        return 0.0

    # Refusal penalty: if model says it doesn't know, score = 0.0
    if penalize_refusal and detect_refusal(text_a):
        return 0.0

    model = _get_embed_model()
    embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
    # Cosine similarity of normalized vectors = dot product
    similarity = float(embeddings[0] @ embeddings[1])
    return round(max(0.0, min(1.0, similarity)), 4)


# ─── LLM-as-a-Judge ──────────────────────────────────────────────────────────

_LLM_JUDGE_PROMPT = """Kamu adalah evaluator AI yang objektif. Nilailah kualitas JAWABAN MODEL berikut dibandingkan REFERENSI (ground truth).

PERTANYAAN: {question}

JAWABAN MODEL:
{answer}

REFERENSI (Ground Truth):
{reference}

Berikan skor 0-100 berdasarkan kriteria berikut:
- Akurasi faktual (40%): Apakah fakta dalam jawaban sesuai referensi? Ada info salah/halusinasi?
- Kelengkapan (30%): Apakah semua poin penting dari referensi tercakup?
- Relevansi (20%): Apakah jawaban fokus pada pertanyaan yang diajukan?
- Kejelasan (10%): Apakah jawaban mudah dipahami dan terstruktur baik?

ATURAN PENILAIAN:
- Skor 90-100: Jawaban sangat akurat, lengkap, dan jelas
- Skor 70-89: Jawaban cukup baik dengan sedikit kekurangan
- Skor 50-69: Jawaban sebagian benar tapi ada hal penting yang kurang
- Skor 30-49: Jawaban kurang akurat atau banyak yang hilang
- Skor 0-29: Jawaban salah, tidak relevan, atau halusinasi berat

Jawab HANYA dalam format JSON berikut (tanpa markdown codeblock):
{{"score": <angka 0-100>, "reasoning": "<penjelasan singkat 1-2 kalimat>"}}"""


def llm_judge_evaluate(
    question: str,
    answer: str,
    reference: str,
    judge_model: str = LLM_JUDGE_MODEL,
) -> dict:
    """
    Skip local Ollama judge call so Gemini can evaluate it later.
    Returns dummy values.
    """
    return {"score": -1, "reasoning": "Menunggu evaluasi dari Gemini Judge", "error": None}


# ─── Dataset ──────────────────────────────────────────────────────────────────
def load_dataset() -> list[dict]:
    csv_path = os.path.join(EVAL_DIR, "ground_truth.csv")
    dataset = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset.append({
                "id": int(row["id"]),
                "question": row["question"],
                "category": row["category"],
                "complexity": row["complexity"],
                "reference_answer": row["reference_answer"]
            })
    return dataset


# ─── BERTScore (load once) ────────────────────────────────────────────────────
# (BLEU and ROUGE removed — following paper recommendation)


# ─── Helper: VRAM via nvidia-smi ─────────────────────────────────────────────
def get_vram_mb() -> float:
    """Return current GPU VRAM usage in MB. Returns -1 if unavailable."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=5,
        )
        return float(out.decode().strip().split("\n")[0])
    except Exception:
        return -1.0


# ─── Helper: Strip Thinking Tags ─────────────────────────────────────────────
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

def _strip_thinking(text: str) -> str:
    """
    Strip qwen3-style <think>...</think> blocks from model output.
    Returns only the final answer portion, stripped of whitespace.
    """
    cleaned = _THINK_RE.sub("", text)
    return cleaned.strip()


# ─── System prompt khusus untuk evaluasi (lebih ringkas dari chatbot) ─────────
_EVAL_SYSTEM_PROMPT = (
    "Kamu adalah asisten akademik AI Pradita University.\n"
    "Tugas: Jawab PERTANYAAN YANG DIAJUKAN berdasarkan KONTEKS yang diberikan.\n"
    "Jika informasi tidak ada di konteks, jawab: 'Maaf sobat, saya tidak memiliki informasi tersebut.'\n"
    "Jawab langsung dan ringkas. Bahasa Indonesia. Gunakan tabel Markdown jika ada banyak data."
)


# ─── Helper: Generate answer via Ollama /api/generate ─────────────────────────
def generate_answer(model: str, prompt: str, context: str) -> dict:
    """
    Call Ollama /api/generate with the system prompt + context + user question.
    Supports per-model token budget via MODEL_CONFIG.
    For qwen3 (thinking ON): strips <think>...</think> tags before returning answer.
    Returns dict with: answer, raw_answer, latency_s, throughput_tps, prompt_tokens, completion_tokens
    """
    import urllib.request

    # Per-model token budget
    model_cfg = MODEL_CONFIG.get(model, {"num_predict": 512})
    num_predict = model_cfg.get("num_predict", 512)

    full_prompt = (
        f"KONTEKS:\n{context}\n\n"
        f"PERTANYAAN: {prompt}\n\n"
        "Jawab pertanyaan di atas berdasarkan konteks yang diberikan."
    )

    payload_dict = {
        "model": model,
        "system": _EVAL_SYSTEM_PROMPT,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": num_predict,
            "top_p": TOP_P,
        },
    }
    payload = json.dumps(payload_dict).encode()

    req = urllib.request.Request(
        f"{OLLAMA_API}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t_start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode()
            result = json.loads(raw)
    except Exception as e:
        latency = time.time() - t_start
        return {
            "answer": f"[ERROR: {e}]",
            "raw_answer": f"[ERROR: {e}]",
            "latency_s": latency,
            "throughput_tps": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "error": str(e),
        }

    latency = time.time() - t_start

    # Ollama returns eval_count (completion tokens) and eval_duration (nanoseconds)
    completion_tokens = result.get("eval_count", 0)
    eval_duration_ns  = result.get("eval_duration", 1)
    throughput_tps    = completion_tokens / (eval_duration_ns / 1e9) if eval_duration_ns > 0 else 0.0
    prompt_tokens     = result.get("prompt_eval_count", 0)

    raw_answer = result.get("response", "").strip()

    # Strip <think>...</think> blocks (qwen3 thinking mode)
    clean_answer = _strip_thinking(raw_answer)

    if raw_answer and not clean_answer:
        print(f"    [WARN] {model} Q: thinking-only response (no final answer after stripping). "
              f"raw_len={len(raw_answer)}, num_predict={num_predict}")

    return {
        "answer": clean_answer,
        "raw_answer": raw_answer,
        "latency_s": latency,
        "throughput_tps": round(throughput_tps, 2),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "error": None,
    }


# BERTScore dihapus — metrik ini tidak dapat mendeteksi halusinasi secara akurat
# dan digantikan sepenuhnya oleh Dual LLM Judge (Gemini + Claude Sonnet).


# ─── RAG Context Diagnostics ─────────────────────────────────────────────────

def diagnose_context(context: str, reference: str, chunks: list) -> dict:
    """
    Diagnose whether the retrieved RAG context contains the answer.

    This helps distinguish:
    - context_has_answer=True + low score -> model hallucination problem
    - context_has_answer=False -> retrieval problem (RAG didn't find data)

    Returns dict with: context_has_answer, context_similarity, num_chunks, context_preview
    """
    if not context:
        return {
            "context_has_answer": False,
            "context_similarity": 0.0,
            "num_chunks_retrieved": 0,
            "context_preview": "",
        }

    # Method 1: Semantic similarity between context and reference
    context_sim = compute_semantic_similarity(context[:2000], reference)

    # Method 2: Key phrase overlap check
    # Extract key phrases from reference (numbers, proper nouns, etc.)
    ref_lower = reference.lower()
    ctx_lower = context.lower()

    # Check for numeric values (times, prices, etc.)
    ref_numbers = set(re.findall(r'\d+[\.,]?\d*', reference))
    ctx_numbers = set(re.findall(r'\d+[\.,]?\d*', context))
    number_overlap = len(ref_numbers & ctx_numbers) / max(len(ref_numbers), 1)

    # Check for key terms (proper nouns, specific terms)
    ref_words = set(w for w in reference.split() if len(w) > 3)
    ctx_words = set(w for w in context.split() if len(w) > 3)
    word_overlap = len(ref_words & ctx_words) / max(len(ref_words), 1)

    # Context "has answer" if semantic similarity is high enough
    # OR if there's significant key-phrase overlap
    has_answer = (
        context_sim >= 0.65
        or (number_overlap >= 0.5 and word_overlap >= 0.3)
        or word_overlap >= 0.5
    )

    return {
        "context_has_answer": has_answer,
        "context_similarity": context_sim,
        "num_chunks_retrieved": len(chunks) if chunks else 0,
        "context_preview": context[:200].replace("\n", " "),
    }


# ─── Main Evaluation Loop ─────────────────────────────────────────────────────
def run_evaluation(dry_run: bool = False, question_ids: list[int] = None):
    """
    Run full evaluation across all models and questions.

    Args:
        dry_run: If True, only run 1 model x 3 questions.
        question_ids: If set, only evaluate specific question IDs.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_csv_path = os.path.join(RESULTS_DIR, f"results_raw_{timestamp}.csv")
    summary_csv_path = os.path.join(RESULTS_DIR, f"results_summary_{timestamp}.csv")

    dataset = load_dataset()
    if question_ids:
        dataset = [qa for qa in dataset if qa["id"] in question_ids]
    if dry_run:
        dataset = dataset[:3]
        models = MODELS[:1]
    else:
        models = MODELS

    print("=" * 70)
    print(f"  Pradita University RAG Evaluation")
    print(f"  Methodology: Paper-aligned (Semantic Similarity + LLM-as-a-Judge)")
    print(f"  Mode: {'DRY RUN' if dry_run else 'FULL'}")
    print(f"  Models: {models}")
    print(f"  Judge Model: {LLM_JUDGE_MODEL}")
    print(f"  Questions: {len(dataset)}")
    print(f"  Total inference calls: {len(models) * len(dataset)}")
    print("=" * 70)

    # CSV columns (paper-aligned)
    fieldnames = [
        "model", "question_id", "question", "category", "complexity",
        "answer", "raw_answer", "reference_answer",
        # Paper metrics
        "semantic_similarity", "llm_judge_score", "llm_judge_reasoning",
        # RAG Context Diagnostics
        "context_has_answer", "context_similarity", "num_chunks_retrieved", "context_preview",
        # Performance metrics
        "latency_s", "throughput_tps", "prompt_tokens", "completion_tokens",
        "vram_mb_before", "vram_mb_after", "vram_peak_mb",
        "thinking_tokens",
        "error",
    ]

    all_rows = []

    for model in models:
        print(f"\n{'='*70}")
        print(f"  Model: {model}")
        print(f"{'='*70}")

        model_hypotheses = []
        model_references = []
        model_rows = []

        for qa in dataset:
            qid    = qa["id"]
            question = qa["question"]
            reference = qa["reference_answer"]
            model_cfg = MODEL_CONFIG.get(model, {"num_predict": 512})
            print(f"\n  Q{qid:02d} [{qa['complexity']:10s}] {question[:60]}...")
            print(f"    Config: num_predict={model_cfg.get('num_predict', 512)}")

            # Retrieve context from RAG
            try:
                rag_result = retrieve_context(question, top_k=6)
                context = rag_result.get("context", "")
                chunks = rag_result.get("chunks", [])
            except Exception as e:
                print(f"    [RAG ERROR] {e}")
                context = ""
                chunks = []

            # RAG Context Diagnostics
            ctx_diag = diagnose_context(context, reference, chunks)
            ctx_status = "✅ FOUND" if ctx_diag["context_has_answer"] else "❌ MISSING"
            print(f"    Context: {ctx_status} (sim={ctx_diag['context_similarity']:.3f}, "
                  f"chunks={ctx_diag['num_chunks_retrieved']})")

            # Measure VRAM before
            vram_before = get_vram_mb()

            # Generate answer
            result = generate_answer(model, question, context)

            # Measure VRAM after
            vram_after = get_vram_mb()
            vram_peak  = max(vram_before, vram_after) if vram_before >= 0 else -1

            answer     = result["answer"]
            raw_answer = result.get("raw_answer", answer)

            # Estimate thinking tokens
            think_blocks = _THINK_RE.findall(raw_answer)
            thinking_chars = sum(len(b) for b in think_blocks)
            thinking_tokens_est = thinking_chars // 4

            print(f"    Latency: {result['latency_s']:.2f}s | Throughput: {result['throughput_tps']:.1f} tok/s")
            if thinking_tokens_est > 0:
                print(f"    Thinking tokens (est): ~{thinking_tokens_est} | Answer tokens: ~{result['completion_tokens'] - thinking_tokens_est}")
            print(f"    Answer preview: {answer[:120] if answer else '[EMPTY - only thinking, no final answer]'}")

            # Compute Semantic Similarity (paper methodology)
            sem_sim = compute_semantic_similarity(answer, reference)
            print(f"    Semantic Similarity: {sem_sim:.4f}")

            # LLM-as-a-Judge evaluation
            print(f"    [Judge] Evaluating with {LLM_JUDGE_MODEL}...")
            judge_result = llm_judge_evaluate(question, answer, reference)
            judge_score = judge_result["score"]
            judge_reasoning = judge_result["reasoning"]
            if judge_result["error"]:
                print(f"    [Judge] ⚠ Error: {judge_result['error']}")
            else:
                print(f"    [Judge] Score: {judge_score}/100 — {judge_reasoning[:80]}")

            row = {
                "model": model,
                "question_id": qid,
                "question": question,
                "category": qa["category"],
                "complexity": qa["complexity"],
                "answer": answer,
                "raw_answer": raw_answer,
                "reference_answer": reference,
                # Paper metrics
                "semantic_similarity": sem_sim,
                "llm_judge_score": judge_score,
                "llm_judge_reasoning": judge_reasoning,
                # RAG Context Diagnostics
                "context_has_answer": ctx_diag["context_has_answer"],
                "context_similarity": ctx_diag["context_similarity"],
                "num_chunks_retrieved": ctx_diag["num_chunks_retrieved"],
                "context_preview": ctx_diag["context_preview"],
                # Performance
                "latency_s": round(result["latency_s"], 3),
                "throughput_tps": result["throughput_tps"],
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "vram_mb_before": vram_before,
                "vram_mb_after": vram_after,
                "vram_peak_mb": vram_peak,
                "thinking_tokens": thinking_tokens_est,
                "error": result.get("error") or "",
            }

            model_rows.append(row)

        all_rows.extend(model_rows)

    # Write raw CSV
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n[Output] Raw results saved: {raw_csv_path}")

    # Compute and write summary
    summary_rows = _compute_summary(all_rows, models)
    summary_fields = [
        "model",
        "avg_semantic_similarity", "avg_llm_judge_score",
        "context_accuracy_pct",
        "avg_latency_s", "avg_throughput_tps", "avg_vram_peak_mb",
        "num_questions", "num_errors",
    ]
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"[Output] Summary saved: {summary_csv_path}")

    # Print summary table
    print(f"\n{'='*80}")
    print("  SUMMARY TABLE (Paper-Aligned Metrics)")
    print(f"{'='*80}")
    print(f"{'Model':<35} {'SemSim':>8} {'Judge':>8} {'Ctx%':>6} {'Latency':>10} {'Tok/s':>8}")
    print("-" * 80)
    for s in summary_rows:
        print(
            f"{s['model']:<35} "
            f"{s['avg_semantic_similarity']:>8.4f} "
            f"{s['avg_llm_judge_score']:>8.1f} "
            f"{s['context_accuracy_pct']:>5.1f}% "
            f"{s['avg_latency_s']:>9.2f}s "
            f"{s['avg_throughput_tps']:>8.1f}"
        )

    return raw_csv_path, summary_csv_path


def _compute_summary(rows: list[dict], models: list[str]) -> list[dict]:
    summaries = []
    for model in models:
        model_rows = [r for r in rows if r["model"] == model]
        if not model_rows:
            continue

        def safe_avg(key):
            vals = [r[key] for r in model_rows if r[key] not in (None, -1, -1.0)]
            return round(sum(vals) / len(vals), 4) if vals else -1.0

        # Context accuracy: % of questions where context contained the answer
        ctx_vals = [r["context_has_answer"] for r in model_rows]
        ctx_accuracy = round(sum(1 for v in ctx_vals if v) / max(len(ctx_vals), 1) * 100, 1)

        summaries.append({
            "model": model,
            "avg_semantic_similarity": safe_avg("semantic_similarity"),
            "avg_llm_judge_score": safe_avg("llm_judge_score"),
            "context_accuracy_pct": ctx_accuracy,
            "avg_latency_s": safe_avg("latency_s"),
            "avg_throughput_tps": safe_avg("throughput_tps"),
            "avg_vram_peak_mb": safe_avg("vram_peak_mb"),
            "num_questions": len(model_rows),
            "num_errors": sum(1 for r in model_rows if r["error"]),
        })
    return summaries


# ─── CLI Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Multi-Model Evaluation (Paper-Aligned)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run only 1 model x 3 questions (quick test)")
    parser.add_argument("--questions", type=int, nargs="+",
                        help="Evaluate specific question IDs only, e.g. --questions 7 10 14")
    parser.add_argument("--judge-model", type=str, default=LLM_JUDGE_MODEL,
                        help=f"Ollama model for LLM-as-a-Judge (default: {LLM_JUDGE_MODEL})")
    args = parser.parse_args()

    if args.judge_model:
        LLM_JUDGE_MODEL = args.judge_model

    run_evaluation(dry_run=args.dry_run, question_ids=args.questions)
