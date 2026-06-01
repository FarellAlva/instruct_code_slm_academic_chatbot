"""
eval/report.py
==============
Generate laporan Markdown dari hasil evaluasi CSV.
Menghasilkan: eval/results/report_<timestamp>.md
"""

import os, sys, csv, glob
from datetime import datetime

EVAL_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(EVAL_DIR, "results")
sys.path.insert(0, os.path.dirname(EVAL_DIR))


def load_latest_results() -> tuple[list[dict], list[dict]]:
    """Load the most recent raw and summary CSVs."""
    raw_files     = sorted(glob.glob(os.path.join(RESULTS_DIR, "results_raw_*.csv")))
    summary_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "results_summary_*.csv")))

    if not raw_files:
        raise FileNotFoundError("No raw results CSV found. Run evaluate.py first.")

    def read_csv(path):
        with open(path, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    raw_rows     = read_csv(raw_files[-1])
    summary_rows = read_csv(summary_files[-1]) if summary_files else []
    print(f"[Report] Loaded: {os.path.basename(raw_files[-1])}")
    return raw_rows, summary_rows


def generate_report(raw_rows: list[dict], summary_rows: list[dict]) -> str:
    now = datetime.now().strftime("%d %B %Y, %H:%M")
    models = list(dict.fromkeys(r["model"] for r in raw_rows))

    # ── Header ────────────────────────────────────────────────────────────────
    lines = [
        "# Laporan Evaluasi RAG Multi-Model (Paper Aligned)",
        f"**Tanggal:** {now}",
        f"**Model yang dievaluasi:** {', '.join(f'`{m}`' for m in models)}",
        f"**Jumlah pertanyaan:** {len(set(r['question_id'] for r in raw_rows))}",
        "",
        "---",
        "",
    ]

    # ── Summary Table ────────────────────────────────────────────────────────
    lines += [
        "## Ringkasan Performa (Rata-rata Semua Pertanyaan)",
        "",
        "| Model | SemSim | Gemini Judge | Claude Judge | Ctx% | Latency (s) | Throughput (tok/s) |",
        "|-------|--------|--------------|--------------|------|-------------|--------------------|",
    ]
    for s in summary_rows:
        ssim   = float(s.get("avg_semantic_similarity", 0))
        judge_g  = float(s.get("avg_llm_judge_score", -1))
        judge_c  = float(s.get("avg_claude_judge_score", -1))
        ctx    = float(s.get("avg_context_precision_pct", s.get("context_accuracy_pct", 100)))
        lat    = float(s.get("avg_latency_s", 0))
        tps    = float(s.get("avg_throughput_tps", 0))
        
        judge_g_str = f"{judge_g:.1f}" if judge_g >= 0 else "N/A"
        judge_c_str = f"{judge_c:.1f}" if judge_c >= 0 else "N/A"
        lines.append(
            f"| `{s['model']}` | {ssim:.4f} | {judge_g_str} | {judge_c_str} | {ctx:.1f}% | {lat:.2f} | {tps:.1f} |"
        )
    lines.append("")

    # ── Best Model Callout ─────────────────────────────────────────────────────
    if summary_rows:
        best_judge_g = max(summary_rows, key=lambda x: float(x.get("avg_llm_judge_score", 0)))
        best_judge_c = max(summary_rows, key=lambda x: float(x.get("avg_claude_judge_score", 0)))
        best_speed = max(summary_rows, key=lambda x: float(x.get("avg_throughput_tps", 0)))
        lines += [
            "> [!NOTE]",
            f"> **Model terbaik (Gemini Judge):** `{best_judge_g['model']}` ({float(best_judge_g.get('avg_llm_judge_score', 0)):.1f}/100)",
            f"> **Model terbaik (Claude Judge):** `{best_judge_c['model']}` ({float(best_judge_c.get('avg_claude_judge_score', 0)):.1f}/100)",
            f"> **Model tercepat:** `{best_speed['model']}` ({float(best_speed.get('avg_throughput_tps', 0)):.1f} tok/s)",
            "",
        ]

    # ── Per-Question Detail ────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Detail Per Pertanyaan",
        "",
    ]

    question_ids = sorted(set(int(r["question_id"]) for r in raw_rows))
    for qid in question_ids:
        qrows = [r for r in raw_rows if int(r["question_id"]) == qid]
        if not qrows:
            continue

        q0 = qrows[0]
        lines += [
            f"### Q{qid:02d} — {q0['category']} [{q0['complexity']}]",
            "",
            f"**Pertanyaan:** {q0['question']}",
            "",
            f"**Referensi jawaban:**",
            f"> {q0['reference_answer'][:300]}{'...' if len(q0['reference_answer']) > 300 else ''}",
            "",
            "**Hasil per model:**",
            "",
            "| Model | SemSim | Gemini | Claude | Latency | Tok/s |",
            "|-------|--------|--------|--------|---------|-------|",
        ]

        for row in qrows:
            ss = float(row.get("semantic_similarity", 0))
            judge_g = float(row.get("llm_judge_score", -1))
            judge_c = float(row.get("claude_judge_score", -1))
            lat  = float(row.get("latency_s", 0))
            tps  = float(row.get("throughput_tps", 0))
            
            judge_g_str = f"{judge_g:.1f}" if judge_g >= 0 else "N/A"
            judge_c_str = f"{judge_c:.1f}" if judge_c >= 0 else "N/A"
            lines.append(
                f"| `{row['model']}` | {ss:.4f} | {judge_g_str} | {judge_c_str} | {lat:.2f}s | {tps:.1f} |"
            )

        # Show answer and reasoning for each model
        lines.append("")
        lines.append("**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**")
        lines.append("")
        for row in qrows:
            ans = row["answer"].replace("\n", " ").strip()
            reasoning_g = row.get("llm_judge_reasoning", "")
            reasoning_c = row.get("claude_judge_reasoning", "")
            lines.append(f"- **`{row['model']}`:** {ans[:250]}{'...' if len(ans) > 250 else ''}")
            if reasoning_g:
                lines.append(f"  * **Gemini 3.1 Pro:** {reasoning_g}")
            if reasoning_c:
                lines.append(f"  * **Claude Sonnet 4.6:** {reasoning_c}")
            lines.append("")

        lines += ["", "---", ""]

    # ── Catatan Metodologi ───────────────────────────────────────────
    lines += [
        "## Catatan Metodologi (Sesuai Paper Hendra Lijaya et al.)",
        "",
        "- **Semantic Similarity**: Cosine similarity embedding berbasis `intfloat/multilingual-e5-base`",
        "- **LLM-as-a-Judge (Gemini 3.1 Pro)**: Penilaian AI berbasis Gemini dari skala 0-100 dengan rubrik: Akurasi Faktual (40%), Kelengkapan (30%), Relevansi (20%), Kejelasan (10%)",
        "- **LLM-as-a-Judge (Claude Sonnet 4.6)**: Penilaian AI berbasis Claude dengan rubrik dan perspektif independen, skala 0-100",
        "- **Context Precision (Ctx%)**: % pertanyaan di mana RAG retriever berhasil menemukan konteks yang relevan",
        "- **BLEU/ROUGE/BERTScore**: Dihapus — metrik berbasis n-gram dan embedding tidak dapat mendeteksi halusinasi secara akurat",
        "",
        "### Mengapa Dual LLM Judge (Tanpa BERTScore)?",
        "",
        "BERTScore (bahkan yang multilingual) tidak dapat mendeteksi halusinasi atau jawaban yang faktual salah dengan baik",
        "karena model hanya mengukur kemiripan embedding, bukan validitas faktual. LLM-as-a-Judge (Gemini + Claude)",
        "mengisi kesenjangan ini dengan menilai akurasi, kelengkapan, dan relevansi secara semantik.",
        "Menggunakan dua model judge yang berbeda (Gemini dan Claude) memberikan perspektif yang lebih objektif.",
        "",
        "*Laporan ini di-generate otomatis oleh sistem evaluasi dengan integrasi Dual LLM Judge (Gemini 3.1 Pro + Claude Sonnet 4.6)*",
    ]

    return "\n".join(lines)


def main():
    raw_rows, summary_rows = load_latest_results()
    report_md = generate_report(raw_rows, summary_rows)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[Report] Generated: {out_path}")


if __name__ == "__main__":
    main()
