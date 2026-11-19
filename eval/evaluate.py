"""
eval/evaluate.py  (versi robust)
================================
Evaluasi multi-model RAG: gemma2:2b, qwen3:1.7B, llama3.2:1b dengan N run per pertanyaan.

Prinsip desain
--------------
1. Kegagalan INFRASTRUKTUR (timeout, koneksi putus, HTTP error, JSON rusak) di-retry otomatis
   dengan parameter & seed yang sama. Baris yang tetap gagal setelah semua retry ditandai
   status="failed", TIDAK PERNAH dirata-ratakan, dan skrip keluar dengan kode 2 (tidak diam-diam).
2. Hasil buruk dari MODEL (jawaban kosong setelah <think> dibuang, terpotong, penolakan) adalah
   data yang sah. Semuanya dicatat dan dihitung secara eksplisit, bukan disembunyikan.
   Re-sampling jawaban kosong hanya jika diminta (--retry-no-answer N) dan tercatat di `attempts`.
3. Setiap sel (model, pertanyaan, run) ditulis ke raw.jsonl segera setelah selesai, sehingga
   crash atau Ctrl+C tidak menghilangkan data. `--resume DIR` hanya mengisi sel yang belum ada/gagal.
4. Konteks RAG diambil SEKALI per pertanyaan dan dipakai untuk semua model dan run (disimpan di
   contexts.json). Kegagalan retrieval menghentikan skrip; tidak ada konteks kosong diam-diam.
5. Urutan: model -> run -> pertanyaan, dengan warm-up per model. Prompt identik tidak pernah
   berurutan, sehingga cache prompt Ollama tidak membiasakan latency run 2..N.
6. Seed per run dicatat (seed = SEED_BASE + run_idx) agar bisa direproduksi.
7. Statistik: rata-rata per pertanyaan dulu, lalu SD antar-pertanyaan (n = jumlah pertanyaan)
   dan SD antar-run (dari rata-rata keseluruhan tiap run).
8. Output ditulis ke folder baru results/run_<timestamp>/ dan tidak menimpa hasil lama.
"""

import os, sys, csv, time, json, subprocess, re, statistics, argparse
import urllib.request, urllib.error
from datetime import datetime

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(EVAL_DIR)
sys.path.insert(0, PROJECT_DIR)
RESULTS_ROOT = os.path.join(EVAL_DIR, "results")

# ─── Konfigurasi eksperimen ──────────────────────────────────────────────────
MODELS = ["gemma2:2b", "qwen3:1.7B", "llama3.2:1b"]
THINKING_MODELS = {"qwen3:1.7B"}      # model yang dipanggil dengan think=True (eksplisit)

TEMPERATURE = 0.4
NUM_CTX     = 2048
NUM_PREDICT = 2048
TOP_P       = 0.9
NUM_RUNS    = 5
SEED_BASE   = 0                       # seed run ke-i = SEED_BASE + i  (1..N)
KEEP_ALIVE  = "10m"
TOP_K_RETRIEVAL = 6

MAX_ATTEMPTS    = 3                   # untuk kegagalan infrastruktur
REQUEST_TIMEOUT = 300                 # detik
OLLAMA_API = os.environ.get("OLLAMA_API", "http://localhost:11434")

# Jika retriever memakai prefix E5 ("query: " / "passage: "), samakan di sini.
EMBED_PREFIX = ""

_EVAL_SYSTEM_PROMPT = (
    "Kamu adalah asisten akademik AI Pradita University.\n"
    "Tugas: Jawab PERTANYAAN YANG DIAJUKAN berdasarkan KONTEKS yang diberikan.\n"
    "Jika informasi tidak ada di konteks, jawab: 'Maaf sobat, saya tidak memiliki informasi tersebut.'\n"
    "Jawab langsung dan ringkas. Bahasa Indonesia. Gunakan tabel Markdown jika ada banyak data."
)

_REFUSAL_PHRASES = [
    "maaf sobat, saya tidak memiliki informasi", "maaf, saya tidak memiliki informasi",
    "saya tidak memiliki informasi tersebut", "saya tidak memiliki informasi",
    "tidak ada informasi yang relevan", "tidak dapat menemukan informasi",
    "tidak memiliki cukup informasi", "informasi tidak tersedia", "maaf, tidak ada data",
    "saya tidak dapat menjawab", "tidak tersedia dalam konteks", "tidak ada dalam konteks",
    "tidak ada dalam dokumen", "tidak ada informasi tentang", "tidak disebutkan dalam dokumen",
]

RAW_FIELDS = [
    "model", "question_id", "run_idx", "seed", "attempts", "status",
    "question", "category", "complexity", "answer", "raw_answer", "reference_answer",
    "semantic_similarity", "refusal_detected", "no_final_answer", "truncated", "ctx_overflow",
    "context_has_answer", "context_similarity", "num_chunks_retrieved",
    "latency_s", "throughput_tps", "prompt_tokens", "completion_tokens",
    "thinking_tokens_est", "answer_tokens_est", "done_reason",
    "vram_mb_before", "vram_mb_after", "error", "timestamp",
]
METRICS = ["semantic_similarity", "latency_s", "throughput_tps", "completion_tokens"]


# ─── Utilitas ────────────────────────────────────────────────────────────────
def log(msg=""):
    print(msg, flush=True)


def mean_sd(values):
    v = [x for x in values if x is not None]
    if not v:
        return None, None
    return statistics.fmean(v), (statistics.stdev(v) if len(v) > 1 else 0.0)


def rnd(x, n=4):
    return None if x is None else round(x, n)


def http_json(path, payload=None, timeout=REQUEST_TIMEOUT):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        OLLAMA_API + path, data=data, headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get_vram_mb():
    """Pemakaian VRAM seluruh GPU saat ini (bukan puncak, bukan khusus Ollama). -1 jika tidak ada."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], timeout=5)
        return float(out.decode().strip().split("\n")[0])
    except Exception:
        return -1.0


# ─── Embedding & semantic similarity ────────────────────────────────────────
_EMBED_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        from config import EMBEDDING_MODEL
        log(f"[SemSim] Loading embedding model: {EMBEDDING_MODEL}")
        _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL)
    return _EMBED_MODEL


def detect_refusal(answer):
    """True jika jawaban non-kosong memuat frasa penolakan. Jawaban kosong ditangani terpisah."""
    if not answer:
        return False
    lower = answer.lower()
    return any(p in lower for p in _REFUSAL_PHRASES)


def compute_semantic_similarity(text_a, text_b):
    """Cosine similarity murni (Persamaan 1). Tanpa penalti refusal. Teks kosong -> 0.0."""
    if not text_a or not text_b:
        return 0.0
    m = _get_embed_model()
    e = m.encode([EMBED_PREFIX + text_a, EMBED_PREFIX + text_b], normalize_embeddings=True)
    return round(max(0.0, min(1.0, float(e[0] @ e[1]))), 4)


def diagnose_context(context, reference, num_chunks):
    if not context:
        return {"context_has_answer": False, "context_similarity": 0.0, "num_chunks_retrieved": 0}
    sim = compute_semantic_similarity(context[:2000], reference)
    ref_nums = set(re.findall(r"\d+[\.,]?\d*", reference))
    ctx_nums = set(re.findall(r"\d+[\.,]?\d*", context))
    num_ov = len(ref_nums & ctx_nums) / max(len(ref_nums), 1)
    ref_w = set(w for w in reference.split() if len(w) > 3)
    ctx_w = set(w for w in context.split() if len(w) > 3)
    word_ov = len(ref_w & ctx_w) / max(len(ref_w), 1)
    has = sim >= 0.65 or (num_ov >= 0.5 and word_ov >= 0.3) or word_ov >= 0.5
    return {"context_has_answer": bool(has), "context_similarity": sim,
            "num_chunks_retrieved": num_chunks}


# ─── Pembuangan <think> ──────────────────────────────────────────────────────
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_RE = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)


def strip_thinking(text):
    return _UNCLOSED_THINK_RE.sub("", _THINK_RE.sub("", text)).strip()


# ─── Dataset ─────────────────────────────────────────────────────────────────
def load_dataset():
    with open(os.path.join(EVAL_DIR, "ground_truth.csv"), newline="", encoding="utf-8") as f:
        return [{"id": int(r["id"]), "question": r["question"], "category": r["category"],
                 "complexity": r["complexity"], "reference_answer": r["reference_answer"]}
                for r in csv.DictReader(f)]


# ─── Panggilan Ollama (melempar exception jika gagal) ───────────────────────
def build_options(temperature, seed, num_predict=NUM_PREDICT):
    return {"temperature": temperature, "top_p": TOP_P, "num_ctx": NUM_CTX,
            "num_predict": num_predict, "seed": seed}


def ollama_generate_once(model, prompt, system, temperature, seed, num_predict=NUM_PREDICT):
    payload = {"model": model, "system": system, "prompt": prompt, "stream": False,
               "keep_alive": KEEP_ALIVE, "options": build_options(temperature, seed, num_predict)}
    if model in THINKING_MODELS:
        payload["think"] = True
    t0 = time.time()
    result = http_json("/api/generate", payload, timeout=REQUEST_TIMEOUT)
    latency = time.time() - t0
    if "error" in result:
        raise RuntimeError(f"ollama error: {result['error']}")
    if "response" not in result:
        raise RuntimeError("ollama response missing 'response' field")
    return result, latency


def warm_up(model, temperature):
    """Muat model ke GPU dengan opsi identik (num_ctx sama agar tidak reload). Tidak dicatat."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            ollama_generate_once(model, "Halo", "Jawab singkat.", temperature, 0, num_predict=8)
            log(f"  [warm-up] {model} siap")
            return
        except Exception as e:
            log(f"  [warm-up] {model} percobaan {attempt}/{MAX_ATTEMPTS} gagal: {e}")
            time.sleep(5 * attempt)
    raise SystemExit(f"Warm-up gagal untuk {model}; periksa Ollama dan ketersediaan model.")


def run_cell(model, qa, run_idx, ctx, temperature, retry_no_answer):
    """Hasilkan satu baris data untuk (model, pertanyaan, run). Tidak melempar exception."""
    base_seed = SEED_BASE + run_idx
    prompt = (f"KONTEKS:\n{ctx['context']}\n\nPERTANYAAN: {qa['question']}\n\n"
              "Jawab pertanyaan di atas berdasarkan konteks yang diberikan.")
    attempts, no_answer_retries, last_err = 0, 0, ""
    seed_used = base_seed
    result = latency = None

    while attempts < MAX_ATTEMPTS + retry_no_answer:
        attempts += 1
        try:
            result, latency = ollama_generate_once(model, prompt, _EVAL_SYSTEM_PROMPT,
                                                   temperature, seed_used)
            last_err = ""
        except Exception as e:                       # kegagalan infrastruktur -> retry, seed sama
            last_err = f"{type(e).__name__}: {e}"
            result = None
            log(f"    ! percobaan {attempts} gagal ({last_err}); retry...")
            if attempts >= MAX_ATTEMPTS:
                break
            time.sleep(5 * attempts)
            continue

        clean = strip_thinking((result.get("response") or "").strip())
        if not clean and no_answer_retries < retry_no_answer:
            no_answer_retries += 1                   # opsional: re-sampling jawaban kosong
            seed_used = base_seed + 1000 * no_answer_retries
            log(f"    ! jawaban kosong; re-sample dengan seed {seed_used}")
            continue
        break

    row = {k: "" for k in RAW_FIELDS}
    row.update({"model": model, "question_id": qa["id"], "run_idx": run_idx, "seed": seed_used,
                "attempts": attempts, "question": qa["question"], "category": qa["category"],
                "complexity": qa["complexity"], "reference_answer": qa["reference_answer"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "context_has_answer": ctx["context_has_answer"],
                "context_similarity": ctx["context_similarity"],
                "num_chunks_retrieved": ctx["num_chunks_retrieved"]})

    if result is None:                               # tetap gagal setelah semua retry
        row.update({"status": "failed", "error": last_err})
        return row

    resp = (result.get("response") or "").strip()
    thinking_field = result.get("thinking") or ""
    clean = strip_thinking(resp)
    completion = int(result.get("eval_count", 0) or 0)
    eval_ns = result.get("eval_duration", 0) or 0
    prompt_tok = int(result.get("prompt_eval_count", 0) or 0)
    thinking_chars = len(thinking_field) + (len(resp) - len(clean))
    think_est = thinking_chars // 4                  # ESTIMASI kasar (4 karakter/token)
    done_reason = result.get("done_reason", "")

    row.update({
        "status": "ok" if clean else "no_final_answer",
        "answer": clean, "raw_answer": (f"<think>{thinking_field}</think>" if thinking_field else "") + resp,
        "semantic_similarity": compute_semantic_similarity(clean, qa["reference_answer"]),
        "refusal_detected": detect_refusal(clean),
        "no_final_answer": not clean,
        "truncated": done_reason == "length",
        "ctx_overflow": (prompt_tok + completion) >= NUM_CTX,
        "latency_s": round(latency, 3),
        "throughput_tps": round(completion / (eval_ns / 1e9), 2) if eval_ns > 0 else 0.0,
        "prompt_tokens": prompt_tok, "completion_tokens": completion,
        "thinking_tokens_est": think_est, "answer_tokens_est": max(0, completion - think_est),
        "done_reason": done_reason, "error": "",
    })
    return row


# ─── Penyimpanan ─────────────────────────────────────────────────────────────
def load_rows(jsonl_path):
    rows = {}
    if os.path.exists(jsonl_path):
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    rows[(r["model"], int(r["question_id"]), int(r["run_idx"]))] = r  # terakhir menang
    return rows


def append_row(jsonl_path, row):
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ─── Agregasi ────────────────────────────────────────────────────────────────
def usable(rows):
    """Baris yang boleh masuk statistik: bukan 'failed'."""
    return [r for r in rows if r["status"] != "failed"]


def per_question_summary(rows, models):
    out = []
    for m in models:
        mr = usable([r for r in rows if r["model"] == m])
        for qid in sorted({r["question_id"] for r in mr}):
            q = [r for r in mr if r["question_id"] == qid]
            rec = {"model": m, "question_id": qid, "n_runs": len(q),
                   "no_final_answer": sum(bool(r["no_final_answer"]) for r in q),
                   "truncated": sum(bool(r["truncated"]) for r in q),
                   "ctx_overflow": sum(bool(r["ctx_overflow"]) for r in q),
                   "refusals": sum(bool(r["refusal_detected"]) for r in q),
                   "context_has_answer": q[0]["context_has_answer"]}
            for k in METRICS + ["thinking_tokens_est"]:
                mu, sd = mean_sd([r[k] for r in q])
                rec[f"mean_{k}"], rec[f"sd_run_{k}"] = rnd(mu), rnd(sd)
            out.append(rec)
    return out


def model_summary(rows, models, expected_per_model):
    out = []
    for m in models:
        all_m = [r for r in rows if r["model"] == m]
        mr = usable(all_m)
        rec = {"model": m, "cells_expected": expected_per_model, "cells_ok": len(mr),
               "cells_failed": sum(r["status"] == "failed" for r in all_m),
               "no_final_answer": sum(bool(r["no_final_answer"]) for r in mr),
               "truncated": sum(bool(r["truncated"]) for r in mr),
               "ctx_overflow": sum(bool(r["ctx_overflow"]) for r in mr),
               "refusals": sum(bool(r["refusal_detected"]) for r in mr),
               "retried_cells": sum(int(r["attempts"] or 1) > 1 for r in mr)}
        qids = sorted({r["question_id"] for r in mr})
        runs = sorted({r["run_idx"] for r in mr})
        for k in METRICS + ["thinking_tokens_est"]:
            # (a) rata-rata per pertanyaan dulu -> mean & SD ANTAR-PERTANYAAN
            qmeans = [statistics.fmean([r[k] for r in mr if r["question_id"] == q]) for q in qids]
            mu, sd_q = mean_sd(qmeans)
            # (b) rata-rata keseluruhan tiap run -> SD ANTAR-RUN
            rmeans = []
            for ri in runs:
                vals = [r[k] for r in mr if r["run_idx"] == ri]
                if vals:
                    rmeans.append(statistics.fmean(vals))
            _, sd_r = mean_sd(rmeans)
            rec[f"mean_{k}"], rec[f"sd_between_questions_{k}"], rec[f"sd_between_runs_{k}"] = \
                rnd(mu), rnd(sd_q), rnd(sd_r)
        out.append(rec)
    return out


def completeness(rows, models, qids, runs):
    done = {(r["model"], int(r["question_id"]), int(r["run_idx"]))
            for r in rows if r["status"] != "failed"}
    expected = {(m, q, r) for m in models for q in qids for r in runs}
    return sorted(expected - done)


def export_all(outdir, rows, models, qids, runs, meta):
    rows_sorted = sorted(rows, key=lambda r: (models.index(r["model"]) if r["model"] in models else 99,
                                              int(r["run_idx"]), int(r["question_id"])))
    write_csv(os.path.join(outdir, "results_raw.csv"), RAW_FIELDS, rows_sorted)
    pq = per_question_summary(rows_sorted, models)
    if pq:
        write_csv(os.path.join(outdir, "results_per_question.csv"), list(pq[0].keys()), pq)
    ms = model_summary(rows_sorted, models, len(qids) * len(runs))
    if ms:
        write_csv(os.path.join(outdir, "results_summary.csv"), list(ms[0].keys()), ms)
    missing = completeness(rows_sorted, models, qids, runs)
    meta["missing_cells"] = [list(x) for x in missing]
    with open(os.path.join(outdir, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return ms, missing


def collect_environment(models):
    env = {"ollama_version": None, "model_digests": {}}
    try:
        env["ollama_version"] = http_json("/api/version", timeout=10).get("version")
    except Exception as e:
        env["ollama_version"] = f"unavailable ({e})"
    try:
        for t in http_json("/api/tags", timeout=10).get("models", []):
            if t.get("name") in models or t.get("model") in models:
                env["model_digests"][t.get("name")] = t.get("digest")
    except Exception:
        pass
    return env


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    global REQUEST_TIMEOUT
    ap = argparse.ArgumentParser(description="Evaluasi RAG multi-model (robust)")
    ap.add_argument("--dry-run", action="store_true", help="1 model x 2 pertanyaan x 1 run")
    ap.add_argument("--questions", type=int, nargs="+")
    ap.add_argument("--models", nargs="+", help="subset model (default: semua)")
    ap.add_argument("--runs", type=int, default=NUM_RUNS)
    ap.add_argument("--temperature", type=float, default=TEMPERATURE)
    ap.add_argument("--resume", metavar="DIR", help="lanjutkan folder hasil sebelumnya")
    ap.add_argument("--retry-no-answer", type=int, default=0,
                    help="berapa kali re-sample jika jawaban kosong setelah <think> dibuang "
                         "(default 0 = dicatat apa adanya)")
    ap.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT)
    args = ap.parse_args()

    REQUEST_TIMEOUT = args.timeout

    dataset = load_dataset()
    if args.questions:
        dataset = [q for q in dataset if q["id"] in args.questions]
    models = args.models or MODELS
    runs = list(range(1, args.runs + 1))
    if args.dry_run:
        dataset, models, runs = dataset[:2], models[:1], [1]
    qids = [q["id"] for q in dataset]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = args.resume or os.path.join(RESULTS_ROOT, f"run_{stamp}{'_dryrun' if args.dry_run else ''}")
    os.makedirs(outdir, exist_ok=True)
    jsonl_path = os.path.join(outdir, "raw.jsonl")
    ctx_path = os.path.join(outdir, "contexts.json")
    meta_path = os.path.join(outdir, "run_meta.json")

    options = build_options(args.temperature, None)
    options.pop("seed")
    if args.resume and os.path.exists(meta_path):
        old = json.load(open(meta_path, encoding="utf-8"))
        if old.get("options") != options or old.get("system_prompt") != _EVAL_SYSTEM_PROMPT:
            raise SystemExit("Resume ditolak: opsi/system prompt berbeda dari run awal.")
    meta = {"started": stamp, "options": options, "seed_scheme": f"SEED_BASE({SEED_BASE}) + run_idx",
            "models": models, "runs": runs, "question_ids": qids, "system_prompt": _EVAL_SYSTEM_PROMPT,
            "thinking_models": sorted(THINKING_MODELS), "retry_no_answer": args.retry_no_answer,
            "max_attempts_infra": MAX_ATTEMPTS, "embed_prefix": EMBED_PREFIX,
            "environment": collect_environment(models)}
    log("=" * 78)
    log(f"  Folder hasil : {outdir}")
    log(f"  Models       : {models}")
    log(f"  Pertanyaan   : {len(dataset)} | Runs: {len(runs)} | Total sel: {len(models)*len(dataset)*len(runs)}")
    log(f"  Opsi Ollama  : {options}")
    log(f"  Ollama       : {meta['environment']['ollama_version']}")
    log("=" * 78)

    rows = load_rows(jsonl_path)
    done = {k for k, r in rows.items() if r["status"] != "failed"}

    # Konteks: sekali per pertanyaan, dipakai bersama
    contexts = json.load(open(ctx_path, encoding="utf-8")) if os.path.exists(ctx_path) else {}
    need = [q for q in dataset if str(q["id"]) not in contexts]
    if need:
        log("[Setup] Mengambil konteks RAG (sekali per pertanyaan)...")
        from rag.retriever import retrieve_context
        for q in need:
            try:
                res = retrieve_context(q["question"], top_k=TOP_K_RETRIEVAL)
            except Exception as e:
                raise SystemExit(f"Retrieval gagal untuk Q{q['id']}: {e}")   # tidak lanjut diam-diam
            ctx, chunks = res.get("context", ""), res.get("chunks", [])
            diag = diagnose_context(ctx, q["reference_answer"], len(chunks) if chunks else 0)
            contexts[str(q["id"])] = {"context": ctx, **diag}
            log(f"    Q{q['id']:02d}: chunks={diag['num_chunks_retrieved']} "
                f"ctx_has_answer={diag['context_has_answer']} sim={diag['context_similarity']:.3f}")
        json.dump(contexts, open(ctx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    try:
        for model in models:
            pending = [(r, q) for r in runs for q in dataset if (model, q["id"], r) not in done]
            if not pending:
                log(f"\n[{model}] semua sel sudah lengkap, dilewati.")
                continue
            log(f"\n{'='*78}\n  Model: {model}  ({len(pending)} sel)\n{'='*78}")
            warm_up(model, args.temperature)
            for run_idx in runs:                                   # run di luar, pertanyaan di dalam
                for qa in dataset:
                    key = (model, qa["id"], run_idx)
                    if key in done:
                        continue
                    v0 = get_vram_mb()
                    row = run_cell(model, qa, run_idx, contexts[str(qa["id"])],
                                   args.temperature, args.retry_no_answer)
                    row["vram_mb_before"], row["vram_mb_after"] = v0, get_vram_mb()
                    append_row(jsonl_path, row)
                    rows[key] = row
                    if row["status"] != "failed":
                        done.add(key)
                    flag = "" if row["status"] == "ok" else f"  <<< {row['status']} {row['error']}"
                    flag += "  [TRUNCATED]" if row["truncated"] is True else ""
                    flag += "  [CTX-OVERFLOW]" if row["ctx_overflow"] is True else ""
                    log(f"  [{model} run {run_idx}/{len(runs)}] Q{qa['id']:02d} "
                        f"lat={row['latency_s']}s tok={row['completion_tokens']} "
                        f"sim={row['semantic_similarity']}{flag}")
    finally:
        ms, missing = export_all(outdir, list(rows.values()), models, qids, runs, meta)

    log(f"\n{'='*78}\n  RINGKASAN (rata-rata per pertanyaan; SD antar-pertanyaan | SD antar-run)\n{'='*78}")
    for s in ms:
        log(f"{s['model']:<13} ok={s['cells_ok']}/{s['cells_expected']} failed={s['cells_failed']} "
            f"no_answer={s['no_final_answer']} trunc={s['truncated']} ctx_over={s['ctx_overflow']} "
            f"refusal={s['refusals']} retried={s['retried_cells']}")
        for k in ("semantic_similarity", "latency_s", "throughput_tps", "completion_tokens"):
            log(f"    {k:<20} {s[f'mean_{k}']} (±{s[f'sd_between_questions_{k}']} | ±{s[f'sd_between_runs_{k}']})")
    if missing:
        log(f"\n[INCOMPLETE] {len(missing)} sel belum berhasil. Jalankan ulang:\n"
            f"    python evaluate.py --resume \"{outdir}\"")
        sys.exit(2)
    log(f"\n[OK] Semua {len(models)*len(qids)*len(runs)} sel lengkap tanpa kegagalan infrastruktur.")
    if any(s["no_final_answer"] or s["truncated"] or s["ctx_overflow"] for s in ms):
        log("[PERHATIAN] Ada jawaban kosong / terpotong / ctx overflow. Periksa results_raw.csv dan laporkan di naskah.")


if __name__ == "__main__":
    main()