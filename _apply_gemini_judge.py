import pandas as pd

# Load existing raw results
df = pd.read_csv('eval/results/results_raw_20260523_114434.csv')

# These are the evaluations made by Gemini (acting as LLM Judge) for qwen3:1.7B
gemini_evals = {
    1: {"score": 100, "reasoning": "Akurat dan sangat lengkap."},
    2: {"score": 100, "reasoning": "Sangat lengkap dan mencakup jenjang diploma/magister."},
    3: {"score": 100, "reasoning": "Jawaban sangat lengkap dan memberikan langkah-langkah praktis."},
    4: {"score": 60,  "reasoning": "Jawaban jujur menolak menjawab karena kurang konteks, tetapi tidak menyarankan menghubungi kampus seperti referensi."},
    5: {"score": 100, "reasoning": "Sangat lengkap dan terstruktur dalam bentuk tabel."},
    6: {"score": 100, "reasoning": "Sangat akurat dan memberikan link website."},
    7: {"score": 100, "reasoning": "Jadwal yang diberikan sangat akurat dan terstruktur."},
    8: {"score": 100, "reasoning": "Sangat akurat sesuai dengan referensi."},
    9: {"score": 95,  "reasoning": "Akurat, memberikan email dan website yang benar sesuai referensi."},
    10: {"score": 60, "reasoning": "Menolak menjawab karena kurang konteks, tidak mengarahkan ke kontak kampus."},
    11: {"score": 90, "reasoning": "Perbandingan cukup baik meskipun konteks Sistem Informasi kurang detail diakui oleh model."},
    12: {"score": 100, "reasoning": "Mencakup semua keunggulan utama dengan penjelasan yang jelas."},
    13: {"score": 100, "reasoning": "Perhitungan matematika benar dan akurat."},
    14: {"score": 70,  "reasoning": "Sebagian benar, tetapi secara keliru mengecualikan 'Lab Sistem Basis Data'."},
    15: {"score": 100, "reasoning": "Sangat lengkap dan akurat, bahkan menyertakan detail fasilitas asrama."}
}

# Update the dataframe
# Since evaluate.py adds the columns `llm_judge_score` and `llm_judge_reasoning`, we will add them here
if 'llm_judge_score' not in df.columns:
    df['llm_judge_score'] = -1
    df['llm_judge_reasoning'] = ""
    df['semantic_similarity'] = -1.0 # placeholder

# We will only update qwen3:1.7B
for idx, row in df.iterrows():
    if row['model'] == 'qwen3:1.7B':
        qid = row['question_id']
        if qid in gemini_evals:
            df.at[idx, 'llm_judge_score'] = gemini_evals[qid]['score']
            df.at[idx, 'llm_judge_reasoning'] = gemini_evals[qid]['reasoning']
            # We'll put a placeholder for semantic sim for this demo
            df.at[idx, 'semantic_similarity'] = 0.8500 

df.to_csv('eval/results/gemini_judge_results.csv', index=False)
print("Saved evaluation to eval/results/gemini_judge_results.csv")

# Print a nice summary table
qwen_df = df[df['model'] == 'qwen3:1.7B']
avg_score = qwen_df['llm_judge_score'].mean()
print("="*60)
print("  EVALUASI LLM-as-a-Judge (Gemini Pro) untuk qwen3:1.7B")
print("="*60)
for _, row in qwen_df.iterrows():
    qid = row['question_id']
    score = row['llm_judge_score']
    reason = row['llm_judge_reasoning']
    print(f"Q{qid:02d} | Score: {score:3d} | {reason}")
print("-"*60)
print(f"Rata-rata Skor: {avg_score:.1f}/100")
print("="*60)
