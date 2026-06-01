"""
_claude_sonnet_as_a_judge.py
============================
Claude Sonnet 4.6 sebagai LLM-as-a-Judge untuk evaluasi RAG multi-model.

Script ini membaca hasil evaluasi terbaru (results_raw_*.csv) dan menambahkan
penilaian dari Claude Sonnet 4.6 sebagai judge independen.

Output: eval/results/claude_sonnet_as_a_judge_results.csv

Rubrik penilaian Claude (skala 0-100):
  - Akurasi Faktual  (40%): Apakah fakta sesuai referensi? Ada halusinasi?
  - Kelengkapan      (30%): Semua poin penting dari referensi tercakup?
  - Relevansi        (20%): Apakah jawaban fokus pada pertanyaan?
  - Kejelasan        (10%): Apakah jawaban mudah dipahami dan terstruktur?

Referensi format: _apply_gemini_judge.py → gemini_judge_results.csv
"""

import pandas as pd
import os
import sys
import glob

sys.path.insert(0, 'd:\\LLM\\instruct')

# ── Cari file raw results terbaru ──────────────────────────────────────────────
RESULTS_DIR = 'd:\\LLM\\instruct\\eval\\results'
raw_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'results_raw_*.csv')))

if not raw_files:
    raise FileNotFoundError("Tidak ada file results_raw_*.csv. Jalankan evaluate.py terlebih dahulu.")

csv_path = raw_files[-1]
print(f"[Load] Membaca: {os.path.basename(csv_path)}")
df = pd.read_csv(csv_path)

print(f"[Load] Total baris: {len(df)}")
print(f"[Load] Model yang ditemukan: {df['model'].unique().tolist()}")

# ── CLAUDE SONNET 4.6 AS JUDGE ───────────────────────────────────────────────
# Rubrik: 0-100, menilai akurasi faktual, kelengkapan, relevansi, kejelasan
# Evaluasi dilakukan oleh Claude Sonnet 4.6 (model: claude-sonnet-4-6)
# Berdasarkan jawaban aktual setiap model per pertanyaan

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
        1:  (75,  "Jawaban mencakup lokasi Jakarta dan Gading Serpong dengan benar, namun kurang detail alamat spesifik dari referensi."),
        2:  (80,  "Membaca isi dokumen mentah untuk mendaftar prodi, tetapi agak terputus. Mencakup S1 Architecture dll."),
        3:  (90,  "Langkah-langkah pendaftaran disebutkan dengan baik walau agak terpenggal di awal."),
        4:  (35,  "Hanya menyebutkan Rp 7.500.000,- (BPP) tanpa menghitung total dengan SKS dan biaya layanan."),
        5:  (85,  "Fasilitas diekstrak secara verbatim dari dokumen, cukup lengkap."),
        6:  (0,   "Halusinasi total. Menyatakan tidak ada informasi beasiswa, sangat bertentangan dengan konteks yang ada."),
        7:  (70,  "Menyebutkan dua dari tiga kelas Theresia (Sistem Basis Data dan Lab). Melewatkan Interaksi Manusia dan Komputer."),
        8:  (90,  "Misi berhasil dirangkum dari konteks dengan baik."),
        9:  (95,  "Kontak yang diberikan benar sesuai referensi."),
        10: (40,  "Menyebutkan informasi bervariasi tanpa memberikan angka dasar (BPP) atau total yang jelas seperti dalam referensi."),
        11: (85,  "Memulai perbandingan dengan baik meskipun penyajian bisa lebih tajam."),
        12: (90,  "Berhasil menangkap beberapa poin keunggulan utama dengan bahasa yang cukup lugas."),
        13: (100, "Matematika tepat. 500.000 * 20 = 10.000.000, dikali 8 = 80 juta."),
        14: (60,  "Mencampurkan mata kuliah yang benar dan salah (contoh: Internet of Things tidak diajar Theresia di jadwal ini)."),
        15: (0,   "Gagal mengekstrak info asrama (Cluster Alloggio) dan menyatakan tidak ada di dokumen.")
    }
}

# ── Tambahkan kolom Claude judge jika belum ada ───────────────────────────────
if 'claude_judge_score' not in df.columns:
    df['claude_judge_score'] = -1.0
if 'claude_judge_reasoning' not in df.columns:
    df['claude_judge_reasoning'] = ''

# ── Inject skor Claude ────────────────────────────────────────────────────────
injected = 0
for idx, row in df.iterrows():
    model = row['model']
    qid = int(row['question_id'])
    if model in claude_eval and qid in claude_eval[model]:
        score, reasoning = claude_eval[model][qid]
        df.at[idx, 'claude_judge_score'] = score
        df.at[idx, 'claude_judge_reasoning'] = reasoning
        injected += 1

print(f"[Inject] Claude judge scores injected: {injected} baris")

# ── Simpan ke claude_sonnet_as_a_judge_results.csv dan menimpa results_raw_*.csv ───
out_path = os.path.join(RESULTS_DIR, 'claude_sonnet_as_a_judge_results.csv')
df.to_csv(out_path, index=False)
df.to_csv(csv_path, index=False)
print(f"[Save] Disimpan ke: {out_path} dan dioverwrite ke {csv_path}")

# ── Rebuild Summary ───────────────────────────────────────────────────────────
models = df['model'].unique().tolist()

print("\n=== CLAUDE SONNET 4.6 AS JUDGE — RINGKASAN ===")
print(f"{'Model':<40} {'Gemini Judge':>14} {'Claude Judge':>14} {'SemSim':>10}")
print("-" * 82)

for model in models:
    mdf = df[df['model'] == model]
    
    # Hitung rata-rata hanya untuk baris valid (score >= 0)
    gemini_valid = mdf[mdf['llm_judge_score'] >= 0]['llm_judge_score']
    claude_valid = mdf[mdf['claude_judge_score'] >= 0]['claude_judge_score']
    semsim_valid = mdf[mdf['semantic_similarity'] >= 0]['semantic_similarity']
    
    g_avg = gemini_valid.mean() if len(gemini_valid) > 0 else -1
    c_avg = claude_valid.mean() if len(claude_valid) > 0 else -1
    s_avg = semsim_valid.mean() if len(semsim_valid) > 0 else -1
    
    g_str = f"{g_avg:.1f}" if g_avg >= 0 else "N/A"
    c_str = f"{c_avg:.1f}" if c_avg >= 0 else "N/A"
    s_str = f"{s_avg:.4f}" if s_avg >= 0 else "N/A"
    
    print(f"{model:<40} {g_str:>14} {c_str:>14} {s_str:>10}")

print("-" * 82)
print(f"\n[Done] Evaluasi Claude Sonnet 4.6 selesai.")
print(f"[Done] File output: {out_path}")
print(f"\n[INFO] Catatan: model 'meta-llama/Llama-3.2-1B-Instruct' perlu dijalankan")
print(f"       evaluate.py terlebih dahulu untuk mendapatkan jawaban aktual,")
print(f"       setelah itu update skor Claude di bagian claude_eval dalam script ini.")
