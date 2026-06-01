import pandas as pd
import os
import sys

sys.path.insert(0, 'd:\\LLM\\instruct')
from eval.report import generate_report

# Load raw results
csv_path = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
df = pd.read_csv(csv_path)

# Dictionary of scores
eval_data = {
    "gemma2:2b": {
        1: (100, "Sangat lengkap dan akurat menyebutkan kedua kampus beserta alamat."),
        2: (95, "Hampir mencakup semua jurusan, terstruktur rapi per jenjang."),
        3: (100, "Instruksi pendaftaran sangat detail, runut, dan dilengkapi URL."),
        4: (40, "Hanya menyebutkan BPP, tidak mencakup biaya SKS dan Student Service sehingga totalnya tidak akurat."),
        5: (100, "Tabel fasilitas komprehensif dan akurat."),
        6: (100, "Menjawab dengan tepat jenis beasiswa yang ada."),
        7: (100, "Jadwal diekstrak dengan sempurna dari OCR hari Senin."),
        8: (100, "Sangat akurat berdasarkan teks RAG."),
        9: (100, "Kontak lengkap sesuai referensi."),
        10: (40, "Hanya menyebutkan BPP, tidak mencakup SKS dan Student Service."),
        11: (0, "Gagal menemukan konteks perbandingan antara TI dan SI."),
        12: (100, "Merangkum keunggulan dengan baik (Conceptual Study, Action Learning)."),
        13: (100, "Kalkulasi matematika sempurna (10.000.000 x 8 = 80 juta)."),
        14: (100, "Menyebutkan semua mata kuliah Theresia dengan tepat."),
        15: (100, "Sangat detail menyebutkan nama asrama dan tarif.")
    },
    "qwen3:1.7B": {
        1: (100, "Model berhasil menjawab kali ini dengan akurasi sangat tinggi ditambah link peta."),
        2: (90, "Lengkap namun format markdown tabel sedikit patah."),
        3: (100, "Langkah pendaftaran lengkap dengan tautan."),
        4: (40, "Hanya menangkap angka BPP pertama tanpa memperhitungkan biaya SKS."),
        5: (100, "Kategorisasi fasilitas sangat rapi."),
        6: (100, "Penjelasan beasiswa sangat baik."),
        7: (100, "Format tabel jadwal sangat luar biasa rapi."),
        8: (100, "Akurat sesuai referensi visi dan misi."),
        9: (100, "Lengkap dan akurat menyebutkan kontak."),
        10: (50, "Sadar bahwa itu adalah BPP, tetapi mengabaikan komponen biaya lainnya."),
        11: (90, "Analisis perbandingan sangat baik walaupun ada sedikit asumsi kurikulum spesifik."),
        12: (100, "Ekstraksi poin keunggulan luar biasa tajam."),
        13: (100, "Kalkulasi matematika tepat sasaran."),
        14: (70, "Menyebutkan mata kuliah namun melewatkan sesi Lab SBD."),
        15: (100, "Sangat mendetail tentang Cluster Alloggio.")
    },
    "llama3.2:1b": {
        1: (90, "Menjawab langsung lokasi kampus namun kurang detail alamat spesifiknya."),
        2: (50, "Terlalu banyak copy-paste mentah tanpa ringkasan yang enak dibaca."),
        3: (30, "Gagal meringkas langkah pendaftaran, hanya mengulang isi dokumen acak."),
        4: (30, "Kontradiksi: menyebut angka lalu berhalusinasi menyatakan informasi tidak ada."),
        5: (40, "Hanya memuntahkan isi dokumen mentah tanpa format yang baik."),
        6: (80, "Cukup mampu menangkap jalur beasiswa yang ditawarkan."),
        7: (0, "Gagal mencari konteks jadwal dalam RAG."),
        8: (80, "Cukup akurat namun format berantakan karena dump dokumen mentah."),
        9: (90, "Benar tetapi melewatkan detail nomor telepon dan email yang eksplisit."),
        10: (40, "Hanya mampu menangkap BPP."),
        11: (20, "Banyak asumsi fiktif mengenai proses karir dan fleksibilitas online/offline."),
        12: (90, "Cukup akurat meskipun repetitif."),
        13: (100, "Kalkulasi matematika perkalian akurat."),
        14: (100, "Berhasil mengekstrak semua kelas yang diajar dosen terkait."),
        15: (0, "Sama sekali gagal menjawab, hanya mendeskripsikan isi dokumen 5 secara meta.")
    }
}

# Update dataframe
for idx, row in df.iterrows():
    model = row['model']
    qid = row['question_id']
    if model in eval_data and qid in eval_data[model]:
        score, reasoning = eval_data[model][qid]
        df.at[idx, 'llm_judge_score'] = score
        df.at[idx, 'llm_judge_reasoning'] = reasoning

# Save back to CSV
df.to_csv(csv_path, index=False)

# Re-generate summary CSV
numeric_cols = ['rouge_l', 'bleu', 'bert_f1', 'semantic_similarity', 'llm_judge_score', 'latency_s', 'throughput_tps', 'vram_peak_mb', 'context_precision_pct']
agg_funcs = {}
for col in numeric_cols:
    if col in df.columns:
        agg_funcs[col] = 'mean'
agg_funcs['question_id'] = 'count'
if 'error' in df.columns:
    agg_funcs['error'] = lambda x: (x.notnull() & (x != '')).sum()

summary_df = df.groupby('model').agg(agg_funcs).reset_index()

rename_map = {col: f"avg_{col}" for col in agg_funcs if col not in ['question_id', 'error']}
rename_map['question_id'] = 'num_questions'
rename_map['error'] = 'num_errors'
summary_df.rename(columns=rename_map, inplace=True)

summary_path = 'd:\\LLM\\instruct\\eval\\results\\results_summary_20260526_013647.csv'
summary_df.to_csv(summary_path, index=False)

# Generate markdown report
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_DIR = 'd:\\LLM\\instruct\\eval\\results'

# Prepare dictionary rows
raw_rows = df.to_dict('records')
summary_rows = summary_df.to_dict('records')

report_md = generate_report(raw_rows, summary_rows)
out_path  = os.path.join(RESULTS_DIR, f"report_{timestamp}.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report_md)

print(f"\n[Report] Generated: {out_path}")
