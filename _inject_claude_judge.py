import pandas as pd
import os
import sys
sys.path.insert(0, 'd:\\LLM\\instruct')

csv_path = 'd:\\LLM\\instruct\\eval\\results\\results_raw_20260526_013647.csv'
df = pd.read_csv(csv_path)

# ── CLAUDE SONNET 4.6 AS JUDGE ──────────────────────────────────────────────
# Rubrik: 0-100, menilai akurasi faktual, kelengkapan, relevansi, kualitas penalaran
claude_eval = {
    "gemma2:2b": {
        1:  (100, "Akurat 100%: menyebutkan kedua alamat kampus beserta nama gedung dan kode pos."),
        2:  (70,  "Hanya 6 prodi S1, melewatkan Informatika, Sistem Informasi, Pariwisata, Manajemen, F&B. Struktur bagus tapi tidak lengkap."),
        3:  (100, "7 langkah pendaftaran runut dan akurat, disertai link portal."),
        4:  (35,  "Hanya BPP (Rp 7.5jt), mengabaikan biaya SKS (Rp 7jt) dan Student Service (Rp 750k). Total seharusnya ~Rp 15.25jt."),
        5:  (100, "Fasilitas dikategorikan dengan sangat baik dan mencakup semua item kunci dari referensi."),
        6:  (95,  "Tiga jalur beasiswa disebutkan dengan tepat. Sedikit kurang detail mengenai syarat spesifik masing-masing jalur."),
        7:  (100, "Ketiga mata kuliah hari Senin diekstrak sempurna dari OCR jadwal beserta kode, ruang, dan jam."),
        8:  (100, "Visi dan 4 misi dikutip secara akurat dan lengkap dari RAG."),
        9:  (100, "Kontak 5-channel (telepon, email, Facebook, sosmed, website) sesuai referensi."),
        10: (35,  "Hanya BPP (Rp 6.5jt), mengabaikan SKS dan Student Service. Total estimasi seharusnya ~Rp 14.25jt."),
        11: (0,   "Tidak menjawab sama sekali, menyatakan tidak ada informasi padahal RAG memiliki data kurikulum TI."),
        12: (95,  "Mengangkat Conceptual Study, Action Learning, dan fasilitas utama dengan akurat."),
        13: (100, "Kalkulasi dua tahap ditampilkan eksplisit: 500k×20=10jt per semester, 10jt×8=80jt total. Benar."),
        14: (100, "IMK, SBD, Lab SBD semua ada dengan info semester yang tepat."),
        15: (100, "Cluster Alloggio, 382 unit, harga Rp 1.5-2jt, fasilitas kolam renang dan shuttle bus — sangat lengkap."),
    },
    "qwen3:1.7B": {
        1:  (100, "Jawaban sangat rapi: dua kampus dengan bullet bersarang, alamat lengkap, ditambah link Google Maps."),
        2:  (95,  "10 prodi S1 plus D3 dan S2 — paling lengkap. Sedikit perbedaan nama (Manajemen vs Manajemen Bisnis). Catatan dokumen sedikit mengganggu."),
        3:  (100, "Langkah pendaftaran 1-6 (lebih ringkas dari gemma) disertai kontak dan link. Tepat."),
        4:  (35,  "Menangkap BPP yang benar (Rp 7.5jt) tapi secara eksplisit menyatakan 'nilai biaya per semester sama dengan VCD' — perbandingan yang membingungkan dan tidak diminta."),
        5:  (100, "Format tiga-bagian (Akademika, Transportasi, Lain-lain) paling terstruktur dari semua model. Termasuk workshop lab dan podcast room."),
        6:  (100, "USM + Jalur Prestasi dijelaskan dengan mekanisme ujian dan jenis penghargaan, plus link langsung ke halaman beasiswa."),
        7:  (100, "Format tabel markdown dengan 6 kolom (Mata Kuliah, Kode, Jam, Kelas, Ruang, Dosen) — representasi paling elegan dari data jadwal OCR."),
        8:  (100, "Visi dan 4 misi akurat. Catatan 'dokumen #1 dan #2' tidak mengganggu jawaban substantif."),
        9:  (80,  "Kontak lengkap dan akurat, namun kalimat pembuka 'Maaf sobat, saya tidak memiliki informasi tersebut' merupakan perilaku aneh yang inkonsisten dan membingungkan pengguna."),
        10: (40,  "Mengakui itu BPP secara eksplisit — menunjukkan kesadaran. Namun tidak menghitung total biaya semester sepenuhnya."),
        11: (85,  "Analisis TI vs SI dengan tabel dan kesimpulan. Menggunakan kode mata kuliah nyata dari jadwal (IF141403, IF232103) — berbasis data RAG. Asumsi 'SI lebih umum' cukup justified."),
        12: (100, "4 poin keunggulan (Pembelajaran Holistik, Penerapan Nyata, Kolaborasi Praktisi, Fasilitas Terkini) dikemas dengan ringkas dan tajam."),
        13: (100, "Menjelaskan total SKS = 160, lalu biaya = 160×500k = 80jt. Pendekatan kalkulasi paling transparan."),
        14: (70,  "Menyebut IMK dan SBD (2 dari 3), melewatkan Lab. Sistem Basis Data padahal ada dalam jadwal."),
        15: (100, "Jawaban sangat kompak: nama asrama, jumlah unit, range harga, fasilitas kolam dan shuttle — semua benar."),
    },
    "llama3.2:1b": {
        1:  (40,  "Hanya menyebutkan nama kampus tanpa alamat spesifik. Jawaban sangat dangkal untuk pertanyaan sederhana ini."),
        2:  (35,  "Dump 5 dokumen mentah tanpa sintesis. Termasuk informasi tidak relevan (lokasi kampus, misi) dalam jawaban 'prodi apa saja'."),
        3:  (20,  "Hanya mendeskripsikan jenis isi dokumen ('Dokumen #1 tentang proses pendaftaran...') tanpa memberikan panduan pendaftaran aktual. Tidak membantu."),
        4:  (30,  "Menyebut angka benar (Rp 7.5jt) tapi kemudian berhalusinasi: 'informasi tersebut tidak ada dalam dokumen'. Kontradiksi yang membingungkan."),
        5:  (35,  "Copy-paste kasar dari beberapa chunk dokumen. Format tidak dibersihkan, termasuk path file lokal (D:\\LLM\\instruct\\...) yang tidak relevan."),
        6:  (75,  "Berhasil mengidentifikasi 4 jalur beasiswa (USM, Rapor, Prestasi) dengan sedikit konteks. Jawaban lebih baik dari rata-rata llama pada pertanyaan lain."),
        7:  (0,   "Secara eksplisit menyatakan tidak ada informasi jadwal Senin padahal RAG memiliki data tersebut. Gagal total mengekstrak konteks yang ada."),
        8:  (55,  "Menyebutkan 2 dari 4 misi, lalu menyimpang ke lokasi kampus, jenjang program studi, dll. Tidak fokus pada pertanyaan."),
        9:  (85,  "Memberikan jawaban yang dapat ditindaklanjuti (website) plus email dan telepon — meski sedikit lebih minimal dari referensi."),
        10: (40,  "Menangkap BPP (Rp 6.5jt) dengan cara yang lebih jelas ('dalam konteks tersebut, biaya adalah...') tapi tetap tidak menghitung total."),
        11: (25,  "Membuat asumsi fiktif: 'prodi SI memiliki kurikulum online/offline', 'proses karir harus melalui dosen pengampu' — halusinasi yang menyesatkan."),
        12: (85,  "6 poin keunggulan termasuk koloni mahasiswa (Cluster Alloggio) yang secara kreatif ditambahkan tapi relevan. Agak repetitif di poin 3-4."),
        13: (100, "Kalkulasi benar dengan dua tahap eksplisit: 500k×20=10jt, 10jt×8=80jt. Lalu berputar ke pertanyaan sampingan yang tidak perlu."),
        14: (100, "Mengekstrak 4 mata kuliah Theresia termasuk IoT dan Logika Matematika (dari prodi berbeda) — melebihi referensi tapi faktual."),
        15: (0,   "Gagal total: hanya menceritakan isi dokumen #5 tentang prosedur pendaftaran, sama sekali tidak menyebut asrama."),
    }
}

# Add claude columns if not present
if 'claude_judge_score' not in df.columns:
    df['claude_judge_score'] = -1.0
if 'claude_judge_reasoning' not in df.columns:
    df['claude_judge_reasoning'] = ''

for idx, row in df.iterrows():
    model = row['model']
    qid = row['question_id']
    if model in claude_eval and qid in claude_eval[model]:
        score, reasoning = claude_eval[model][qid]
        df.at[idx, 'claude_judge_score'] = score
        df.at[idx, 'claude_judge_reasoning'] = reasoning

df.to_csv(csv_path, index=False)
print("[OK] Claude judge scores injected.")

# ── REBUILD SUMMARY ──────────────────────────────────────────────────────────
numeric_cols = [c for c in ['rouge_l','bleu','bert_f1','semantic_similarity',
                             'llm_judge_score','claude_judge_score',
                             'latency_s','throughput_tps','vram_peak_mb',
                             'context_precision_pct'] if c in df.columns]

agg_funcs = {col: 'mean' for col in numeric_cols}
agg_funcs['question_id'] = 'count'
if 'error' in df.columns:
    agg_funcs['error'] = lambda x: (x.notnull() & (x != '')).sum()

summary_df = df.groupby('model').agg(agg_funcs).reset_index()
rename_map = {col: f"avg_{col}" for col in numeric_cols}
rename_map['question_id'] = 'num_questions'
rename_map['error'] = 'num_errors'
summary_df.rename(columns=rename_map, inplace=True)

summary_path = 'd:\\LLM\\instruct\\eval\\results\\results_summary_20260526_013647.csv'
summary_df.to_csv(summary_path, index=False)
print("[OK] Summary CSV updated.")

# Print quick summary
print("\n=== DUAL JUDGE SUMMARY ===")
print(f"{'Model':<20} {'Gemini Judge':>14} {'Claude Judge':>14}")
print("-"*50)
for _, r in summary_df.iterrows():
    g = r.get('avg_llm_judge_score', -1)
    c = r.get('avg_claude_judge_score', -1)
    print(f"{r['model']:<20} {g:>14.1f} {c:>14.1f}")
